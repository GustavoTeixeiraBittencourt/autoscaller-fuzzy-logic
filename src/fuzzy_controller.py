"""Controlador fuzzy Mamdani para decisão de autoscaling.

Três entradas (cpu, fila, tendencia), cada uma com 3 conjuntos
(baixo/médio/alto), e uma saída (delta_instancias) com 5 conjuntos. A base
de 27 regras é gerada a partir de um critério explícito (soma dos níveis
das entradas) para garantir, por construção, que toda combinação de
entradas ativa alguma regra — ver docs/SPEC.md, seção 3.

Todas as funções de pertinência são parametrizáveis por um vetor plano de
14 números (``VETOR_PADRAO`` é a configuração manual padrão), pensando na
futura otimização por NSGA-II (ver docs/SPEC.md, seção 7): o vetor nunca é
usado diretamente sem passar por ``validar``/``repair``.
"""

from __future__ import annotations

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

DOMINIO_CPU = (0.0, 100.0)
DOMINIO_FILA = (0.0, 50.0)
DOMINIO_TENDENCIA = (-20.0, 20.0)
DOMINIO_DELTA = (-3.0, 3.0)

N_PARAMS = 14
EPS = 1e-3

# [cpu: p1,p2,p3] [fila: p1,p2,p3] [tendencia: p1,p2,p3] [saida: c1..c5]
VETOR_PADRAO = np.array(
    [
        30.0, 50.0, 70.0,
        5.0, 15.0, 25.0,
        -8.0, 0.0, 8.0,
        -2.0, -1.0, 0.0, 1.0, 2.0,
    ]
)

NIVEL_CPU = {"baixa": -1, "media": 0, "alta": 1}
NIVEL_FILA = {"pequena": -1, "media": 0, "grande": 1}
NIVEL_TENDENCIA = {"caindo": -1, "estavel": 0, "subindo": 1}

# notas curtas só nas combinações mais relevantes para a apresentação
_NOTAS = {
    ("alta", "grande", "subindo"): "pico de tráfego claro: reage com força máxima",
    ("baixa", "pequena", "caindo"): "ociosidade clara: economiza custo",
    ("alta", "pequena", "caindo"): (
        "evita oscilação: CPU alta momentânea mas fila vazia e carga já "
        "caindo não justifica manter capacidade extra"
    ),
    ("media", "media", "estavel"): "ponto de equilíbrio do sistema",
}


def _rotulo_saida(score: int) -> str:
    if score <= -2:
        return "remover_muito"
    if score == -1:
        return "remover"
    if score == 0:
        return "manter"
    if score == 1:
        return "adicionar"
    return "adicionar_muito"


def _montar_tabela_regras():
    """Gera as 27 regras (cpu, fila, tendencia) -> delta sem buracos.

    O rótulo de saída é função apenas da soma dos níveis das 3 entradas,
    então toda combinação das 3x3x3 entradas tem, por construção, exatamente
    uma saída associada.
    """
    tabela = []
    for cpu_label, lc in NIVEL_CPU.items():
        for fila_label, lf in NIVEL_FILA.items():
            for tend_label, lt in NIVEL_TENDENCIA.items():
                score = lc + lf + lt
                delta_label = _rotulo_saida(score)
                nota = _NOTAS.get((cpu_label, fila_label, tend_label), "")
                tabela.append((cpu_label, fila_label, tend_label, delta_label, nota))
    return tabela


TABELA_REGRAS = _montar_tabela_regras()


def _repair_grupo(pontos, dmin: float, dmax: float, eps: float = EPS) -> np.ndarray:
    """Ordena, recorta ao domínio e garante espaçamento mínimo entre pontos."""
    p = np.clip(np.sort(np.asarray(pontos, dtype=float)), dmin, dmax)
    n = len(p)
    for i in range(1, n):
        p[i] = max(p[i], p[i - 1] + eps)
    for i in range(n - 2, -1, -1):
        if p[i + 1] > dmax:
            p[i + 1] = dmax
        if p[i] > p[i + 1] - eps:
            p[i] = p[i + 1] - eps
    return np.clip(p, dmin, dmax)


def repair(vetor) -> np.ndarray:
    """Corrige um vetor de parâmetros inválido (ordem e domínio).

    Usado pela futura busca do NSGA-II: um indivíduo gerado por
    cruzamento/mutação pode violar a ordem baixa<média<alta (ou o domínio) e
    precisa ser reparado antes de virar um controlador.
    """
    vetor = np.asarray(vetor, dtype=float)
    if vetor.shape != (N_PARAMS,):
        raise ValueError(f"vetor precisa ter {N_PARAMS} elementos, recebeu shape {vetor.shape}")
    cpu = _repair_grupo(vetor[0:3], *DOMINIO_CPU)
    fila = _repair_grupo(vetor[3:6], *DOMINIO_FILA)
    tendencia = _repair_grupo(vetor[6:9], *DOMINIO_TENDENCIA)
    saida = _repair_grupo(vetor[9:14], *DOMINIO_DELTA)
    return np.concatenate([cpu, fila, tendencia, saida])


def validar(vetor) -> bool:
    """Levanta ValueError com mensagem clara se o vetor for inválido."""
    vetor = np.asarray(vetor, dtype=float)
    if vetor.shape != (N_PARAMS,):
        raise ValueError(f"vetor precisa ter {N_PARAMS} elementos, recebeu shape {vetor.shape}")
    grupos = {
        "cpu": (vetor[0:3], DOMINIO_CPU),
        "fila": (vetor[3:6], DOMINIO_FILA),
        "tendencia": (vetor[6:9], DOMINIO_TENDENCIA),
        "saida": (vetor[9:14], DOMINIO_DELTA),
    }
    for nome, (pontos, (dmin, dmax)) in grupos.items():
        if not np.all(np.diff(pontos) > 0):
            raise ValueError(f"grupo '{nome}' precisa ter pontos estritamente crescentes, recebeu {pontos.tolist()}")
        if pontos.min() < dmin or pontos.max() > dmax:
            raise ValueError(f"grupo '{nome}' fora do domínio [{dmin}, {dmax}]: {pontos.tolist()}")
    return True


def _mfs_entrada(pontos, dmin: float, dmax: float):
    """3 conjuntos (baixo trapézio / médio triângulo / alto trapézio) a
    partir de 3 pontos de corte — ver docs/SPEC.md seção 2."""
    p1, p2, p3 = pontos
    baixo = [dmin, dmin, p1, p2]
    medio = [p1, p2, p3]
    alto = [p2, p3, dmax, dmax]
    return baixo, medio, alto


def _mfs_saida(centros, dmin: float, dmax: float):
    """5 conjuntos a partir de 5 centros — ver docs/SPEC.md seção 2."""
    c1, c2, c3, c4, c5 = centros
    remover_muito = [dmin, dmin, c1, c2]
    remover = [c1, c2, c3]
    manter = [c2, c3, c4]
    adicionar = [c3, c4, c5]
    adicionar_muito = [c4, c5, dmax, dmax]
    return remover_muito, remover, manter, adicionar, adicionar_muito


def _construir_variaveis(vetor: np.ndarray):
    cpu_p, fila_p, tend_p, saida_p = vetor[0:3], vetor[3:6], vetor[6:9], vetor[9:14]

    cpu = ctrl.Antecedent(np.linspace(*DOMINIO_CPU, 201), "cpu")
    fila = ctrl.Antecedent(np.linspace(*DOMINIO_FILA, 201), "fila")
    tendencia = ctrl.Antecedent(np.linspace(*DOMINIO_TENDENCIA, 201), "tendencia")
    delta = ctrl.Consequent(np.linspace(*DOMINIO_DELTA, 201), "delta")

    baixa, media, alta = _mfs_entrada(cpu_p, *DOMINIO_CPU)
    cpu["baixa"] = fuzz.trapmf(cpu.universe, baixa)
    cpu["media"] = fuzz.trimf(cpu.universe, media)
    cpu["alta"] = fuzz.trapmf(cpu.universe, alta)

    pequena, media_fila, grande = _mfs_entrada(fila_p, *DOMINIO_FILA)
    fila["pequena"] = fuzz.trapmf(fila.universe, pequena)
    fila["media"] = fuzz.trimf(fila.universe, media_fila)
    fila["grande"] = fuzz.trapmf(fila.universe, grande)

    caindo, estavel, subindo = _mfs_entrada(tend_p, *DOMINIO_TENDENCIA)
    tendencia["caindo"] = fuzz.trapmf(tendencia.universe, caindo)
    tendencia["estavel"] = fuzz.trimf(tendencia.universe, estavel)
    tendencia["subindo"] = fuzz.trapmf(tendencia.universe, subindo)

    rm, r, m, a, am = _mfs_saida(saida_p, *DOMINIO_DELTA)
    delta["remover_muito"] = fuzz.trapmf(delta.universe, rm)
    delta["remover"] = fuzz.trimf(delta.universe, r)
    delta["manter"] = fuzz.trimf(delta.universe, m)
    delta["adicionar"] = fuzz.trimf(delta.universe, a)
    delta["adicionar_muito"] = fuzz.trapmf(delta.universe, am)

    return cpu, fila, tendencia, delta


def _construir_regras(cpu, fila, tendencia, delta):
    regras = []
    for cpu_label, fila_label, tend_label, delta_label, _nota in TABELA_REGRAS:
        regras.append(
            ctrl.Rule(
                cpu[cpu_label] & fila[fila_label] & tendencia[tend_label],
                delta[delta_label],
            )
        )
    return regras


class ControladorFuzzy:
    """Controlador Mamdani: ``decidir(observacao) -> int`` em [-3, 3].

    ``observacao`` é um dict com as chaves ``cpu``, ``fila`` e ``tendencia``
    (mesmas unidades do SPEC). A saída contínua do centroide só é
    arredondada para inteiro no fim, em ``decidir``.
    """

    def __init__(self, vetor=None):
        self.vetor = VETOR_PADRAO.copy() if vetor is None else repair(np.asarray(vetor, dtype=float))
        validar(self.vetor)
        self.cpu, self.fila, self.tendencia, self.delta = _construir_variaveis(self.vetor)
        self.regras = _construir_regras(self.cpu, self.fila, self.tendencia, self.delta)
        self.sistema = ctrl.ControlSystem(self.regras)
        self._sim = ctrl.ControlSystemSimulation(self.sistema)

    def decidir_continuo(self, observacao: dict) -> float:
        self._sim.input["cpu"] = float(np.clip(observacao["cpu"], *DOMINIO_CPU))
        self._sim.input["fila"] = float(np.clip(observacao["fila"], *DOMINIO_FILA))
        self._sim.input["tendencia"] = float(np.clip(observacao["tendencia"], *DOMINIO_TENDENCIA))
        self._sim.compute()
        return float(self._sim.output["delta"])

    def decidir(self, observacao: dict) -> int:
        return int(np.round(self.decidir_continuo(observacao)))


def controlador_padrao() -> ControladorFuzzy:
    return ControladorFuzzy(None)


def params_to_controller(vetor=None) -> ControladorFuzzy:
    return ControladorFuzzy(vetor)

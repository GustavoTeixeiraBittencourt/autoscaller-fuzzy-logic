"""Loop de malha fechada e avaliação headless.

``simular`` roda o loop completo (observar -> decidir -> avançar) e
devolve o histórico; ``avaliar`` é a versão headless (sem plot) pensada
para ser chamada milhares de vezes pela futura busca por NSGA-II (ver
docs/SPEC.md, seção 7) — por isso devolve só números, nunca abre figura.
``plotar_evolucao`` é o gráfico estático da malha fechada usado no
notebook.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

from environment import Ambiente, ConfigAmbiente, EstadoAmbiente


class Controlador(Protocol):
    def decidir(self, observacao: dict) -> int: ...


@dataclass
class ResultadoSimulacao:
    estados: list[EstadoAmbiente]

    def array(self, campo: str) -> np.ndarray:
        return np.array([getattr(estado, campo) for estado in self.estados])


def simular(
    controlador: Controlador,
    config: Optional[ConfigAmbiente] = None,
    seed: int = 0,
    passos: int = 500,
) -> ResultadoSimulacao:
    ambiente = Ambiente(config=config, seed=seed)
    estados = []
    for _ in range(passos):
        observacao = ambiente.observar()
        delta = controlador.decidir(observacao)
        estados.append(ambiente.avancar(delta))
    return ResultadoSimulacao(estados=estados)


def avaliar(
    controlador: Controlador,
    config: Optional[ConfigAmbiente] = None,
    seed: int = 0,
    passos: int = 500,
) -> dict:
    """Roda a simulação em modo headless e devolve as métricas básicas.

    Determinístico para (controlador, config, seed, passos) fixos — sem
    isso a busca do NSGA-II não conseguiria comparar indivíduos de forma
    justa. `slo_violations` é a fração de passos em violação (não a
    contagem) para já vir normalizada como objetivo de otimização.
    """
    resultado = simular(controlador, config=config, seed=seed, passos=passos)
    violacoes = resultado.array("violacao_slo")
    ns = resultado.array("n")
    deltas = resultado.array("delta_decidido")
    filas = resultado.array("q")
    return {
        "slo_violations": float(violacoes.mean()),
        "cost": float(ns.sum()),
        "fila_maxima": float(filas.max()),
        "num_mudancas_escala": int(np.count_nonzero(deltas)),
    }


def plotar_evolucao(
    resultado: ResultadoSimulacao,
    config: Optional[ConfigAmbiente] = None,
    titulo: str = "",
    salvar_em: Optional[str] = None,
):
    """Gráfico estático (3 painéis: CPU, fila/instância, n) da evolução no
    tempo de uma simulação de malha fechada, com a janela de pico (se
    houver) destacada."""
    import matplotlib.pyplot as plt

    t = resultado.array("t")
    cpu = resultado.array("cpu")
    fila = resultado.array("fila_por_instancia")
    n = resultado.array("n")
    violacao = resultado.array("violacao_slo").astype(bool)

    fig, axs = plt.subplots(3, 1, figsize=(10, 7), sharex=True)

    axs[0].plot(t, cpu, color="tab:blue", linewidth=1)
    if violacao.any():
        axs[0].scatter(t[violacao], cpu[violacao], color="tab:red", s=10, zorder=3, label="violação SLO")
        axs[0].legend(loc="lower right")
    axs[0].set_ylabel("CPU (%)")
    axs[0].set_ylim(-5, 105)

    axs[1].plot(t, fila, color="tab:orange", linewidth=1)
    axs[1].set_ylabel("fila / instância")

    axs[2].step(t, n, where="post", color="tab:green", linewidth=1.5)
    axs[2].set_ylabel("n instâncias")
    axs[2].set_xlabel("passo (t)")

    if config is not None and config.pico_inicio is not None:
        inicio, fim = config.pico_inicio, config.pico_inicio + config.pico_duracao
        for ax in axs:
            ax.axvspan(inicio, fim, color="tab:red", alpha=0.08)

    fig.suptitle(titulo)
    fig.tight_layout()
    if salvar_em:
        fig.savefig(salvar_em, dpi=120)
    return fig

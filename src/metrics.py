"""Métricas de desempenho e tabela comparativa entre controladores.

Ver docs/SPEC.md, seção 5. Usa `simulation.simular` para rodar cada
controlador no mesmo cenário (`ConfigAmbiente`) e seed, de forma que a
comparação seja justa (mesmas chegadas, mesmo pico).
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from environment import ConfigAmbiente
from simulation import Controlador, ResultadoSimulacao, simular

SETPOINT_CPU = 65.0
JANELA_RECUPERACAO = 5  # passos consecutivos abaixo do setpoint para considerar "recuperado"


def tempo_recuperacao(resultado: ResultadoSimulacao, config: Optional[ConfigAmbiente]) -> Optional[float]:
    """Nº de passos entre o fim do pico de tráfego e a CPU voltar a ficar
    abaixo do setpoint por `JANELA_RECUPERACAO` passos consecutivos.
    `None` se não houver pico configurado, ou se o sistema não se
    recuperar dentro da simulação."""
    if config is None or config.pico_inicio is None:
        return None
    fim_pico = config.pico_inicio + config.pico_duracao
    t = resultado.array("t")
    cpu = resultado.array("cpu")
    idx_fim = int(np.searchsorted(t, fim_pico))
    for i in range(idx_fim, len(cpu) - JANELA_RECUPERACAO + 1):
        if np.all(cpu[i : i + JANELA_RECUPERACAO] < SETPOINT_CPU):
            return float(t[i] - fim_pico)
    return None


def calcular_metricas(resultado: ResultadoSimulacao, config: Optional[ConfigAmbiente] = None) -> dict:
    violacao = resultado.array("violacao_slo")
    n = resultado.array("n")
    delta = resultado.array("delta_decidido")
    q = resultado.array("q")
    return {
        "pct_violacao_slo": float(violacao.mean() * 100.0),
        "custo": float(n.sum()),
        "fila_maxima": float(q.max()),
        "num_mudancas_escala": int(np.count_nonzero(delta)),
        "tempo_recuperacao": tempo_recuperacao(resultado, config),
    }


def tabela_comparativa(
    controladores: dict[str, Controlador],
    config: Optional[ConfigAmbiente] = None,
    seed: int = 0,
    passos: int = 500,
) -> dict[str, dict]:
    """Roda cada controlador no mesmo cenário/seed e devolve
    ``{nome_controlador: métricas}``."""
    resultados = {}
    for nome, controlador in controladores.items():
        resultado = simular(controlador, config=config, seed=seed, passos=passos)
        resultados[nome] = calcular_metricas(resultado, config=config)
    return resultados


def formatar_tabela(resultados: dict[str, dict]) -> str:
    """Formata a tabela comparativa como texto alinhado (sem depender de
    pandas), para imprimir no notebook/terminal."""
    colunas = ["pct_violacao_slo", "custo", "fila_maxima", "num_mudancas_escala", "tempo_recuperacao"]
    cabecalho = ["controlador"] + colunas
    linhas = [cabecalho]
    for nome, metricas in resultados.items():
        linha = [nome] + [
            "-" if metricas[c] is None else f"{metricas[c]:.2f}" if isinstance(metricas[c], float) else str(metricas[c])
            for c in colunas
        ]
        linhas.append(linha)
    larguras = [max(len(linha[i]) for linha in linhas) for i in range(len(cabecalho))]
    texto = []
    for linha in linhas:
        texto.append(" | ".join(valor.ljust(largura) for valor, largura in zip(linha, larguras)))
    return "\n".join(texto)

"""Animação em tempo real da malha fechada (bônus): revela, frame a
frame, a mesma evolução de 3 painéis de ``simulation.plotar_evolucao``
(CPU, fila por instância, nº de instâncias).

A simulação é rodada por inteiro primeiro (determinística, dado o seed) e
depois revelada incrementalmente — em vez de simular dentro do callback de
cada frame — para a animação ser reprodutível e poder ser salva em GIF
sem depender de ffmpeg (``PillowWriter``).
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from environment import ConfigAmbiente
from simulation import Controlador, ResultadoSimulacao, simular


def animar_malha_fechada(
    resultado: ResultadoSimulacao,
    config: Optional[ConfigAmbiente] = None,
    titulo: str = "",
    passo_frame: int = 2,
    intervalo_ms: int = 40,
    salvar_em: Optional[str] = None,
):
    """Devolve a ``FuncAnimation`` (e, se ``salvar_em`` for passado, também
    salva — ``.gif`` via ``PillowWriter``, outros formatos via o writer
    padrão do matplotlib para a extensão)."""
    import matplotlib.pyplot as plt
    from matplotlib import animation

    t = resultado.array("t")
    cpu = resultado.array("cpu")
    fila = resultado.array("fila_por_instancia")
    n = resultado.array("n")
    violacao = resultado.array("violacao_slo").astype(bool)

    fig, axs = plt.subplots(3, 1, figsize=(10, 7), sharex=True)

    (linha_cpu,) = axs[0].plot([], [], color="tab:blue", linewidth=1)
    pontos_violacao = axs[0].scatter([], [], color="tab:red", s=10, zorder=3, label="violação SLO")
    axs[0].set_xlim(t[0], t[-1])
    axs[0].set_ylim(-5, 105)
    axs[0].set_ylabel("CPU (%)")
    axs[0].legend(loc="lower right")

    (linha_fila,) = axs[1].plot([], [], color="tab:orange", linewidth=1)
    axs[1].set_xlim(t[0], t[-1])
    axs[1].set_ylim(0, max(float(fila.max()), 1.0) * 1.1)
    axs[1].set_ylabel("fila / instância")

    (linha_n,) = axs[2].step([], [], where="post", color="tab:green", linewidth=1.5)
    axs[2].set_xlim(t[0], t[-1])
    axs[2].set_ylim(0, int(n.max()) + 1)
    axs[2].set_ylabel("n instâncias")
    axs[2].set_xlabel("passo (t)")

    if config is not None and config.pico_inicio is not None:
        inicio, fim = config.pico_inicio, config.pico_inicio + config.pico_duracao
        for ax in axs:
            ax.axvspan(inicio, fim, color="tab:red", alpha=0.08)

    fig.suptitle(titulo)
    fig.tight_layout()

    frames = list(range(1, len(t) + 1, max(1, passo_frame)))
    if frames[-1] != len(t):
        frames.append(len(t))

    def atualizar(k):
        linha_cpu.set_data(t[:k], cpu[:k])
        idx = np.flatnonzero(violacao[:k])
        if len(idx):
            pontos_violacao.set_offsets(np.column_stack([t[idx], cpu[idx]]))
        linha_fila.set_data(t[:k], fila[:k])
        linha_n.set_data(t[:k], n[:k])
        return linha_cpu, pontos_violacao, linha_fila, linha_n

    anim = animation.FuncAnimation(fig, atualizar, frames=frames, interval=intervalo_ms, blit=False)

    if salvar_em:
        if salvar_em.endswith(".gif"):
            fps = max(1, round(1000 / intervalo_ms))
            anim.save(salvar_em, writer=animation.PillowWriter(fps=fps))
        else:
            anim.save(salvar_em)

    return anim


def gerar_gif_demo(
    controlador: Controlador,
    config: Optional[ConfigAmbiente] = None,
    seed: int = 0,
    passos: int = 150,
    salvar_em: str = "docs/demo_malha_fechada.gif",
    titulo: str = "Autoscaler fuzzy — malha fechada (pico de tráfego)",
):
    """Atalho usado no notebook/README: simula e já salva o GIF de
    demonstração."""
    import matplotlib.pyplot as plt

    resultado = simular(controlador, config=config, seed=seed, passos=passos)
    anim = animar_malha_fechada(resultado, config=config, titulo=titulo, salvar_em=salvar_em)
    plt.close(anim._fig)
    return resultado

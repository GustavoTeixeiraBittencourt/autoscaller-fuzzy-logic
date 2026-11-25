"""Painel interno do fuzzy (bônus): mostra, para uma observação específica,
o grau de pertinência ativado em cada conjunto das 3 entradas e o conjunto
agregado de saída (Mamdani) com o centroide marcado.

A inferência (pertinência -> força de disparo -> corte -> agregação ->
centroide) é recalculada aqui "na mão", a partir de ``TABELA_REGRAS`` e dos
universos/termos do próprio ``ControladorFuzzy`` — não da
``ControlSystemSimulation`` interna do skfuzzy — porque isso é o que permite
desenhar os 4 painéis numa única figura. O centroide recalculado bate com
``decidir_continuo`` a menos de um erro de discretização da grade (ver
``tests/test_viz.py``).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import skfuzzy as fuzz

from fuzzy_controller import ControladorFuzzy, TABELA_REGRAS


def _graus_pertinencia(variavel, valor: float) -> dict[str, float]:
    valor = float(np.clip(valor, variavel.universe.min(), variavel.universe.max()))
    return {
        label: float(fuzz.interp_membership(variavel.universe, termo.mf, valor))
        for label, termo in variavel.terms.items()
    }


def inferencia_detalhada(controlador: ControladorFuzzy, observacao: dict) -> dict:
    """Roda a inferência Mamdani passo a passo e devolve todo o estado
    intermediário (graus de pertinência, ativação por regra, conjunto
    agregado e centroide) — o que o painel visual desenha."""
    graus_cpu = _graus_pertinencia(controlador.cpu, observacao["cpu"])
    graus_fila = _graus_pertinencia(controlador.fila, observacao["fila"])
    graus_tendencia = _graus_pertinencia(controlador.tendencia, observacao["tendencia"])

    ativacao = {label: 0.0 for label in controlador.delta.terms}
    regras_disparadas = []
    for cpu_label, fila_label, tend_label, delta_label, nota in TABELA_REGRAS:
        forca = min(graus_cpu[cpu_label], graus_fila[fila_label], graus_tendencia[tend_label])
        if forca > 0:
            regras_disparadas.append((cpu_label, fila_label, tend_label, delta_label, forca, nota))
        ativacao[delta_label] = max(ativacao[delta_label], forca)

    universo_saida = controlador.delta.universe
    agregado = np.zeros_like(universo_saida)
    for label, nivel in ativacao.items():
        cortada = np.fmin(nivel, controlador.delta.terms[label].mf)
        agregado = np.fmax(agregado, cortada)

    if agregado.any():
        centroide = float(fuzz.defuzz(universo_saida, agregado, "centroid"))
    else:
        centroide = float(np.mean(universo_saida))

    regras_disparadas.sort(key=lambda r: r[4], reverse=True)

    return {
        "graus_cpu": graus_cpu,
        "graus_fila": graus_fila,
        "graus_tendencia": graus_tendencia,
        "ativacao_saida": ativacao,
        "agregado_saida": agregado,
        "centroide": centroide,
        "regras_disparadas": regras_disparadas,
    }


def _plotar_entrada(ax, variavel, valor: float, graus: dict[str, float], titulo: str):
    for label, termo in variavel.terms.items():
        (linha,) = ax.plot(variavel.universe, termo.mf, linewidth=1, label=label)
        grau = graus[label]
        if grau > 0:
            ax.fill_between(variavel.universe, 0, np.fmin(grau, termo.mf), color=linha.get_color(), alpha=0.25)
    ax.axvline(valor, color="k", linestyle="--", linewidth=1.5)
    ax.set_ylim(0, 1.05)
    ax.set_title(titulo)
    ax.legend(fontsize=8, loc="upper right", framealpha=0.5)


def _plotar_saida(ax, controlador: ControladorFuzzy, resultado: dict):
    universo = controlador.delta.universe
    for label, termo in controlador.delta.terms.items():
        ax.plot(universo, termo.mf, linewidth=1, linestyle=":", label=label)
    ax.fill_between(universo, 0, resultado["agregado_saida"], color="tab:purple", alpha=0.4, label="agregado")
    ax.axvline(resultado["centroide"], color="k", linestyle="--", linewidth=1.5)
    ax.set_ylim(0, 1.05)
    ax.set_title(f"delta_instancias (centroide = {resultado['centroide']:.2f})")
    ax.legend(fontsize=7, loc="upper right", framealpha=0.5)


def figura_painel_interno(
    controlador: ControladorFuzzy,
    observacao: dict,
    salvar_em: Optional[str] = None,
):
    """Figura 2x2: pertinência ativada em cada entrada (cpu, fila,
    tendencia) e o conjunto agregado de saída com o centroide marcado,
    para uma observação específica."""
    import matplotlib.pyplot as plt

    resultado = inferencia_detalhada(controlador, observacao)

    fig, axs = plt.subplots(2, 2, figsize=(10, 7))
    _plotar_entrada(axs[0, 0], controlador.cpu, observacao["cpu"], resultado["graus_cpu"], "cpu (%)")
    _plotar_entrada(axs[0, 1], controlador.fila, observacao["fila"], resultado["graus_fila"], "fila / instância")
    _plotar_entrada(
        axs[1, 0], controlador.tendencia, observacao["tendencia"], resultado["graus_tendencia"], "tendência"
    )
    _plotar_saida(axs[1, 1], controlador, resultado)

    fig.suptitle(
        f"Painel interno — cpu={observacao['cpu']:.1f}, fila={observacao['fila']:.1f}, "
        f"tendencia={observacao['tendencia']:.1f} -> delta={int(round(resultado['centroide']))}"
    )
    fig.tight_layout()
    if salvar_em:
        fig.savefig(salvar_em, dpi=120)
    return fig

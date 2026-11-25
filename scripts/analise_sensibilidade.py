"""Análise de sensibilidade do controlador fuzzy padrão.

Uso (a partir da raiz do projeto):
    python scripts/analise_sensibilidade.py

Imprime (a) o efeito de variar uma entrada por vez a partir do ponto de
equilíbrio e (b) a fração da variância da saída explicada por cada entrada
em uma grade 15x15x15 sobre os domínios.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from fuzzy_controller import controlador_padrao

DOMINIOS = {"cpu": (0, 100), "fila": (0, 50), "tendencia": (-20, 20)}
BASE = {"cpu": 50, "fila": 15, "tendencia": 0}
N_GRADE = 15

controlador = controlador_padrao()


def saida(cpu, fila, tendencia):
    return controlador.decidir_continuo({"cpu": cpu, "fila": fila, "tendencia": tendencia})


def uma_por_vez():
    print(f"Ponto base {BASE}: saída = {saida(**BASE):.2f}")
    for nome, (a, b) in DOMINIOS.items():
        valores = np.linspace(a, b, 5)
        saidas = [saida(**{**BASE, nome: v}) for v in valores]
        print(f"{nome:10s} entradas={[float(v) for v in valores]} "
              f"saídas={[round(s, 2) for s in saidas]} "
              f"amplitude={max(saidas) - min(saidas):.2f}")


def contribuicao_global():
    eixos = [np.linspace(a, b, N_GRADE) for a, b in DOMINIOS.values()]
    Y = np.array([[[saida(x, y, z) for z in eixos[2]] for y in eixos[1]] for x in eixos[0]])
    total = Y.var()
    print(f"\nGrade {N_GRADE}^3: saída em [{Y.min():.2f}, {Y.max():.2f}], variância total={total:.3f}")
    soma = 0.0
    for i, nome in enumerate(DOMINIOS):
        medias = Y.mean(axis=tuple(j for j in range(3) if j != i))
        fracao = medias.var() / total
        soma += fracao
        print(f"{nome:10s} fração da variância = {fracao:.1%}")
    print(f"{'interações':10s} fração da variância ≈ {1 - soma:.1%}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    uma_por_vez()
    contribuicao_global()

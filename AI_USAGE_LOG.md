# Log de uso de IA generativa

Este arquivo registra, sessão por sessão, como a IA generativa (Claude Code)
foi usada no desenvolvimento deste projeto. Ele alimenta a declaração de uso
de IA que abre o notebook final (`notebooks/projeto_fuzzy.ipynb`).

Autor do projeto: Gustavo Teixeira Bittencourt (CESUPA — Engenharia de
Computação, disciplina de Inteligência Computacional).

Ferramenta utilizada: Claude Code (Anthropic), modelo Claude Sonnet 5
(claude-sonnet-5).

Modo de trabalho: a IA (Claude Code) implementou o código do projeto
(modelagem fuzzy, ambiente, simulação, testes, visualizações) a partir dos
requisitos e decisões de modelagem discutidos com o autor. O autor revisou,
validou e estudou cada decisão antes de aceitá-la — domínios, formas das
funções de pertinência, base de regras, modelo do ambiente e métricas estão
documentados e justificados em `docs/SPEC.md` e `docs/DECISOES.md`
exatamente para permitir essa revisão e para que o autor consiga defender o
trabalho na apresentação sem depender da IA.

Cada entrada abaixo segue o formato:

- **Data:**
- **Fase:**
- **O que a IA gerou/revisou:**
- **O que eu validei ou alterei:**

---

## 2026-11-08 — Setup inicial do projeto

- **Data:** 2026-11-08
- **Fase:** 0 — Setup (estrutura de pastas, ambiente, esqueletos)
- **O que a IA gerou/revisou:**
  - Estrutura de pastas do projeto (`src/`, `src/viz/`, `notebooks/`,
    `tests/`, `docs/`, `outputs/`).
  - Criação do ambiente virtual (`.venv`) e verificação de compatibilidade
    entre `numpy` e `scikit-fuzzy` antes de fixar versões no
    `requirements.txt` (identificou que `scikit-fuzzy==0.5.0` não declara
    `scipy`, `packaging` e `networkx` como dependências no PyPI, apesar de
    precisar delas em runtime — foram adicionadas explicitamente).
  - `requirements.txt` com versões fixadas testadas em Python 3.12.3.
  - `.gitignore` (venv, caches Python/Jupyter, `outputs/` exceto `.gitkeep`).
  - Esqueleto do `README.md`.
  - Este arquivo (`AI_USAGE_LOG.md`).
- **O que eu validei ou alterei:**
  - (preencher após revisão)

---

## 2026-11-24 — SPEC e controlador fuzzy (Fase 1)

- **Data:** 2026-11-24
- **Fase:** 1 — `docs/SPEC.md` e `src/fuzzy_controller.py` + testes
- **O que a IA gerou/revisou:**
  - `docs/SPEC.md`: domínios e unidades das 3 entradas (`cpu`, `fila`,
    `tendencia`) e da saída (`delta_instancias`), formas das funções de
    pertinência e a justificativa de cada uma, critério de construção da
    base de 27 regras (sem buracos, por soma de níveis), modelo do
    ambiente (fila, atraso de provisionamento, SLO), métricas e interface
    pensada para a extensão NSGA-II futura.
  - `src/fuzzy_controller.py`: variáveis fuzzy e base de regras via
    `skfuzzy.control`, Mamdani com defuzzificação por centroide,
    `TABELA_REGRAS` (27 entradas, geradas por construção a partir dos
    níveis das entradas, com notas nas regras mais importantes),
    `params_to_controller(vetor)`, `validar(vetor)` e `repair(vetor)` para
    a futura otimização.
  - `tests/test_fuzzy_controller.py`: cobertura das 27 regras sem buracos
    (grid fino sem NaN/exceção), validação/reparo de vetores de
    parâmetros, equivalência entre configuração manual e
    `params_to_controller`, e verificação de que toda entrada muda a
    saída.
- **O que eu validei ou alterei:**
  - (preencher após revisão)

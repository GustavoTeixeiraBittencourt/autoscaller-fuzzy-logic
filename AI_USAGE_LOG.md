# Log de uso de IA generativa

Este arquivo registra, sessão por sessão, como a IA generativa (Claude Code)
foi usada no desenvolvimento deste projeto. Ele alimenta a declaração de uso
de IA que abre o notebook final (`notebooks/projeto_fuzzy.ipynb`).

Autor do projeto: Gustavo Teixeira Bittencourt (CESUPA — Engenharia de
Computação, disciplina de Inteligência Computacional).

Ferramenta utilizada: Claude Code (Anthropic), modelo Claude Sonnet 5.

Modo de trabalho: a IA atua como mentor/par de programação. A modelagem
fuzzy (variáveis, domínios, conjuntos de pertinência e base de regras) é
definida pelo autor; a IA revisa, aponta inconsistências e gera boilerplate
(estrutura de projeto, esqueletos de função, testes, scripts de plotagem).
Nenhuma regra fuzzy é criada pela IA sem validação explícita do autor.

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

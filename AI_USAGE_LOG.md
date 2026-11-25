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


---

## 2026-11-24 — Loop de malha fechada (Fase 3)

- **Data:** 2026-11-24
- **Fase:** 3 — `src/simulation.py` + testes
- **O que a IA gerou/revisou:**
  - `simulation.py`: `simular()` (loop observar/decidir/avançar),
    `avaliar()` headless e determinístico (fração de passos em violação
    de SLO, custo, fila máxima, nº de mudanças de escala — nomes já
    alinhados com os objetivos da futura extensão NSGA-II) e
    `plotar_evolucao()` (gráfico estático de 3 painéis: CPU, fila por
    instância, nº de instâncias, com a janela de pico destacada).
  - `tests/test_simulation.py`: determinismo de `avaliar`, efeito do pico
    de tráfego e de 2 condições iniciais diferentes nas métricas, e
    geração/salvamento da figura.
- **O que eu validei ou alterei:**
  - (preencher após revisão)

---

## 2026-11-24 — Baselines e métricas (Fase 4)

- **Data:** 2026-11-24
- **Fase:** 4 — `src/baselines.py`, `src/metrics.py` + testes
- **O que a IA gerou/revisou:**
  - `baselines.py`: `ControladorLimiar` (if/else por CPU, estilo
    Kubernetes HPA) e `ControladorPID` (sobre o erro de CPU, setpoint
    65%, saída limitada a [-3,3] para atuar na mesma faixa do fuzzy).
    Ganhos do PID calibrados empiricamente (testes manuais fora da suíte)
    depois que os ganhos iniciais produziram oscilação excessiva
    (`delta` chegando a ±7 por passo).
  - `tests/test_baselines.py`, `tests/test_metrics.py`.
  - Rodada exploratória (fora dos testes) com pico de tráfego comparando
    os 3 controladores — resultado e interpretação registrados em
    `docs/DECISOES.md` (trade-off custo × SLO, motivação da extensão
    futura com NSGA-II).
- **O que eu validei ou alterei:**
   - `metrics.py`: `calcular_metricas` (violação de SLO, custo, fila
    máxima, mudanças de escala, tempo de recuperação pós-pico),
    `tabela_comparativa` e `formatar_tabela` para rodar os 3
    controladores no mesmo cenário/seed.

---

## 2026-11-25 — Painel interno e animação em tempo real (Fase 5)

- **Data:** 2026-11-25
- **Fase:** 5 — `src/viz/inner_panel.py`, `src/viz/realtime.py` + testes
  (bônus)
- **O que a IA gerou/revisou:**
    (diferença < 0.01, atribuída à discretização da grade de 201 pontos).
  - `tests/test_viz.py`: 6 testes (equivalência do centroide manual,
    ordenação das regras disparadas por força, geração/salvamento de
    figura e de GIF).
  - `docs/demo_malha_fechada.gif` e `docs/painel_interno_pico.png` /
    `docs/painel_interno_ocioso.png` gerados a partir desses módulos.
- **O que eu validei ou alterei:**
  - `viz/realtime.py`: animação da malha fechada (`FuncAnimation`)
    revelando frame a frame uma simulação já computada (determinística,
    sem re-simular no callback), salva em GIF via `PillowWriter` (sem
    depender de ffmpeg); `gerar_gif_demo` como atalho.
  - `viz/inner_panel.py`: reimplementação manual (fora da
    `ControlSystemSimulation` do skfuzzy) da inferência Mamdani passo a
    passo — graus de pertinência por entrada, regras disparadas, conjunto
    agregado de saída e centroide — para poder desenhar os 4 painéis numa
    única figura; validado numericamente contra `decidir_continuo`

---

## 2026-11-25 — Notebook final (Fase 6)

- **Data:** 2026-11-25
- **Fase:** 6 — `notebooks/projeto_fuzzy.ipynb`
- **O que a IA gerou/revisou:**
  - Declaração de uso de IA no topo do notebook.
  - 4 casos de teste comentados do controlador fuzzy (ligados às notas de
    `_NOTAS` em `fuzzy_controller.py`: pico de tráfego, ociosidade,
    equilíbrio, combate à oscilação).
  - Evolução no tempo da malha fechada com pico de tráfego e 2 condições
    iniciais (sistema vazio vs. fila acumulada).
  - Painel interno e animação (versão curta renderizada inline via
    `to_jshtml`, GIF completo referenciado de `docs/`).
  - Executado do zero (`jupyter execute`) sem erros antes de salvar, para
    que os resultados já fiquem embutidos no arquivo.
- **O que eu validei ou alterei:**
    - 3 superfícies de controle 3D (malha aberta): `cpu x fila`,
    `cpu x tendencia`, `fila x tendencia`.
     - Tabela comparativa dos 3 controladores (fuzzy, limiar, PID) no mesmo
    cenário/seed.

---

## 2026-11-25 — README final (Fase 7)

- **Data:** 2026-11-25
- **Fase:** 7 — `README.md`
- **O que a IA gerou/revisou:**
  - Seção "Como executar" expandida: suíte de testes, abrir o notebook,
    usar os módulos num script/REPL, e regenerar os assets de `docs/`
    (GIF e painéis internos).
  - Vídeo de apresentação: fica como pendência do autor (roteiro
    preparado à parte, fora do controle de versão por enquanto).
- **O que eu validei ou alterei:**
    - GIF de demonstração como imagem de abertura do README.
    - Checklist de "Status do desenvolvimento" atualizado (fases 5–7
    marcadas).
    - Nova seção "Painel interno do fuzzy (bônus)" com imagem embutida.

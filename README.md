# Autoscaler fuzzy (malha fechada)

> Projeto final — Inteligência Computacional (CESUPA)
> Autor: Gustavo Teixeira Bittencourt

![demo da malha fechada: CPU, fila por instância e nº de instâncias reagindo a um pico de tráfego](docs/demo_malha_fechada.gif)

## Visão geral

Controlador fuzzy (Mamdani) que decide, a cada passo de tempo, quantas
instâncias de um servidor adicionar ou remover, com base no estado
observado do sistema (uso de CPU, tamanho da fila de requisições por
instância, tendência de curto prazo da carga). O ambiente (fila +
instâncias) evolui segundo um modelo determinístico (dado um seed); o
próximo estado realimenta o controlador no passo seguinte, formando a
malha fechada. Dois baselines (if/else por limiar de CPU, estilo
Kubernetes HPA, e PID) servem de referência para comparação.

Descrição detalhada do cenário, das variáveis fuzzy, da base de 27 regras
e do modelo do ambiente está em [`docs/SPEC.md`](docs/SPEC.md); as decisões
de modelagem e sua justificativa (incluindo perguntas prováveis de
apresentação) estão em [`docs/DECISOES.md`](docs/DECISOES.md).

## Estrutura do projeto

```
fuzzy-autoscaler/
├── README.md
├── AI_USAGE_LOG.md
├── requirements.txt
├── src/
│   ├── fuzzy_controller.py     # variáveis, regras, inferência
│   ├── environment.py          # dinâmica do ambiente (fila/instâncias)
│   ├── simulation.py           # loop de realimentação
│   ├── baselines.py            # controladores if/else e PID
│   ├── metrics.py              # métricas de desempenho
│   └── viz/
│       ├── realtime.py         # animação em tempo real
│       └── inner_panel.py      # painel interno do fuzzy (pertinências etc.)
├── notebooks/
│   └── projeto_fuzzy.ipynb
├── tests/
├── docs/                        # figuras, GIF, vídeo
└── outputs/                     # saídas geradas (não versionadas)
```

## Como executar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Rodar a suíte de testes (a partir da raiz do projeto):

```bash
pytest
```

Abrir o notebook final (já executado, com os resultados salvos — basta
abrir para ler, ou rodar `Kernel > Restart & Run All` para reproduzir):

```bash
jupyter notebook notebooks/projeto_fuzzy.ipynb
```

Usar os módulos diretamente em um script/REPL (a partir da raiz, com
`src/` no `PYTHONPATH` — é o que `conftest.py` já faz para os testes e a
primeira célula do notebook faz via `sys.path.insert`):

```python
from environment import ConfigAmbiente
from fuzzy_controller import controlador_padrao
from simulation import simular, plotar_evolucao

cfg = ConfigAmbiente(pico_inicio=80, pico_duracao=30, pico_amplitude=60.0)
resultado = simular(controlador_padrao(), config=cfg, seed=0, passos=200)
plotar_evolucao(resultado, config=cfg, titulo="exemplo").savefig("outputs/evolucao.png")
```

Gerar o GIF de demonstração e os painéis internos em `docs/` (os arquivos
já versionados foram gerados assim):

```python
from environment import ConfigAmbiente
from fuzzy_controller import controlador_padrao
from viz.inner_panel import figura_painel_interno
from viz.realtime import gerar_gif_demo

cfg = ConfigAmbiente(pico_inicio=60, pico_duracao=30, pico_amplitude=60.0)
gerar_gif_demo(controlador_padrao(), config=cfg, seed=1, passos=180, salvar_em="docs/demo_malha_fechada.gif")
figura_painel_interno(controlador_padrao(), {"cpu": 90.0, "fila": 35.0, "tendencia": 14.0},
                      salvar_em="docs/painel_interno_pico.png")
```

## Painel interno do fuzzy (bônus)

`src/viz/inner_panel.py` reconstrói a inferência Mamdani passo a passo
(graus de pertinência de cada entrada, regras disparadas, conjunto
agregado de saída e centroide) para uma observação específica — útil para
inspecionar/explicar uma decisão do controlador. Exemplo com tráfego em
pico (`cpu=90`, `fila=35`, `tendencia=14`, decide `+2`):

![painel interno do fuzzy para um cenário de pico de tráfego](docs/painel_interno_pico.png)

## Status do desenvolvimento

- [x] Fase 0 — Estrutura do projeto, ambiente e dependências
- [x] Fase 1 — Controlador fuzzy Mamdani (`fuzzy_controller.py`) e testes
- [x] Fase 2 — Modelo do ambiente (`environment.py`) e testes
- [x] Fase 3 — Loop de malha fechada (`simulation.py`) e gráficos estáticos
- [x] Fase 4 — Baselines (if/else, PID) e tabela comparativa (`baselines.py`, `metrics.py`)
- [x] Fase 5 — Visualização em tempo real (`viz/realtime.py`) e painel interno do fuzzy (`viz/inner_panel.py`) (bônus)
- [x] Fase 6 — Notebook final (`notebooks/projeto_fuzzy.ipynb`)
- [x] Fase 7 — README completo e declaração de IA (vídeo de demonstração: gravação pendente pelo autor)

## Uso de IA generativa

Este projeto foi desenvolvido com apoio de IA generativa (Claude Code) em
papel par de programação, alem do mais de estar testando o modo de implementação do Spec-Driven-Development(SDD). Detalhes de uso sessão a sessão estão em [`AI_USAGE_LOG.md`](AI_USAGE_LOG.md); a declaração formal consta no
início do notebook final.

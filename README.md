# Autoscaler fuzzy (malha fechada)

> Projeto final — Inteligência Computacional (CESUPA)
> Autor: Gustavo Teixeira Bittencourt

<!-- GIF de demonstração da simulação em tempo real vai aqui (docs/) -->

## Visão geral

Controlador fuzzy (Mamdani) que decide, a cada passo de tempo, quantas
instâncias de um servidor adicionar ou remover, com base no estado
observado do sistema (ex.: uso de CPU, tamanho da fila de requisições,
tendência da carga). O ambiente (fila + instâncias) evolui segundo um
modelo determinístico; o próximo estado realimenta o controlador no passo
seguinte, formando a malha fechada.

*(Descrição detalhada do cenário, variáveis e regras será preenchida na
Fase 1/2 do desenvolvimento.)*

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

*(Instruções de execução da simulação e do notebook serão adicionadas
conforme o projeto avança.)*

## Status do desenvolvimento

- [x] Fase 0 — Estrutura do projeto, ambiente e dependências
- [x] Fase 1 — Controlador fuzzy Mamdani (`fuzzy_controller.py`) e testes
- [ ] Fase 2 — Modelo do ambiente (`environment.py`) e testes
- [ ] Fase 3 — Loop de malha fechada (`simulation.py`) e gráficos estáticos
- [ ] Fase 4 — Baselines (if/else, PID) e tabela comparativa (`baselines.py`, `metrics.py`)
- [ ] Fase 5 — Visualização em tempo real e painel interno do fuzzy (bônus)
- [ ] Fase 6 — Notebook final
- [ ] Fase 7 — README completo, vídeo e declaração de IA

## Uso de IA generativa

Este projeto foi desenvolvido com apoio de IA generativa (Claude Code) em
papel de mentor/par de programação. Detalhes de uso sessão a sessão estão
em [`AI_USAGE_LOG.md`](AI_USAGE_LOG.md); a declaração formal consta no
início do notebook final.

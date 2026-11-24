# SPEC — Autoscaler com Controlador Fuzzy (Mamdani)

## 1. Objetivo

Controlar, a cada passo de tempo discreto, o número de instâncias `n(t)` de
um servidor para manter a fila de requisições sob controle e a CPU numa
faixa saudável, reagindo também à tendência de curto prazo da carga —
usando um controlador fuzzy Mamdani em malha fechada com o ambiente
simulado. Dois controladores de referência (if/else por limiar e PID)
servem de baseline para comparação.

Por que é um problema fuzzy: a decisão "quantas instâncias adicionar"
depende de limiares difusos e combinações de 3 variáveis correlacionadas
(CPU, fila, tendência) — não há um limiar único que separe "ok" de
"sobrecarregado"; a transição é gradual e o operador humano raciocina em
termos como "CPU meio alta, mas a fila tá caindo, então espera". Regras
linguísticas (Mamdani) capturam esse raciocínio melhor que um controlador
PID puro (que só vê uma variável de erro) ou que limiares se/então rígidos
(que oscilam nas bordas).

## 2. Variáveis fuzzy

### Entradas

| Variável | Domínio | Unidade | Conjuntos (forma) |
|---|---|---|---|
| `cpu` | [0, 100] | % utilização média das instâncias | baixa (trapézio 0/0/30/50), média (triângulo 30/50/70), alta (trapézio 50/70/100/100) |
| `fila` | [0, 50] | requisições em espera **por instância** (`q/n`) | pequena (trapézio 0/0/5/15), média (triângulo 5/15/25), grande (trapézio 15/25/50/50) |
| `tendencia` | [-20, 20] | variação suavizada (EMA) da taxa de chegada, req/passo | caindo (trapézio -20/-20/-8/0), estável (triângulo -8/0/8), subindo (trapézio 0/8/20/20) |

Justificativa das formas: extremos usam trapézio (saturam no limite do
domínio — "muito alto" não fica mais "muito alto" além de um ponto) e o
meio usa triângulo (pico único, sem platô, porque "médio"/"estável" é uma
faixa estreita de equilíbrio). Os limites (30/50/70 para CPU, por
exemplo) seguem a prática comum de autoscaling (setpoint de CPU em
60–70%, por isso o conjunto "alta" já cobre a partir de 50% com pico em
70%) e foram ajustados observando a faixa real produzida pelo ambiente
simulado (Fase 3), não escolhidos a priori. `fila` é normalizada por
instância (`q/n`) e não em valor absoluto porque 100 requisições
acumuladas atrás de 10 instâncias é uma situação bem diferente de 100
requisições atrás de 2 — a normalização torna o critério de decisão
independente da escala atual do sistema.

### Saída

| Variável | Domínio | Unidade | Conjuntos (forma) |
|---|---|---|---|
| `delta_instancias` | [-3, 3] | instâncias (arredondado para inteiro após o centroide) | remover_muito (trapézio -3/-3/-2/-1), remover (triângulo -2/-1/0), manter (triângulo -1/0/1), adicionar (triângulo 0/1/2), adicionar_muito (trapézio 1/2/3/3) |

## 3. Base de regras

27 regras (3×3×3), construídas por um critério explícito e verificável —
não "no olho" — para garantir coerência e ausência de buracos:

```
score = nivel(cpu) + nivel(fila) + nivel(tendencia)   # cada nível em {-1, 0, +1}
score <= -2  -> remover_muito
score == -1  -> remover
score ==  0  -> manter
score ==  1  -> adicionar
score >=  2  -> adicionar_muito
```

onde `nivel` é -1 para o conjunto "baixo" de cada entrada (baixa/pequena/
caindo), 0 para o "médio" (média/média/estável) e +1 para o "alto" (alta/
grande/subindo). Essa regra de construção cobre as 27 combinações sem
exceção (teste automático de cobertura na Fase 1: grade fina 50×50×50
nos domínios, nenhuma saída NaN). Regras-chave comentadas no código:

- `cpu=alta, fila=grande, tendencia=subindo -> adicionar_muito` (pico de
  tráfego claro, reage com força máxima)
- `cpu=baixa, fila=pequena, tendencia=caindo -> remover_muito` (ociosidade
  clara, economiza custo)
- `cpu=alta, fila=pequena, tendencia=caindo` (score = 1-1-1=-1) `-> remover`
  — evita oscilação: CPU alta momentânea mas fila vazia e carga já caindo
  não justifica manter capacidade extra
- `cpu=média, fila=média, tendencia=estável -> manter` (ponto de equilíbrio)

Mamdani (em vez de Sugeno) porque as regras foram pensadas em termos
linguísticos simétricos nas 3 entradas e a saída também precisa ser
interpretável/inspecionável no painel interno (bônus) — Sugeno produziria
uma saída numérica direta por regra, perdendo a legibilidade do conjunto
agregado. Defuzzificação por **centroide** (center of gravity) em vez de
`mom`/`bisector` porque é a mais suave: pequenas variações em qualquer
entrada mudam a saída continuamente, importante tanto para a malha de
controle (evita saltos bruscos de `n`) quanto para a futura otimização por
NSGA-II (função objetivo mais bem comportada).

## 4. Ambiente (a "física" da malha fechada)

Passos de tempo discretos `t = 0, 1, 2, ...`.

- `capacidade`: 10 requisições atendidas por instância por passo.
- `n_min = 1`, `n_max = 10` instâncias.
- `chegadas(t) = base + amplitude * sin(2π t / periodo) + Poisson(ruido) [+ pico(t)]`
  — carga "dia/noite" (`base=30`, `amplitude=15`, `periodo=100` passos) +
  ruído Poisson + pico de tráfego configurável (`inicio`, `duracao`,
  `amplitude_pico`).
- `atendidas(t) = min(q(t) + chegadas(t), n(t) * capacidade)`
- `q(t+1) = max(0, q(t) + chegadas(t) - n(t) * capacidade)`
- `cpu(t) = min(100, 100 * atendidas(t) / (n(t) * capacidade))`
- `tendencia(t)`: EMA de `chegadas` (`alpha=0.3`) menos a EMA no passo
  anterior.
- **Atraso de provisionamento**: aumentos de `n` só entram em vigor `k=3`
  passos após a decisão (tempo de boot de uma instância nova); reduções
  são imediatas (desprovisionar é rápido). É esse atraso que torna o
  controle não-trivial — reagir tarde demais a um pico de tráfego custa
  SLO; reagir "forte demais" com antecedência custa dinheiro.
- **SLO**: espera estimada `q(t) / (n(t) * capacidade)` (em passos) acima
  de `limite_slo = 2.0` passos conta como violação no passo `t`.

Controladores compatíveis com a mesma interface `decidir(observacao) ->
delta` (inteiro, antes do clamp de `n_min`/`n_max`):
1. **Fuzzy** (Mamdani, este projeto)
2. **if/else por limiar** (estilo Kubernetes HPA: compara CPU a limites
   fixos)
3. **PID** sobre o erro `setpoint_cpu − cpu(t)` (setpoint 65%)

## 5. Métricas (`metrics.py`)

- `pct_violacao_slo`: % de passos com violação de SLO
- `custo`: soma de `n(t)` ao longo da simulação (proxy de instância×tempo)
- `fila_maxima`: pico de `q(t)`
- `num_mudancas_escala`: nº de passos em que `delta != 0` (proxy de oscilação)
- `tempo_recuperacao`: nº de passos entre o fim do pico de tráfego e o
  momento em que `cpu(t)` volta a ficar abaixo do setpoint de forma
  sustentada (5 passos consecutivos)

## 6. Critérios de aceite (mínimo garantido)

1. `fuzzy_controller.py` com 27 regras, zero NaN/exceção na grade de
   cobertura, e `params_to_controller(vetor)` funcional (com `repair()`).
2. `environment.py` determinístico com seed, testado.
3. `simulation.py` com loop de malha fechada + `avaliar()` headless.
4. Notebook com ≥4 casos de teste comentados + 3 superfícies de controle
   (malha aberta) + gráficos de evolução no tempo com pico de tráfego e
   2 condições iniciais (malha fechada).
5. `AI_USAGE_LOG.md` atualizado por fase e declaração de IA no notebook.

Extras (ordem de prioridade se o tempo apertar): baselines + tabela
comparativa > animação em tempo real > painel interno fuzzy > polimento
do README/vídeo.

## 7. Preparação para a extensão futura (NSGA-II, não implementada agora)

- Todas as funções de pertinência serão parametrizáveis por um vetor
  plano (`params_to_controller(vetor: np.ndarray) -> FuzzyController`),
  além da configuração padrão manual acima.
- `repair(vetor)` corrige violações de ordem (ex.: pico de "baixa" <
  pico de "média" < pico de "alta" em cada variável) e de domínio,
  devolvendo um vetor válido; a validação roda antes de construir o
  controlador e levanta erro claro se não for corrigível.
- `avaliar(controlador, cenario, seed) -> dict` roda a simulação em modo
  headless (sem plot) e devolve as métricas da Seção 5, incluindo
  `slo_violations` e `cost` — nomes que o NSGA-II (dois objetivos) vai
  consumir diretamente.

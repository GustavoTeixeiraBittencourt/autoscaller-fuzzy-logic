# Decisões de modelagem (para estudo/apresentação)

Este arquivo registra, em linguagem simples, cada decisão de modelagem do
projeto: o que foi escolhido, por quê, e qual alternativa foi descartada.
Serve de apoio para eu estudar e defender o trabalho na apresentação, já
que faltei às aulas de fuzzy.

## Fase 1 — Controlador fuzzy

### Por que 3 entradas e não só CPU?

Um autoscaler que olha só para CPU reage tarde: a CPU só sobe depois que a
fila já começou a acumular. `fila` dá um sinal de pressão mais direto (e
atrasado de forma diferente da CPU) e `tendencia` antecipa o que vai
acontecer nos próximos passos. Usar as 3 juntas é o que justifica o fuzzy
em vez de um controlador de uma variável só (ex.: PID simples no erro de
CPU, que é um dos baselines).

### Por que `fila` é normalizada por instância (`q/n`) e não em valor absoluto?

100 requisições na fila atrás de 10 instâncias é tranquilo; 100
requisições atrás de 2 instâncias é colapso. Se eu usasse o valor
absoluto, o controlador precisaria "saber" quantas instâncias existem para
interpretar a fila corretamente — mas isso não é informação fuzzy, é
aritmética, então eu tiro essa conta fora do controlador e entrego a ele
já a grandeza certa (fila por instância).

### Por que trapézio nas pontas e triângulo no meio?

Trapézio nas pontas: depois de um certo ponto, "mais CPU" não é mais
diferente de "muito mais CPU" para a decisão — então a pertinência satura
em 1 (plateau), não cai de novo. Triângulo no meio: "médio"/"estável" é um
estado de equilíbrio estreito, não uma faixa larga — por isso tem um pico
único em vez de um platô.

### Por que os limites são 30/50/70 (CPU), 5/15/25 (fila), -8/0/8 (tendência)?

Para CPU, segui a prática comum de autoscaling: setpoint em torno de
60–70% de utilização, por isso o conjunto "alta" já começa a ganhar peso a
partir de 50% e tem pico em 70%. Para fila e tendência, os valores da Fase
1 são estimativas iniciais plausíveis (fila: poucas requisições por
instância é "pequena", acima de ~25 por instância já é fila grande;
tendência: ±8 req/passo como "mudança perceptível" dado o ruído esperado).
Na Fase 3, depois de rodar o ambiente simulado, confirmei (ou ajustei) esses
limites observando a faixa real de `fila` e `tendencia` produzida, para
garantir que os 3 conjuntos de cada variável realmente se sobrepõem na
faixa de operação normal — ver a atualização desta seção abaixo.

### Por que a base de regras é "soma dos níveis" e não escrita regra a regra?

Porque escrever 27 regras à mão, uma por uma, é fácil de deixar buraco ou
inconsistência (ex.: duas combinações parecidas com saídas contraditórias
sem motivo). Em vez disso, defini um critério único — cada entrada vale
-1 (baixo), 0 (médio) ou +1 (alto); a soma dos 3 níveis (-3 a +3) decide a
categoria de saída. Isso garante, por construção, que: (1) toda combinação
tem exatamente uma regra, (2) regras "parecidas" produzem saídas
"parecidas" (sem contradição), e (3) eu consigo justificar qualquer regra
específica recalculando a soma, em vez de dizer "porque pareceu certo".

### Por que Mamdani e não Sugeno?

Sugeno seria mais rápido computacionalmente (saída é uma função direta das
entradas, sem defuzzificação de um conjunto agregado), mas perde a
inspecionabilidade: o bônus de painel interno mostra o conjunto fuzzy
agregado da saída e o centroide — isso só existe em Mamdani. Como o
projeto pede esse painel e a lauda pede "mostrar que toda entrada muda a
saída" de forma visual, Mamdani é a escolha certa aqui.

### Por que centroide e não `mom`/`bisector`?

Centroide é a defuzzificação mais suave: pequenas mudanças em qualquer
entrada mudam a saída continuamente (sem saltos). Isso importa de duas
formas: (1) na malha fechada, evita que o número de instâncias "pule" de
forma abrupta por uma mudança pequena de CPU; (2) a extensão futura com
NSGA-II otimiza parâmetros das funções de pertinência — uma função objetivo
suave é mais fácil de otimizar do que uma com descontinuidades.

### Por que a saída só é arredondada depois do centroide?

O centroide devolve um número contínuo (ex.: 1.4 instâncias). Arredondar
antes de calcular o centroide (ex.: arredondar cada conjunto de saída)
destruiria a suavidade do resultado; arredondar só no fim é a prática
padrão em controle fuzzy quando a variável de atuação é discreta por
natureza (não dá para ligar "1.4 instância").

## Fase 2 — Ambiente

### Por que `atendidas(t) = min(q(t) + chegadas(t), n(t)·capacidade)` em vez de só `chegadas(t)`?

Porque a fila existe justamente para representar trabalho acumulado: se eu
ignorasse `q(t)` no cálculo de quanto é atendido, a fila nunca
descarregaria mais rápido do que a chegada do próprio passo, mesmo com
capacidade sobrando. Com essa fórmula, quando há capacidade de sobra, o
sistema "come" tanto a fila atrasada quanto a chegada nova do passo.

### Por que o aumento de instâncias tem atraso e a redução não?

Isso imita o mundo real: provisionar uma instância nova (boot, imagem,
health check) leva minutos; desligar uma é imediato. Esse atraso
assimétrico (`atraso_provisionamento=3` passos só para aumentos) é
intencional e é o que torna o problema de controle não-trivial — reagir
tarde a um pico custa violação de SLO, porque a capacidade extra só chega
depois.

### Por que o sistema passa boa parte do tempo com CPU em 100%, mesmo sem pico de tráfego?

Validei isso simulando o controlador fuzzy padrão por 500 passos sem pico
(seed fixo): a CPU fica em 100% cerca de metade do tempo. Isso não é um
bug — é consequência de três escolhas deliberadas: (1) `chegadas(t)` usa
ruído Poisson (desvio padrão ≈ √média), então qualquer número de
instâncias "just right" para a média vai ser insuficiente em ~metade dos
passos só por variância estatística; (2) o controlador fuzzy, do jeito que
foi desenhado, não mantém uma margem de segurança grande (ele reage à CPU
alta, não tenta ficar permanentemente ocioso) porque isso tem custo
(mais instâncias = mais dinheiro); (3) o atraso de provisionamento
atrasa a correção. Decidi manter esse comportamento em vez de "suavizar"
o ambiente para a CPU parecer mais estável, porque é exatamente a tensão
custo×SLO que justifica a extensão futura com NSGA-II (dois objetivos:
violação de SLO e custo) — um controlador hand-tuned "sem noção de custo"
tende a ficar nessa zona de equilíbrio arriscada, e é isso que a
otimização multiobjetivo vai poder corrigir.

### Como validei os domínios de `fila` e `tendencia` (Fase 1 revisitada)?

Rodei o ambiente com o controlador fuzzy padrão (500 passos, sem pico) e
observei: `fila` (por instância) fica em 0 na maior parte do tempo, com
p90 ≈ 11–15 e picos pontuais até ~45–70 — o domínio `[0, 50]` (Fase 1)
cobre bem a faixa normal e satura (sem quebrar) nos picos mais extremos,
o que é aceitável. `tendencia` fica tipicamente entre -2.3 e +2.3 (p10/p90)
no regime sem pico, mas **durante um pico de tráfego realista**
(`pico_amplitude=40`, 30 passos) chega a +9/+13 logo no início do pico —
exatamente a faixa que os conjuntos "subindo"/"caindo" (ponto de corte em
±8) precisam para disparar com força perto do pico, confirmando que os
limites de -8/0/8 (Fase 1) fazem sentido: ficam "quietos" (estável) na
operação normal e disparam justamente quando um pico real começa.

## Perguntas prováveis na apresentação

**P: Por que não usar só um if/else com limiares de CPU, tipo Kubernetes HPA?**
R: É um dos baselines do projeto (`baselines.py`) justamente para comparar.
O problema do if/else é que ele oscila nas bordas dos limiares (ex.: CPU
oscilando entre 69% e 71% com limiar em 70% causa scale up/down repetido) e
não combina múltiplos sinais (fila, tendência) de forma gradual — o fuzzy
combina os 3 sinais com pertinência parcial, suavizando essas bordas.

**P: Por que não um PID simples?**
R: PID (outro baseline) controla bem uma única variável de erro (CPU vs.
setpoint), mas não tem como incorporar fila ou tendência de forma nativa
sem virar um PID multivariável mal-justificado. Fuzzy é a ferramenta
natural para combinar 3 variáveis com faixas difusas e nomes linguísticos.

**P: Como vocês garantem que não existe combinação de entradas sem regra ativa?**
R: A base de regras é gerada por um critério (soma dos níveis das 3
entradas), não escrita manualmente regra a regra, então as 27 combinações
têm cobertura garantida por construção. Isso é testado automaticamente
(`test_cobertura_grid_sem_nan_nem_excecao`): uma varredura fina do espaço
de entrada confere que a saída nunca é NaN nem lança exceção.

**P: Por que a fila é normalizada por instância?**
R: Porque fila absoluta depende de quantas instâncias já existem — 100
requisições atrás de 10 instâncias é bem diferente de atrás de 2. Dividir
pelo número de instâncias torna o critério de decisão independente da
escala atual do sistema.

**P: O que aconteceria se vocês trocassem o centroide por outro método de defuzzificação?**
R: O resultado mudaria de forma suave para pequenos ajustes de entrada
(centroide pondera todo o conjunto agregado), enquanto `mom` (média dos
máximos) ou `bisector` podem produzir saltos quando o conjunto dominante
muda — pior para estabilidade da malha de controle e para a futura
otimização via NSGA-II, que precisa de uma função objetivo bem comportada.

**P: Por que o aumento de instâncias é atrasado e a redução não?**
R: Representa o tempo real de provisionamento (boot de uma VM/container)
versus o desligamento, que é imediato. Esse atraso assimétrico é
justamente o que torna a malha fechada interessante: um controlador que
reage tarde a um pico paga em violação de SLO porque a capacidade extra
só chega alguns passos depois.

**P: Por que o sistema fica com CPU em 100% boa parte do tempo mesmo sem pico?**
R: É esperado dado o ruído Poisson nas chegadas (desvio padrão proporcional
à raiz da média) combinado com um controlador que não mantém margem de
segurança grande — ele reage à sobrecarga, não a evita com antecedência,
porque manter instâncias extras tem custo. Essa tensão custo×SLO é
documentada e é exatamente o que a extensão futura (NSGA-II, dois
objetivos) otimiza.

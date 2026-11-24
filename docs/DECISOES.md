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

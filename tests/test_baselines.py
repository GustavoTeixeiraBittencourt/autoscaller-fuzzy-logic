from baselines import ConfigLimiar, ConfigPID, ControladorLimiar, ControladorPID


def test_limiar_adiciona_acima_do_limite_alto():
    ctrl = ControladorLimiar(ConfigLimiar(limite_baixo=40, limite_alto=70, passo=2))
    assert ctrl.decidir({"cpu": 80, "fila": 0, "tendencia": 0}) == 2


def test_limiar_remove_abaixo_do_limite_baixo():
    ctrl = ControladorLimiar(ConfigLimiar(limite_baixo=40, limite_alto=70, passo=2))
    assert ctrl.decidir({"cpu": 20, "fila": 0, "tendencia": 0}) == -2


def test_limiar_mantem_na_faixa_morta():
    ctrl = ControladorLimiar(ConfigLimiar(limite_baixo=40, limite_alto=70))
    assert ctrl.decidir({"cpu": 55, "fila": 0, "tendencia": 0}) == 0


def test_pid_reage_na_direcao_certa():
    ctrl = ControladorPID(ConfigPID(setpoint=65))
    acima = ctrl.decidir({"cpu": 95, "fila": 0, "tendencia": 0})
    ctrl2 = ControladorPID(ConfigPID(setpoint=65))
    abaixo = ctrl2.decidir({"cpu": 20, "fila": 0, "tendencia": 0})
    assert acima > 0
    assert abaixo < 0


def test_pid_satura_na_saida_max():
    ctrl = ControladorPID(ConfigPID(setpoint=0, kp=10.0, ki=0, kd=0, saida_max=3.0))
    saida = ctrl.decidir({"cpu": 100, "fila": 0, "tendencia": 0})
    assert saida == 3


def test_pid_integra_erro_ao_longo_do_tempo():
    ctrl = ControladorPID(ConfigPID(setpoint=65, kp=0.0, ki=0.05, kd=0.0, saida_max=3.0))
    saidas = [ctrl.decidir({"cpu": 70, "fila": 0, "tendencia": 0}) for _ in range(10)]
    assert saidas[-1] >= saidas[0]

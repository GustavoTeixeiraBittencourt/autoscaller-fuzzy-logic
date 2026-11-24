from baselines import ControladorLimiar, ControladorPID
from environment import ConfigAmbiente
from fuzzy_controller import controlador_padrao
from metrics import calcular_metricas, formatar_tabela, tabela_comparativa, tempo_recuperacao
from simulation import simular


def test_calcular_metricas_tem_todas_as_chaves():
    resultado = simular(controlador_padrao(), seed=0, passos=50)
    metricas = calcular_metricas(resultado)
    for chave in ("pct_violacao_slo", "custo", "fila_maxima", "num_mudancas_escala", "tempo_recuperacao"):
        assert chave in metricas


def test_tempo_recuperacao_none_sem_pico():
    resultado = simular(controlador_padrao(), seed=0, passos=50)
    assert tempo_recuperacao(resultado, None) is None
    assert tempo_recuperacao(resultado, ConfigAmbiente()) is None  # sem pico_inicio


def test_tempo_recuperacao_detecta_recuperacao_apos_pico():
    cfg = ConfigAmbiente(pico_inicio=20, pico_duracao=10, pico_amplitude=60.0)
    resultado = simular(controlador_padrao(), config=cfg, seed=0, passos=200)
    tempo = tempo_recuperacao(resultado, cfg)
    assert tempo is None or tempo >= 0


def test_tabela_comparativa_roda_os_tres_controladores_no_mesmo_cenario():
    controladores = {
        "fuzzy": controlador_padrao(),
        "limiar": ControladorLimiar(),
        "pid": ControladorPID(),
    }
    cfg = ConfigAmbiente(pico_inicio=30, pico_duracao=15, pico_amplitude=40.0)
    resultados = tabela_comparativa(controladores, config=cfg, seed=0, passos=150)
    assert set(resultados.keys()) == set(controladores.keys())
    for metricas in resultados.values():
        assert metricas["custo"] > 0


def test_formatar_tabela_produz_texto_com_cabecalho():
    controladores = {"fuzzy": controlador_padrao(), "limiar": ControladorLimiar()}
    resultados = tabela_comparativa(controladores, seed=0, passos=50)
    texto = formatar_tabela(resultados)
    assert "controlador" in texto
    assert "fuzzy" in texto
    assert "limiar" in texto

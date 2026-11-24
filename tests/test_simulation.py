import os

import numpy as np

from environment import ConfigAmbiente
from fuzzy_controller import controlador_padrao
from simulation import avaliar, plotar_evolucao, simular


def test_simular_roda_o_numero_certo_de_passos():
    resultado = simular(controlador_padrao(), passos=50, seed=0)
    assert len(resultado.estados) == 50
    assert list(resultado.array("t")) == list(range(50))


def test_avaliar_e_deterministico():
    m1 = avaliar(controlador_padrao(), seed=5, passos=100)
    m2 = avaliar(controlador_padrao(), seed=5, passos=100)
    assert m1 == m2


def test_avaliar_devolve_chaves_esperadas():
    metricas = avaliar(controlador_padrao(), seed=0, passos=50)
    for chave in ("slo_violations", "cost", "fila_maxima", "num_mudancas_escala"):
        assert chave in metricas
    assert 0.0 <= metricas["slo_violations"] <= 1.0
    assert metricas["cost"] > 0


def test_pico_de_trafego_aumenta_violacoes_de_slo():
    cfg_base = ConfigAmbiente()
    cfg_pico = ConfigAmbiente(pico_inicio=50, pico_duracao=30, pico_amplitude=60.0)
    sem_pico = avaliar(controlador_padrao(), config=cfg_base, seed=1, passos=150)
    com_pico = avaliar(controlador_padrao(), config=cfg_pico, seed=1, passos=150)
    assert com_pico["fila_maxima"] >= sem_pico["fila_maxima"]


def test_duas_condicoes_iniciais_dao_resultados_diferentes():
    cfg_vazio = ConfigAmbiente(n_inicial=2, q_inicial=0.0)
    cfg_cheio = ConfigAmbiente(n_inicial=2, q_inicial=300.0)
    m_vazio = avaliar(controlador_padrao(), config=cfg_vazio, seed=2, passos=60)
    m_cheio = avaliar(controlador_padrao(), config=cfg_cheio, seed=2, passos=60)
    assert m_vazio["fila_maxima"] != m_cheio["fila_maxima"]


def test_plotar_evolucao_gera_figura_e_pode_salvar(tmp_path):
    cfg = ConfigAmbiente(pico_inicio=20, pico_duracao=10, pico_amplitude=50.0)
    resultado = simular(controlador_padrao(), config=cfg, seed=0, passos=60)
    caminho = tmp_path / "evolucao.png"
    fig = plotar_evolucao(resultado, config=cfg, titulo="teste", salvar_em=str(caminho))
    assert os.path.exists(caminho)
    import matplotlib.pyplot as plt

    plt.close(fig)

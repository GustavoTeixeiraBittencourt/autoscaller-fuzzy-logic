import os

from environment import ConfigAmbiente
from fuzzy_controller import controlador_padrao
from simulation import simular
from viz.inner_panel import figura_painel_interno, inferencia_detalhada
from viz.realtime import animar_malha_fechada, gerar_gif_demo


def test_inferencia_detalhada_bate_com_decidir_continuo():
    """O centroide recalculado na mão (para desenhar o painel) tem que
    bater com a saída real do controlador, a menos de erro de discretização
    da grade de universos (201 pontos)."""
    controlador = controlador_padrao()
    obs = {"cpu": 72.0, "fila": 18.0, "tendencia": 5.0}
    resultado = inferencia_detalhada(controlador, obs)
    assert abs(resultado["centroide"] - controlador.decidir_continuo(obs)) < 0.01


def test_inferencia_detalhada_lista_regras_disparadas_em_ordem_de_forca():
    controlador = controlador_padrao()
    obs = {"cpu": 72.0, "fila": 18.0, "tendencia": 5.0}
    resultado = inferencia_detalhada(controlador, obs)
    forcas = [forca for *_, forca, _ in resultado["regras_disparadas"]]
    assert len(forcas) > 0
    assert forcas == sorted(forcas, reverse=True)


def test_figura_painel_interno_gera_figura_e_pode_salvar(tmp_path):
    import matplotlib.pyplot as plt

    controlador = controlador_padrao()
    obs = {"cpu": 85.0, "fila": 30.0, "tendencia": 10.0}
    caminho = tmp_path / "painel.png"
    fig = figura_painel_interno(controlador, obs, salvar_em=str(caminho))
    assert os.path.exists(caminho)
    plt.close(fig)


def test_animar_malha_fechada_gera_animacao_com_um_frame_por_passo_pedido():
    cfg = ConfigAmbiente(pico_inicio=10, pico_duracao=5, pico_amplitude=40.0)
    resultado = simular(controlador_padrao(), config=cfg, seed=0, passos=30)
    anim = animar_malha_fechada(resultado, config=cfg, passo_frame=5)
    assert len(list(anim.new_frame_seq())) >= 6


def test_animar_malha_fechada_salva_gif(tmp_path):
    import matplotlib.pyplot as plt

    cfg = ConfigAmbiente(pico_inicio=10, pico_duracao=5, pico_amplitude=40.0)
    resultado = simular(controlador_padrao(), config=cfg, seed=0, passos=20)
    caminho = tmp_path / "demo.gif"
    anim = animar_malha_fechada(resultado, config=cfg, passo_frame=5, salvar_em=str(caminho))
    assert os.path.exists(caminho)
    plt.close(anim._fig)


def test_gerar_gif_demo_roda_simulacao_e_salva_arquivo(tmp_path):
    cfg = ConfigAmbiente(pico_inicio=10, pico_duracao=5, pico_amplitude=40.0)
    caminho = tmp_path / "demo_completo.gif"
    resultado = gerar_gif_demo(
        controlador_padrao(), config=cfg, seed=0, passos=20, salvar_em=str(caminho)
    )
    assert os.path.exists(caminho)
    assert len(resultado.estados) == 20

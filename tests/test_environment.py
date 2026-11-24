import numpy as np
import pytest

from environment import Ambiente, ConfigAmbiente


def _rodar(seed, passos, config=None, politica=lambda obs, estado: 0):
    ambiente = Ambiente(config=config, seed=seed)
    registros = []
    for _ in range(passos):
        obs = ambiente.observar()
        delta = politica(obs, ambiente)
        registros.append(ambiente.avancar(delta))
    return registros


def test_determinismo_com_mesmo_seed():
    r1 = _rodar(seed=42, passos=50)
    r2 = _rodar(seed=42, passos=50)
    for a, b in zip(r1, r2):
        assert a == b


def test_seeds_diferentes_produzem_trajetorias_diferentes():
    r1 = _rodar(seed=1, passos=50)
    r2 = _rodar(seed=2, passos=50)
    assert any(a.chegadas != b.chegadas for a, b in zip(r1, r2))


def test_avancar_sem_observar_levanta_erro():
    ambiente = Ambiente(seed=0)
    with pytest.raises(RuntimeError):
        ambiente.avancar(0)


def test_n_respeita_limites():
    cfg = ConfigAmbiente(n_min=2, n_max=4, n_inicial=2, atraso_provisionamento=1)
    registros = _rodar(seed=0, passos=30, config=cfg, politica=lambda obs, amb: 5)
    assert all(2 <= r.n <= 4 for r in registros)

    registros = _rodar(seed=0, passos=10, config=cfg, politica=lambda obs, amb: -5)
    assert all(2 <= r.n <= 4 for r in registros)


def test_reducao_e_imediata_aumento_tem_atraso():
    cfg = ConfigAmbiente(n_min=1, n_max=10, n_inicial=5, atraso_provisionamento=3)
    ambiente = Ambiente(config=cfg, seed=0)

    ambiente.observar()
    estado = ambiente.avancar(-2)
    assert estado.n == 3  # redução imediata

    ambiente.observar()
    estado = ambiente.avancar(2)
    assert estado.n == 3  # aumento ainda não entrou em vigor

    for passos_faltando in (2, 1):
        ambiente.observar()
        estado = ambiente.avancar(0)
        assert estado.n == 3, f"n não deveria mudar com {passos_faltando} passos restantes"

    ambiente.observar()
    estado = ambiente.avancar(0)
    assert estado.n == 5  # atraso_provisionamento=3 passos depois da decisão


def test_fila_cresce_quando_chegadas_excedem_capacidade():
    cfg = ConfigAmbiente(n_min=1, n_max=1, n_inicial=1, capacidade=1.0, base_chegadas=50.0, amplitude_chegadas=0.0)
    registros = _rodar(seed=0, passos=20, config=cfg)
    assert registros[-1].q > registros[0].q


def test_fila_fica_zerada_quando_capacidade_sobra():
    cfg = ConfigAmbiente(n_min=5, n_max=5, n_inicial=5, capacidade=1000.0, base_chegadas=10.0, amplitude_chegadas=0.0)
    registros = _rodar(seed=0, passos=20, config=cfg)
    assert all(r.q == 0.0 for r in registros)


def test_violacao_slo_consistente_com_espera_estimada():
    registros = _rodar(seed=7, passos=100)
    for r in registros:
        assert r.violacao_slo == (r.espera_estimada > ConfigAmbiente().limite_slo)


def test_pico_de_trafego_aumenta_chegadas_na_janela():
    cfg = ConfigAmbiente(
        base_chegadas=30.0, amplitude_chegadas=0.0,
        pico_inicio=10, pico_duracao=5, pico_amplitude=500.0,
    )
    registros = _rodar(seed=0, passos=20, config=cfg)
    chegadas_no_pico = [r.chegadas for r in registros[10:15]]
    chegadas_fora_do_pico = [r.chegadas for r in registros[:10]]
    assert min(chegadas_no_pico) > max(chegadas_fora_do_pico)


def test_duas_condicoes_iniciais_convergem_de_formas_diferentes():
    cfg_vazio = ConfigAmbiente(n_inicial=5, q_inicial=0.0)
    cfg_cheio = ConfigAmbiente(n_inicial=5, q_inicial=500.0)
    r_vazio = _rodar(seed=3, passos=5, config=cfg_vazio)
    r_cheio = _rodar(seed=3, passos=5, config=cfg_cheio)
    assert r_vazio[0].q != r_cheio[0].q

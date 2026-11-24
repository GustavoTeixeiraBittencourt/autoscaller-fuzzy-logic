import itertools

import numpy as np
import pytest

import fuzzy_controller as fc


def test_vetor_padrao_e_valido():
    assert fc.validar(fc.VETOR_PADRAO) is True


def test_tabela_de_regras_tem_27_entradas_sem_buracos():
    assert len(fc.TABELA_REGRAS) == 27
    combinacoes = {(c, f, t) for c, f, t, _, _ in fc.TABELA_REGRAS}
    assert len(combinacoes) == 27  # nenhuma combinação repetida ou faltando
    rotulos_validos = {"remover_muito", "remover", "manter", "adicionar", "adicionar_muito"}
    assert all(d in rotulos_validos for _, _, _, d, _ in fc.TABELA_REGRAS)


@pytest.mark.parametrize(
    "vetor_invalido",
    [
        np.array([1.0, 2.0]),  # tamanho errado
        np.concatenate([[50.0, 30.0, 70.0], fc.VETOR_PADRAO[3:]]),  # fora de ordem
        np.concatenate([[30.0, 50.0, 200.0], fc.VETOR_PADRAO[3:]]),  # fora do domínio
    ],
)
def test_validar_rejeita_vetores_invalidos(vetor_invalido):
    with pytest.raises(ValueError):
        fc.validar(vetor_invalido)


def test_repair_corrige_ordem_e_dominio():
    vetor_bagunçado = np.array(
        [
            70.0, 30.0, 50.0,  # cpu fora de ordem
            25.0, 5.0, 15.0,  # fila fora de ordem
            8.0, -8.0, 0.0,  # tendencia fora de ordem
            2.0, -2.0, 1.0, -1.0, 0.0,  # saida fora de ordem
        ]
    )
    reparado = fc.repair(vetor_bagunçado)
    fc.validar(reparado)  # não deve levantar
    assert np.all(np.diff(reparado[0:3]) > 0)
    assert np.all(np.diff(reparado[3:6]) > 0)
    assert np.all(np.diff(reparado[6:9]) > 0)
    assert np.all(np.diff(reparado[9:14]) > 0)


def test_repair_e_idempotente():
    uma_vez = fc.repair(fc.VETOR_PADRAO + 0.001)
    duas_vezes = fc.repair(uma_vez)
    assert np.allclose(uma_vez, duas_vezes, atol=1e-6)


def test_repair_recorta_pontos_fora_do_dominio():
    vetor_fora = fc.VETOR_PADRAO.copy()
    vetor_fora[2] = 500.0  # cpu p3 bem acima do domínio [0, 100]
    reparado = fc.repair(vetor_fora)
    fc.validar(reparado)
    assert reparado[2] <= fc.DOMINIO_CPU[1]


def test_params_to_controller_default_equivale_ao_manual():
    manual = fc.controlador_padrao()
    via_vetor = fc.params_to_controller(fc.VETOR_PADRAO)
    assert np.array_equal(manual.vetor, via_vetor.vetor)
    obs = {"cpu": 72.0, "fila": 18.0, "tendencia": 5.0}
    assert manual.decidir(obs) == via_vetor.decidir(obs)


def test_decidir_retorna_inteiro_dentro_do_dominio():
    controlador = fc.controlador_padrao()
    casos = [
        {"cpu": 10, "fila": 2, "tendencia": -15},
        {"cpu": 50, "fila": 15, "tendencia": 0},
        {"cpu": 95, "fila": 45, "tendencia": 18},
    ]
    for obs in casos:
        delta = controlador.decidir(obs)
        assert isinstance(delta, int)
        assert fc.DOMINIO_DELTA[0] <= delta <= fc.DOMINIO_DELTA[1]


def test_cobertura_grid_sem_nan_nem_excecao():
    """Varre uma grade fina do espaço de entrada e garante que toda
    combinação ativa alguma regra (sem NaN, sem exceção) — rubrica de
    'regras sem buracos'."""
    controlador = fc.controlador_padrao()
    cpus = np.linspace(*fc.DOMINIO_CPU, 10)
    filas = np.linspace(*fc.DOMINIO_FILA, 10)
    tendencias = np.linspace(*fc.DOMINIO_TENDENCIA, 10)
    for cpu, fila, tendencia in itertools.product(cpus, filas, tendencias):
        obs = {"cpu": cpu, "fila": fila, "tendencia": tendencia}
        valor = controlador.decidir_continuo(obs)
        assert np.isfinite(valor), f"saída não finita para {obs}"


def test_toda_entrada_muda_a_saida():
    """Varia uma entrada por vez, mantendo as outras fixas no ponto neutro,
    e confere que a saída de fato se move (rubrica de modelagem)."""
    controlador = fc.controlador_padrao()
    base = {"cpu": 50.0, "fila": 15.0, "tendencia": 0.0}

    saida_baixa_cpu = controlador.decidir_continuo({**base, "cpu": 5.0})
    saida_alta_cpu = controlador.decidir_continuo({**base, "cpu": 95.0})
    assert saida_baixa_cpu < saida_alta_cpu

    saida_fila_pequena = controlador.decidir_continuo({**base, "fila": 1.0})
    saida_fila_grande = controlador.decidir_continuo({**base, "fila": 45.0})
    assert saida_fila_pequena < saida_fila_grande

    saida_tend_caindo = controlador.decidir_continuo({**base, "tendencia": -18.0})
    saida_tend_subindo = controlador.decidir_continuo({**base, "tendencia": 18.0})
    assert saida_tend_caindo < saida_tend_subindo


def test_extremos_batem_com_intuicao_de_escala():
    controlador = fc.controlador_padrao()
    tudo_baixo = controlador.decidir({"cpu": 0.0, "fila": 0.0, "tendencia": -20.0})
    tudo_alto = controlador.decidir({"cpu": 100.0, "fila": 50.0, "tendencia": 20.0})
    neutro = controlador.decidir({"cpu": 50.0, "fila": 15.0, "tendencia": 0.0})
    assert tudo_baixo < 0
    assert tudo_alto > 0
    assert neutro == 0

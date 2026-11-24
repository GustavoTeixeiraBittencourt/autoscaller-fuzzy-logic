"""Ambiente simulado (fila + instâncias) — a "física" da malha fechada.

Ver docs/SPEC.md, seção 4, para as equações e a justificativa de cada
parâmetro. Uso típico em um passo de simulação:

    obs = ambiente.observar()          # {"cpu":..., "fila":..., "tendencia":...}
    delta = controlador.decidir(obs)
    estado = ambiente.avancar(delta)   # aplica a decisão e evolui a fila

``observar()`` tem que ser chamado antes de ``avancar()`` em cada passo
(nessa ordem) — é o que garante que a observação vista pelo controlador e
o estado realmente processado nesse passo usam o mesmo valor de
``chegadas(t)``, sem sortear ruído duas vezes para o mesmo instante.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

ALPHA_TENDENCIA = 0.3  # suavização da EMA usada para estimar a tendência


@dataclass
class ConfigAmbiente:
    capacidade: float = 10.0  # requisições atendidas por instância por passo
    n_min: int = 1
    n_max: int = 10
    n_inicial: int = 3
    q_inicial: float = 0.0
    atraso_provisionamento: int = 3  # passos até um aumento de n entrar em vigor

    base_chegadas: float = 30.0
    amplitude_chegadas: float = 15.0
    periodo: int = 100  # passos de um ciclo "dia/noite"

    limite_slo: float = 2.0  # espera estimada (em passos) acima disso = violação

    # pico de tráfego opcional
    pico_inicio: Optional[int] = None
    pico_duracao: int = 0
    pico_amplitude: float = 0.0


@dataclass
class EstadoAmbiente:
    t: int
    q: float
    n: int
    cpu: float
    chegadas: float
    atendidas: float
    tendencia: float
    espera_estimada: float
    violacao_slo: bool
    fila_por_instancia: float
    delta_decidido: int


class Ambiente:
    """Simulação determinística (dado um seed) da dinâmica fila/instâncias."""

    def __init__(self, config: Optional[ConfigAmbiente] = None, seed: int = 0):
        self.cfg = config or ConfigAmbiente()
        self.rng = np.random.default_rng(seed)
        self.t = 0
        self.q = float(self.cfg.q_inicial)
        self.n = int(self.cfg.n_inicial)
        self._pendentes: list[tuple[int, int]] = []  # (t_aplicacao, quantidade)
        self._ema_chegadas: Optional[float] = None

        self._obs_pronta_para_t: Optional[int] = None
        self._chegadas_atual = 0.0
        self._cpu_atual = 0.0
        self._atendidas_atual = 0.0
        self._tendencia_atual = 0.0

    def _media_chegadas(self, t: int) -> float:
        cfg = self.cfg
        media = cfg.base_chegadas + cfg.amplitude_chegadas * np.sin(2 * np.pi * t / cfg.periodo)
        if cfg.pico_inicio is not None and cfg.pico_inicio <= t < cfg.pico_inicio + cfg.pico_duracao:
            media += cfg.pico_amplitude
        return max(media, 0.0)

    def _atualizar_tendencia(self, chegadas: float) -> float:
        ema_anterior = self._ema_chegadas if self._ema_chegadas is not None else chegadas
        ema_novo = ALPHA_TENDENCIA * chegadas + (1 - ALPHA_TENDENCIA) * ema_anterior
        self._ema_chegadas = ema_novo
        return ema_novo - ema_anterior

    def observar(self) -> dict:
        """Calcula e devolve a observação (cpu, fila, tendencia) do passo
        atual, para o controlador decidir. Sorteia `chegadas(t)` uma única
        vez por passo — o valor é reaproveitado por `avancar`."""
        chegadas = self.rng.poisson(self._media_chegadas(self.t))
        atendidas = min(self.q + chegadas, self.n * self.cfg.capacidade)
        cpu = min(100.0, 100.0 * atendidas / (self.n * self.cfg.capacidade))
        tendencia = self._atualizar_tendencia(chegadas)

        self._chegadas_atual = float(chegadas)
        self._atendidas_atual = atendidas
        self._cpu_atual = cpu
        self._tendencia_atual = tendencia
        self._obs_pronta_para_t = self.t

        return {"cpu": cpu, "fila": self.q / self.n, "tendencia": tendencia}

    def avancar(self, delta: int) -> EstadoAmbiente:
        """Aplica a decisão `delta` (clamp em n_min/n_max; aumentos só
        entram em vigor após `atraso_provisionamento` passos, reduções são
        imediatas) e evolui a fila para o próximo passo."""
        if self._obs_pronta_para_t != self.t:
            raise RuntimeError("chame observar() antes de avancar() em cada passo")

        cfg = self.cfg
        pendentes_restantes = []
        for t_aplicacao, quantidade in self._pendentes:
            if t_aplicacao <= self.t:
                self.n = int(np.clip(self.n + quantidade, cfg.n_min, cfg.n_max))
            else:
                pendentes_restantes.append((t_aplicacao, quantidade))
        self._pendentes = pendentes_restantes

        if delta > 0:
            self._pendentes.append((self.t + cfg.atraso_provisionamento, delta))
        elif delta < 0:
            self.n = int(np.clip(self.n + delta, cfg.n_min, cfg.n_max))

        espera_estimada = self.q / (self.n * cfg.capacidade)
        estado = EstadoAmbiente(
            t=self.t,
            q=self.q,
            n=self.n,
            cpu=self._cpu_atual,
            chegadas=self._chegadas_atual,
            atendidas=self._atendidas_atual,
            tendencia=self._tendencia_atual,
            espera_estimada=espera_estimada,
            violacao_slo=espera_estimada > cfg.limite_slo,
            fila_por_instancia=self.q / self.n,
            delta_decidido=delta,
        )

        self.q = max(0.0, self.q + self._chegadas_atual - self.n * cfg.capacidade)
        self.t += 1
        self._obs_pronta_para_t = None
        return estado

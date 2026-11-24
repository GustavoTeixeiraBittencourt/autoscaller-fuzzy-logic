"""Controladores de referência (baselines), mesma interface do fuzzy:
``decidir(observacao) -> int``. Usados em `metrics.py` para comparar com
o controlador fuzzy nos mesmos cenários e seeds (ver docs/SPEC.md, seção 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class ConfigLimiar:
    """Limiares de CPU no estilo Kubernetes HPA."""

    limite_baixo: float = 40.0
    limite_alto: float = 70.0
    passo: int = 1


class ControladorLimiar:
    """if/else por limiar de CPU: acima do limite alto, adiciona `passo`
    instâncias; abaixo do limite baixo, remove `passo`; no meio, mantém."""

    def __init__(self, config: Optional[ConfigLimiar] = None):
        self.cfg = config or ConfigLimiar()

    def decidir(self, observacao: dict) -> int:
        cpu = observacao["cpu"]
        if cpu > self.cfg.limite_alto:
            return self.cfg.passo
        if cpu < self.cfg.limite_baixo:
            return -self.cfg.passo
        return 0


@dataclass
class ConfigPID:
    setpoint: float = 65.0  # % de CPU
    kp: float = 0.025
    ki: float = 0.004
    kd: float = 0.015
    integral_max: float = 50.0  # anti-windup
    saida_max: float = 3.0  # mesma faixa de atuação do delta fuzzy ([-3, 3])


class ControladorPID:
    """PID sobre o erro `cpu(t) - setpoint`: erro positivo (CPU acima do
    setpoint) empurra a saída para adicionar instâncias. Saída limitada a
    [-saida_max, saida_max] para atuar na mesma faixa do controlador fuzzy
    (comparação justa entre os dois)."""

    def __init__(self, config: Optional[ConfigPID] = None):
        self.cfg = config or ConfigPID()
        self._integral = 0.0
        self._erro_anterior: Optional[float] = None

    def decidir(self, observacao: dict) -> int:
        cfg = self.cfg
        erro = observacao["cpu"] - cfg.setpoint

        self._integral = float(np.clip(self._integral + erro, -cfg.integral_max, cfg.integral_max))
        derivada = 0.0 if self._erro_anterior is None else erro - self._erro_anterior
        self._erro_anterior = erro

        saida = cfg.kp * erro + cfg.ki * self._integral + cfg.kd * derivada
        saida = float(np.clip(saida, -cfg.saida_max, cfg.saida_max))
        return int(np.round(saida))

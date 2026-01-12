"""
Adapter for simple JSON signals from external tools.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ultimate_wealth.ultimate_modular.types import AdapterSignal
from ultimate_wealth.ultimate_modular.utils import load_json


class JsonSignalAdapter:
    def __init__(self, name: str, path: Path, enabled: bool) -> None:
        self.name = name
        self.path = path
        self.enabled = enabled

    def get_signal(self, data, index, signal_type_cls) -> Optional[AdapterSignal]:
        if not self.enabled:
            return None
        payload = load_json(self.path)
        if not payload:
            return None

        signal_raw = str(payload.get("signal", "")).lower()
        bias = payload.get("bias")
        confidence = float(payload.get("confidence", 0.5))
        bias_value = 0.0
        if bias == 1 or bias == "1":
            bias_value = 1.0
        elif bias == -1 or bias == "-1":
            bias_value = -1.0

        if signal_raw in {"buy", "long", "bull"} or bias_value == 1.0:
            signal_type = signal_type_cls.BUY
            signal_value = 1.0
        elif signal_raw in {"sell", "short", "bear"} or bias_value == -1.0:
            signal_type = signal_type_cls.SELL
            signal_value = -1.0
        else:
            return AdapterSignal(
                signal_type_cls.HOLD,
                0.0,
                f"{self.name} signal=none",
                self.name,
                {
                    "confidence": float(confidence),
                    "bias": float(bias_value),
                    "signal": 0.0,
                },
            )

        reason = f"{self.name} signal={signal_raw or bias}"
        return AdapterSignal(
            signal_type,
            min(0.9, max(0.1, confidence)),
            reason,
            self.name,
            {
                "confidence": float(confidence),
                "bias": float(bias_value),
                "signal": float(signal_value),
            },
        )

"""
Adapter for qiquan_bisai options strategy signals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from ultimate_wealth.ultimate_modular.types import AdapterSignal
from ultimate_wealth.ultimate_modular.utils import ensure_repo_on_path


class QiquanStrategyAdapter:
    def __init__(self, config) -> None:
        self.enabled = bool(getattr(config, "ENABLE_QIQUAN_STRATEGY", False))
        self.price_path = Path(getattr(config, "QIQUAN_PRICE_PATH", ""))
        self.events_path = Path(getattr(config, "QIQUAN_EVENTS_PATH", ""))
        self.iv_risk_off = float(getattr(config, "QIQUAN_IV_RISK_OFF", 0.7))
        self._prepared = False
        self._signals_by_date: Dict[object, AdapterSignal] = {}

    def _prepare(self, signal_type_cls) -> None:
        ensure_repo_on_path()
        try:
            from qiquan_bisai.strategy_sim import read_price_series, read_events, simple_trend_signal

            series = read_price_series(str(self.price_path))
            events = read_events(str(self.events_path))

            for idx, (when, _) in enumerate(series):
                trend = simple_trend_signal(series, idx)
                if trend == "call":
                    base_signal = signal_type_cls.BUY
                    trend_value = 1.0
                elif trend == "put":
                    base_signal = signal_type_cls.SELL
                    trend_value = -1.0
                else:
                    base_signal = signal_type_cls.HOLD
                    trend_value = 0.0

                confidence = 0.55 if trend_value != 0.0 else 0.0
                reason = f"qiquan trend={trend or 'none'}"

                iv_value = 0.0
                event = events.get(when.date())
                if event and event.get("iv"):
                    try:
                        iv_value = float(event["iv"])
                    except ValueError:
                        iv_value = 0.0
                    if iv_value >= self.iv_risk_off and trend_value != 0.0:
                        base_signal = signal_type_cls.SELL
                        confidence = min(0.85, confidence + 0.2)
                        reason = f"{reason} iv_risk_off={iv_value:.2f}"

                indicators = {
                    "trend": trend_value,
                    "iv": float(iv_value),
                    "iv_risk_off": float(self.iv_risk_off),
                }

                self._signals_by_date[when.date()] = AdapterSignal(
                    base_signal,
                    confidence,
                    reason,
                    "qiquan_bisai",
                    indicators,
                )
        except Exception:
            self._signals_by_date = {}

        self._prepared = True

    def get_signal(self, data, index, signal_type_cls) -> Optional[AdapterSignal]:
        if not self.enabled:
            return None
        if not self._prepared:
            self._prepare(signal_type_cls)
        if not self._signals_by_date:
            return None
        current_date = data.index[index].date()
        return self._signals_by_date.get(current_date)

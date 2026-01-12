"""
Adapter for spread_strategy signals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ultimate_wealth.ultimate_modular.types import AdapterSignal
from ultimate_wealth.ultimate_modular.utils import ensure_repo_on_path


class SpreadStrategyAdapter:
    def __init__(self, config) -> None:
        self.enabled = bool(getattr(config, "ENABLE_SPREAD_STRATEGY", False))
        self.data_path = Path(getattr(config, "SPREAD_DATA_PATH", ""))
        self.upper = float(getattr(config, "SPREAD_UPPER", 5.0))
        self.lower = float(getattr(config, "SPREAD_LOWER", -5.0))
        self._prepared = False
        self._latest_signal: Optional[AdapterSignal] = None
        self._latest_indicators: Optional[dict[str, float]] = None

    def _prepare(self, signal_type_cls) -> None:
        ensure_repo_on_path()
        from spread_strategy.brent_wti_strategy import load_prices

        try:
            prices = load_prices(self.data_path)
        except Exception:
            self._prepared = True
            return

        if not prices:
            self._prepared = True
            return

        latest = prices[-1]
        spread = latest.spread
        self._latest_indicators = {
            "spread": float(spread),
            "upper": float(self.upper),
            "lower": float(self.lower),
        }
        if spread > self.upper:
            self._latest_signal = AdapterSignal(
                signal_type_cls.SELL,
                0.6,
                f"spread {spread:.2f} > upper {self.upper:.2f}",
                "spread_strategy",
                self._latest_indicators,
            )
        elif spread < self.lower:
            self._latest_signal = AdapterSignal(
                signal_type_cls.BUY,
                0.6,
                f"spread {spread:.2f} < lower {self.lower:.2f}",
                "spread_strategy",
                self._latest_indicators,
            )

        self._prepared = True

    def get_signal(self, data, index, signal_type_cls) -> Optional[AdapterSignal]:
        if not self.enabled:
            return None
        if not self._prepared:
            self._prepare(signal_type_cls)
        if self._latest_signal:
            return self._latest_signal
        if self._latest_indicators:
            return AdapterSignal(
                signal_type_cls.HOLD,
                0.0,
                "spread_strategy in_range",
                "spread_strategy",
                self._latest_indicators,
            )
        return None

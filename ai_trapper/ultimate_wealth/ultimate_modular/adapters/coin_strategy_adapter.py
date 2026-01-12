"""
Adapter for coin_strategy signals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from ultimate_wealth.ultimate_modular.types import AdapterSignal
from ultimate_wealth.ultimate_modular.utils import ensure_repo_on_path


class CoinStrategyAdapter:
    def __init__(self, config) -> None:
        self.enabled = bool(getattr(config, "ENABLE_COIN_STRATEGY", False))
        self.price_path = Path(getattr(config, "COIN_PRICE_PATH", ""))
        self.sentiment_path = Path(getattr(config, "COIN_SENTIMENT_PATH", ""))
        self._prepared = False
        self._signals_by_date: Dict[object, tuple[int, Optional[str]]] = {}

    def _prepare(self) -> None:
        ensure_repo_on_path()
        try:
            from coin_strategy.strategy_engine import read_price_series, read_sentiment, compute_signal
            prices = read_price_series(str(self.price_path))
            sentiment_map = read_sentiment(str(self.sentiment_path))

            for idx, bar in enumerate(prices):
                sentiment = sentiment_map.get(bar.date.date())
                score, side = compute_signal(prices, idx, sentiment)
                self._signals_by_date[bar.date.date()] = (score, side)
        except Exception:
            self._signals_by_date = {}

        self._prepared = True

    def get_signal(self, data, index, signal_type_cls) -> Optional[AdapterSignal]:
        if not self.enabled:
            return None

        if not self._prepared:
            self._prepare()

        if not self._signals_by_date:
            return None

        current_date = data.index[index].date()
        if current_date not in self._signals_by_date:
            return None

        score, side = self._signals_by_date[current_date]
        indicators = {
            "score": float(score),
            "side": 1.0 if side == "long" else -1.0 if side == "short" else 0.0,
        }

        if side == "long":
            signal_type = signal_type_cls.BUY
        elif side == "short":
            signal_type = signal_type_cls.SELL
        else:
            return AdapterSignal(
                signal_type_cls.HOLD,
                0.0,
                f"coin_strategy score={score} side=none",
                "coin_strategy",
                indicators,
            )

        confidence = min(0.9, max(0.1, score / 3.0))
        reason = f"coin_strategy score={score} side={side}"
        return AdapterSignal(signal_type, confidence, reason, "coin_strategy", indicators)

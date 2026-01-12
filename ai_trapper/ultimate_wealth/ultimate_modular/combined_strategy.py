"""
Combined strategy that aggregates signals from multiple subprojects.
"""
from __future__ import annotations

from typing import List

from ultimate_wealth.ultimate_modular.adapters.coin_strategy_adapter import CoinStrategyAdapter
from ultimate_wealth.ultimate_modular.adapters.ai_headhunter_adapter import AIHeadhunterAdapter
from ultimate_wealth.ultimate_modular.adapters.smc_adapter import SMCStrategyAdapter
from ultimate_wealth.ultimate_modular.adapters.spread_strategy_adapter import SpreadStrategyAdapter
from ultimate_wealth.ultimate_modular.adapters.qiquan_strategy_adapter import QiquanStrategyAdapter
from ultimate_wealth.ultimate_modular.adapters.trendradar_adapter import TrendRadarAdapter
from ultimate_wealth.ultimate_modular.adapters.json_signal_adapter import JsonSignalAdapter
from ultimate_wealth.ultimate_modular.types import AdapterSignal
from ultimate_wealth.ultimate_modular.utils import ensure_repo_on_path


class CombinedStrategy:
    def __init__(self, config) -> None:
        self.config = config
        ensure_repo_on_path()

        from ai_trapper.gold_strategy import GoldTradingStrategy, SignalType, TradingSignal

        self.SignalType = SignalType
        self.TradingSignal = TradingSignal
        self.base_strategy = GoldTradingStrategy(config)

        self.adapters = [
            CoinStrategyAdapter(config),
            SpreadStrategyAdapter(config),
            QiquanStrategyAdapter(config),
            SMCStrategyAdapter(config),
            TrendRadarAdapter(config),
            JsonSignalAdapter("xueqiu", config.XUEQIU_SIGNAL_PATH, config.ENABLE_XUEQIU),
            JsonSignalAdapter("x_scraper", config.X_SCRAPER_SIGNAL_PATH, config.ENABLE_X_SCRAPER),
            JsonSignalAdapter("ai_hedge_fund", config.HEDGE_FUND_SIGNAL_PATH, config.ENABLE_AI_HEDGE_FUND),
            AIHeadhunterAdapter(config),
        ]

    def _combine_scores(self, base_signal: AdapterSignal, extra_signals: List[AdapterSignal]) -> AdapterSignal:
        weights = {
            "base": self.config.WEIGHT_BASE,
            "coin_strategy": self.config.WEIGHT_COIN,
            "spread_strategy": self.config.WEIGHT_SPREAD,
            "qiquan_bisai": self.config.WEIGHT_QIQUAN,
            "jinshJ_index": self.config.WEIGHT_SMC,
            "trendradar": self.config.WEIGHT_TRENDRADAR,
            "xueqiu": self.config.WEIGHT_XUEQIU,
            "x_scraper": self.config.WEIGHT_X_SCRAPER,
            "ai_hedge_fund": self.config.WEIGHT_AI_HEDGE_FUND,
            "ai_headhunter": self.config.WEIGHT_AI_HEADHUNTER,
        }

        score = 0.0
        reasons = [base_signal.reason]
        score += base_signal.signal_type.value * base_signal.confidence * weights["base"]

        for signal in extra_signals:
            weight = weights.get(signal.source, 0.0)
            score += signal.signal_type.value * signal.confidence * weight
            if signal.signal_type != self.SignalType.HOLD:
                reasons.append(signal.reason)

        if abs(score) < self.config.COMBINE_THRESHOLD:
            signal_type = self.SignalType.HOLD
        elif score > 0:
            signal_type = self.SignalType.BUY
        else:
            signal_type = self.SignalType.SELL

        confidence = min(0.95, max(0.1, abs(score)))
        reason = " | ".join(reasons)
        return AdapterSignal(signal_type, confidence, reason, "combined")

    def generate_composite_signal(self, data, index):
        if self.config.ENABLE_AI_TRAPPER_BASE:
            base = self.base_strategy.generate_composite_signal(data, index)
            base_signal = AdapterSignal(
                base.signal_type,
                base.confidence,
                base.reason,
                "base",
            )
            timestamp = base.timestamp
            price = base.price
            indicators = dict(base.indicators or {})
        else:
            timestamp = data.index[index]
            price = float(data.iloc[index]["Close"])
            indicators = {}
            base_signal = AdapterSignal(
                self.SignalType.HOLD,
                0.0,
                "base_disabled",
                "base",
            )

        extra_signals = []
        for adapter in self.adapters:
            signal = adapter.get_signal(data, index, self.SignalType)
            if signal:
                extra_signals.append(signal)
                if signal.indicators:
                    for key, value in signal.indicators.items():
                        indicators[f"{signal.source}_{key}"] = value

        combined = self._combine_scores(base_signal, extra_signals)
        return self.TradingSignal(
            timestamp=timestamp,
            signal_type=combined.signal_type,
            price=price,
            confidence=combined.confidence,
            indicators=indicators,
            reason=combined.reason,
        )

    def should_exit_position(self, data, index, entry_price, entry_signal_type):
        should_exit, reason = self.base_strategy.should_exit_position(
            data, index, entry_price, entry_signal_type
        )
        if should_exit:
            return should_exit, reason

        current = self.generate_composite_signal(data, index)
        if current.signal_type != self.SignalType.HOLD and current.signal_type != entry_signal_type:
            if current.confidence >= 0.7:
                return True, f"opposite_signal {current.reason}"
        return False, ""

"""
Adapter for jinshJ_index SMC-style structural signals.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from ultimate_wealth.ultimate_modular.types import AdapterSignal
from ultimate_wealth.ultimate_modular.utils import ensure_repo_on_path


class SMCStrategyAdapter:
    def __init__(self, config) -> None:
        self.enabled = bool(getattr(config, "ENABLE_SMC_STRATEGY", False))
        self.lookback = int(getattr(config, "SMC_LOOKBACK_BARS", 400))
        self.swing_window = int(getattr(config, "SMC_SWING_WINDOW", 3))

    def get_signal(self, data, index, signal_type_cls) -> Optional[AdapterSignal]:
        if not self.enabled:
            return None

        ensure_repo_on_path()
        try:
            from jinshJ_index.plot_gold_smc import find_swings, detect_bos_ch
        except Exception:
            return None

        if index < self.swing_window * 2:
            return None

        start = max(0, index - self.lookback)
        window = data.iloc[start : index + 1]
        df = pd.DataFrame(
            {
                "open": window["Open"].values,
                "high": window["High"].values,
                "low": window["Low"].values,
                "close": window["Close"].values,
            }
        )

        swing_highs, swing_lows = find_swings(df, window=self.swing_window)
        bos_list, ch_list = detect_bos_ch(df, swing_highs, swing_lows)

        if not bos_list:
            return None

        last_bos = bos_list[-1]
        direction_up = df["close"].iloc[last_bos] >= df["open"].iloc[last_bos]
        signal_type = signal_type_cls.BUY if direction_up else signal_type_cls.SELL
        confidence = 0.55
        direction_label = "up" if direction_up else "down"
        reason = f"smc bos={direction_label}"
        indicators = {
            "bos_dir": 1.0 if direction_up else -1.0,
            "ch_recent": 0.0,
        }

        if ch_list and ch_list[-1] >= max(0, len(df) - 5):
            confidence = 0.45
            reason = f"{reason} ch_recent"
            indicators["ch_recent"] = 1.0

        return AdapterSignal(signal_type, confidence, reason, "jinshJ_index", indicators)

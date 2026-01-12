"""
Adapter for TrendRadar offline text output signals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ultimate_wealth.ultimate_modular.types import AdapterSignal


class TrendRadarAdapter:
    def __init__(self, config) -> None:
        self.enabled = bool(getattr(config, "ENABLE_TRENDRADAR", False))
        self.output_dir = Path(getattr(config, "TRENDRADAR_OUTPUT_DIR", ""))
        self.bull_words = tuple(getattr(config, "TRENDRADAR_BULL_WORDS", ()))
        self.bear_words = tuple(getattr(config, "TRENDRADAR_BEAR_WORDS", ()))
        self.min_score = int(getattr(config, "TRENDRADAR_MIN_SCORE", 2))

    def _latest_text(self) -> Optional[str]:
        if not self.output_dir.exists():
            return None
        candidates = list(self.output_dir.rglob("*.txt"))
        if not candidates:
            return None
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        try:
            return latest.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

    def get_signal(self, data, index, signal_type_cls) -> Optional[AdapterSignal]:
        if not self.enabled:
            return None

        text = self._latest_text()
        if not text:
            return None

        text_lower = text.lower()
        bull_score = sum(text_lower.count(word) for word in self.bull_words)
        bear_score = sum(text_lower.count(word) for word in self.bear_words)
        score = bull_score - bear_score

        indicators = {
            "bull_score": float(bull_score),
            "bear_score": float(bear_score),
            "score": float(score),
        }

        if abs(score) < self.min_score:
            return AdapterSignal(
                signal_type_cls.HOLD,
                0.0,
                f"trendradar score={score} (bull={bull_score}, bear={bear_score})",
                "trendradar",
                indicators,
            )

        signal_type = signal_type_cls.BUY if score > 0 else signal_type_cls.SELL
        confidence = min(0.8, 0.4 + abs(score) * 0.1)
        reason = f"trendradar score={score} (bull={bull_score}, bear={bear_score})"
        return AdapterSignal(signal_type, confidence, reason, "trendradar", indicators)

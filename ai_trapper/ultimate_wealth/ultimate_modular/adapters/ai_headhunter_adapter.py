"""
Adapter for ai_headhunter indicators (non-trading, indicator-only).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ultimate_wealth.ultimate_modular.types import AdapterSignal


class AIHeadhunterAdapter:
    def __init__(self, config) -> None:
        self.enabled = bool(getattr(config, "ENABLE_AI_HEADHUNTER", False))
        self.data_path = Path(getattr(config, "AI_HEADHUNTER_DATA_PATH", ""))
        self._prepared = False
        self._signal: Optional[AdapterSignal] = None

    def _prepare(self, signal_type_cls) -> None:
        if not self.data_path.exists():
            self._prepared = True
            return

        try:
            payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._prepared = True
            return

        if not isinstance(payload, list):
            self._prepared = True
            return

        count = float(len(payload))
        if count == 0:
            self._prepared = True
            return

        total_exp = 0.0
        total_skills = 0.0
        for item in payload:
            try:
                total_exp += float(item.get("experience", 0) or 0)
            except (TypeError, ValueError):
                total_exp += 0.0
            skills = item.get("skills") or []
            if isinstance(skills, list):
                total_skills += float(len(skills))

        indicators = {
            "candidate_count": count,
            "avg_experience": total_exp / count,
            "avg_skill_count": total_skills / count,
        }

        self._signal = AdapterSignal(
            signal_type_cls.HOLD,
            0.0,
            "ai_headhunter indicators",
            "ai_headhunter",
            indicators,
        )
        self._prepared = True

    def get_signal(self, data, index, signal_type_cls) -> Optional[AdapterSignal]:
        if not self.enabled:
            return None
        if not self._prepared:
            self._prepare(signal_type_cls)
        return self._signal

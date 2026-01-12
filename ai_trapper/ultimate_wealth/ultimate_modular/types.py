"""
Shared types for adapters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class AdapterSignal:
    signal_type: Any
    confidence: float
    reason: str
    source: str
    indicators: Dict[str, float] = field(default_factory=dict)

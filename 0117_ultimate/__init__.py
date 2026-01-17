"""
究极策略 (Ultimate Strategy)
整合多个优秀量化交易策略的终极回测系统
"""

__version__ = "1.0.0"
__author__ = "HUG_AI Team"

from .config import UltimateConfig
from .data_handler import DataHandler
from .backtest_engine import BacktestEngine
from .performance_analyzer import PerformanceAnalyzer
from .ultimate_strategy import UltimateStrategy

__all__ = [
    'UltimateConfig',
    'DataHandler',
    'BacktestEngine',
    'PerformanceAnalyzer',
    'UltimateStrategy',
]

"""
顽主杯松松交易策略量化实现
基于松松的短线交易策略，包括选股、买卖信号生成和风险控制
"""

__version__ = "1.0.0"
__author__ = "AI Trapper"

from .strategy.songsong_strategy import SongSongStrategy
from .strategy.stock_selector import StockSelector
from .strategy.signal_generator import SignalGenerator
from .strategy.risk_manager import RiskManager

__all__ = [
    'SongSongStrategy',
    'StockSelector', 
    'SignalGenerator',
    'RiskManager'
]

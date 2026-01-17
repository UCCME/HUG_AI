"""
Saber 慢牛双模组期权策略系统
Slow Bull Options Matrix Strategy

核心理念：在加密货币慢牛行情中，通过期权价差组合降低成本并提高盈亏比
适用标的：BTC、ETH 等具有高流动性期权链的加密资产
"""

__version__ = '1.0.0'
__author__ = 'AI Trapper Team'

from saber.strategy.saber_strategy import SaberStrategy
from saber.config.strategy_config import StrategyConfig

__all__ = ['SaberStrategy', 'StrategyConfig']

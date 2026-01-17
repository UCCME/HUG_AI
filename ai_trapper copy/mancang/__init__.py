"""
满仓大佬交易策略系统
A股趋势跟随与回调低吸策略

核心理念：本金安全第一，盈利第二
适用标的：A股市场主线题材龙头股、新股（IPO）
操作周期：短线（持仓通常3-5天）
"""

__version__ = '1.0.0'
__author__ = 'AI Trapper Team'

from mancang.strategy.mancang_strategy import MancangStrategy
from mancang.config.strategy_config import StrategyConfig

__all__ = ['MancangStrategy', 'StrategyConfig']

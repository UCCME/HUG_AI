"""
可插拔式策略配置
支持动态配置策略组合
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class StrategyConfig:
    """单个策略配置"""
    name: str  # 策略名称（工厂注册名）
    weight: float = 1.0  # 策略权重
    enabled: bool = True  # 是否启用
    params: Dict[str, Any] = field(default_factory=dict)  # 策略参数


@dataclass
class PluggableConfig:
    """可插拔式配置类"""
    
    # ==================== 基础配置 ====================
    INITIAL_CAPITAL: float = 100000.0
    COMMISSION_RATE: float = 0.002
    SLIPPAGE: float = 0.001
    
    # ==================== 数据源配置 ====================
    DATA_PROVIDER: str = "yfinance"
    SYMBOL: str = "GC=F"
    LOCAL_DATA_PATH: str = "../XAU_5m_data.csv"
    
    # ==================== 策略组合配置 ====================
    # 信号决策参数
    SIGNAL_THRESHOLD: float = 0.18  # 综合信号触发阈值
    MIN_SIGNAL_COUNT: int = 2  # 最小信号数量
    
    # 策略列表配置
    STRATEGIES: List[StrategyConfig] = field(default_factory=lambda: [
        # 基础技术指标策略
        StrategyConfig(
            name='ma',
            weight=0.25,
            enabled=True,
            params={'fast_period': 72, 'slow_period': 216}
        ),
        StrategyConfig(
            name='rsi',
            weight=0.15,
            enabled=True,
            params={'period': 14, 'oversold': 30, 'overbought': 70}
        ),
        StrategyConfig(
            name='macd',
            weight=0.20,
            enabled=True,
            params={'fast': 12, 'slow': 26, 'signal': 9}
        ),
        StrategyConfig(
            name='bollinger',
            weight=0.10,
            enabled=True,
            params={'period': 20, 'std_dev': 2.0}
        ),
        StrategyConfig(
            name='volume',
            weight=0.05,
            enabled=True,
            params={'volume_threshold': 1.5, 'price_change_threshold': 0.01}
        ),
        
        # 高级策略
        StrategyConfig(
            name='stoch_rsi',
            weight=0.10,
            enabled=True,
            params={'period': 14, 'k_period': 3, 'd_period': 3, 'oversold': 20, 'overbought': 80}
        ),
        StrategyConfig(
            name='ut_bot',
            weight=0.10,
            enabled=True,
            params={'atr_period': 10, 'key_value': 1.2}
        ),
        StrategyConfig(
            name='smc',
            weight=0.05,
            enabled=True,
            params={'swing_window': 3, 'ob_lookback': 10}
        ),
    ])
    
    # ==================== 风险控制配置 ====================
    STOP_LOSS_PCT: float = 0.05
    TAKE_PROFIT_PCT: float = 0.10
    ATR_STOP_MULTIPLIER: float = 2.0
    ATR_TAKE_PROFIT_MULTIPLIER: float = 3.0
    TRAILING_STOP_ENABLED: bool = True
    TRAILING_STOP_ACTIVATION: float = 0.03
    TRAILING_STOP_DISTANCE: float = 0.02
    TIME_STOP_DAYS: int = 7
    
    # ==================== 仓位管理配置 ====================
    POSITION_SIZE: float = 0.95
    MAX_POSITION_PCT: float = 0.10
    RISK_PER_TRADE: float = 0.01
    ROLL_ATTACK_RATIO: float = 0.30
    ROLL_DEFENSE_RATIO: float = 0.70
    ROLL_TRIGGER_PCT: float = 0.08
    
    # ==================== 回测配置 ====================
    START_DATE: str = None
    END_DATE: str = None
    LOG_TRADES: bool = True
    TRADES_LOG_PATH: str = "0117_ultimate/trades_log.txt"
    PLOT_RESULTS: bool = True
    
    def get_enabled_strategies(self) -> List[StrategyConfig]:
        """获取已启用的策略配置"""
        return [s for s in self.STRATEGIES if s.enabled]
    
    def enable_strategy(self, name: str):
        """启用策略"""
        for strategy in self.STRATEGIES:
            if strategy.name == name:
                strategy.enabled = True
                return
        raise ValueError(f"未找到策略: {name}")
    
    def disable_strategy(self, name: str):
        """禁用策略"""
        for strategy in self.STRATEGIES:
            if strategy.name == name:
                strategy.enabled = False
                return
        raise ValueError(f"未找到策略: {name}")
    
    def set_strategy_weight(self, name: str, weight: float):
        """设置策略权重"""
        for strategy in self.STRATEGIES:
            if strategy.name == name:
                strategy.weight = weight
                return
        raise ValueError(f"未找到策略: {name}")
    
    def add_strategy(self, strategy_config: StrategyConfig):
        """添加策略"""
        self.STRATEGIES.append(strategy_config)
    
    def remove_strategy(self, name: str):
        """移除策略"""
        self.STRATEGIES = [s for s in self.STRATEGIES if s.name != name]
    
    def print_config(self):
        """打印配置信息"""
        print("\n" + "=" * 60)
        print("⚙️  可插拔式策略配置")
        print("=" * 60)
        print(f"初始资金: ${self.INITIAL_CAPITAL:,.2f}")
        print(f"数据源: {self.DATA_PROVIDER}")
        print(f"交易品种: {self.SYMBOL}")
        print(f"\n信号决策:")
        print(f"  - 信号阈值: {self.SIGNAL_THRESHOLD}")
        print(f"  - 最小信号数: {self.MIN_SIGNAL_COUNT}")
        print(f"\n已启用策略 ({len(self.get_enabled_strategies())}/{len(self.STRATEGIES)}):")
        for i, strategy in enumerate(self.get_enabled_strategies(), 1):
            print(f"  {i}. {strategy.name} - 权重: {strategy.weight:.2f}")
        print("=" * 60)


# 创建全局配置实例
pluggable_config = PluggableConfig()


# ==================== 预设配置方案 ====================

def get_conservative_config() -> PluggableConfig:
    """保守型配置：注重风险控制"""
    config = PluggableConfig()
    config.STOP_LOSS_PCT = 0.03
    config.TAKE_PROFIT_PCT = 0.08
    config.POSITION_SIZE = 0.70
    config.SIGNAL_THRESHOLD = 0.25  # 更高的信号阈值
    config.MIN_SIGNAL_COUNT = 3  # 需要更多信号确认
    
    # 只启用基础策略
    for strategy in config.STRATEGIES:
        if strategy.name in ['ma', 'rsi', 'macd']:
            strategy.enabled = True
            strategy.weight = 0.33
        else:
            strategy.enabled = False
    
    return config


def get_balanced_config() -> PluggableConfig:
    """平衡型配置：默认配置"""
    return PluggableConfig()


def get_aggressive_config() -> PluggableConfig:
    """激进型配置：追求收益"""
    config = PluggableConfig()
    config.STOP_LOSS_PCT = 0.08
    config.TAKE_PROFIT_PCT = 0.15
    config.POSITION_SIZE = 0.95
    config.SIGNAL_THRESHOLD = 0.15  # 更低的信号阈值
    config.MIN_SIGNAL_COUNT = 2
    
    # 启用所有策略
    for strategy in config.STRATEGIES:
        strategy.enabled = True
    
    return config


def get_trend_following_config() -> PluggableConfig:
    """趋势跟踪配置：专注趋势策略"""
    config = PluggableConfig()
    
    # 只启用趋势相关策略
    for strategy in config.STRATEGIES:
        if strategy.name in ['ma', 'macd', 'ut_bot', 'smc']:
            strategy.enabled = True
            strategy.weight = 0.25
        else:
            strategy.enabled = False
    
    return config


def get_mean_reversion_config() -> PluggableConfig:
    """均值回归配置：专注超买超卖"""
    config = PluggableConfig()
    
    # 只启用均值回归策略
    for strategy in config.STRATEGIES:
        if strategy.name in ['rsi', 'bollinger', 'stoch_rsi']:
            strategy.enabled = True
            strategy.weight = 0.33
        else:
            strategy.enabled = False
    
    return config

"""
策略工厂
负责策略的创建、注册和管理
"""
from typing import Dict, Type, List, Optional
from strategies.base_strategy import BaseStrategy
from strategies.ma_strategy import MAStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.volume_strategy import VolumeStrategy
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ut_bot_strategy import UTBotStrategy
from strategies.smc_strategy import SMCStrategy


class StrategyFactory:
    """
    策略工厂类
    使用注册机制管理所有可用策略
    """
    
    # 策略注册表
    _registry: Dict[str, Type[BaseStrategy]] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: Type[BaseStrategy]):
        """
        注册策略
        
        Args:
            name: 策略名称
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise TypeError(f"{strategy_class} 必须继承自 BaseStrategy")
        cls._registry[name] = strategy_class
        print(f"✅ 策略已注册: {name}")
    
    @classmethod
    def unregister(cls, name: str):
        """注销策略"""
        if name in cls._registry:
            del cls._registry[name]
            print(f"❌ 策略已注销: {name}")
    
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseStrategy:
        """
        创建策略实例
        
        Args:
            name: 策略名称
            **kwargs: 策略参数
            
        Returns:
            BaseStrategy: 策略实例
        """
        if name not in cls._registry:
            raise ValueError(f"未找到策略: {name}。可用策略: {list(cls._registry.keys())}")
        
        strategy_class = cls._registry[name]
        return strategy_class(**kwargs)
    
    @classmethod
    def create_multiple(cls, configs: List[Dict]) -> List[BaseStrategy]:
        """
        批量创建策略实例
        
        Args:
            configs: 策略配置列表，每个配置包含 name 和参数
            
        Returns:
            List[BaseStrategy]: 策略实例列表
        """
        strategies = []
        for config in configs:
            name = config.pop('name')
            strategy = cls.create(name, **config)
            strategies.append(strategy)
        return strategies
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """获取所有可用策略名称"""
        return list(cls._registry.keys())
    
    @classmethod
    def get_strategy_info(cls, name: str) -> Dict:
        """获取策略信息"""
        if name not in cls._registry:
            raise ValueError(f"未找到策略: {name}")
        
        strategy_class = cls._registry[name]
        return {
            'name': name,
            'class': strategy_class.__name__,
            'doc': strategy_class.__doc__,
        }
    
    @classmethod
    def list_strategies(cls):
        """列出所有已注册的策略"""
        print("\n" + "=" * 60)
        print("📋 已注册的策略列表")
        print("=" * 60)
        for i, (name, strategy_class) in enumerate(cls._registry.items(), 1):
            print(f"{i}. {name}")
            print(f"   类名: {strategy_class.__name__}")
            print(f"   说明: {strategy_class.__doc__.strip() if strategy_class.__doc__ else '无'}")
        print("=" * 60)


# 自动注册所有内置策略
def register_builtin_strategies():
    """注册所有内置策略"""
    StrategyFactory.register('ma', MAStrategy)
    StrategyFactory.register('rsi', RSIStrategy)
    StrategyFactory.register('macd', MACDStrategy)
    StrategyFactory.register('bollinger', BollingerStrategy)
    StrategyFactory.register('volume', VolumeStrategy)
    StrategyFactory.register('stoch_rsi', StochRSIStrategy)
    StrategyFactory.register('ut_bot', UTBotStrategy)
    StrategyFactory.register('smc', SMCStrategy)


# 模块加载时自动注册
register_builtin_strategies()

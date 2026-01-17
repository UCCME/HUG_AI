"""
可插拔式策略使用示例
演示如何灵活配置和组合策略
"""
from pluggable_config import PluggableConfig, StrategyConfig
from strategy_factory import StrategyFactory
from strategy_composer import StrategyComposer
from data_handler import DataHandler
import pandas as pd


def example_1_list_strategies():
    """示例1：列出所有可用策略"""
    print("\n" + "=" * 60)
    print("示例1：列出所有可用策略")
    print("=" * 60)
    
    StrategyFactory.list_strategies()


def example_2_create_single_strategy():
    """示例2：创建单个策略"""
    print("\n" + "=" * 60)
    print("示例2：创建单个策略")
    print("=" * 60)
    
    # 创建MA策略
    ma_strategy = StrategyFactory.create(
        'ma',
        weight=0.5,
        enabled=True,
        fast_period=50,
        slow_period=200
    )
    
    print(f"策略信息: {ma_strategy}")
    print(f"所需指标: {ma_strategy.get_required_indicators()}")
    print(f"策略参数: {ma_strategy.get_params()}")


def example_3_create_strategy_composer():
    """示例3：创建策略组合器"""
    print("\n" + "=" * 60)
    print("示例3：创建策略组合器")
    print("=" * 60)
    
    # 创建多个策略
    strategies = [
        StrategyFactory.create('ma', weight=0.4, fast_period=72, slow_period=216),
        StrategyFactory.create('rsi', weight=0.3, oversold=30, overbought=70),
        StrategyFactory.create('macd', weight=0.3, fast=12, slow=26, signal=9),
    ]
    
    # 创建组合器
    composer = StrategyComposer(
        strategies=strategies,
        signal_threshold=0.2,
        min_signal_count=2
    )
    
    composer.print_info()


def example_4_dynamic_strategy_management():
    """示例4：动态策略管理"""
    print("\n" + "=" * 60)
    print("示例4：动态策略管理")
    print("=" * 60)
    
    # 创建配置
    config = PluggableConfig()
    
    print("初始配置:")
    config.print_config()
    
    # 禁用某个策略
    print("\n禁用 volume 策略...")
    config.disable_strategy('volume')
    
    # 修改策略权重
    print("修改 ma 策略权重为 0.35...")
    config.set_strategy_weight('ma', 0.35)
    
    # 添加新策略
    print("添加自定义策略...")
    config.add_strategy(StrategyConfig(
        name='rsi',
        weight=0.25,
        enabled=True,
        params={'period': 21, 'oversold': 25, 'overbought': 75}
    ))
    
    print("\n修改后配置:")
    config.print_config()


def example_5_preset_configs():
    """示例5：使用预设配置"""
    print("\n" + "=" * 60)
    print("示例5：使用预设配置")
    print("=" * 60)
    
    from pluggable_config import (
        get_conservative_config,
        get_aggressive_config,
        get_trend_following_config
    )
    
    configs = {
        '保守型': get_conservative_config(),
        '激进型': get_aggressive_config(),
        '趋势跟踪': get_trend_following_config()
    }
    
    for name, config in configs.items():
        print(f"\n{name}配置:")
        print(f"  止损: {config.STOP_LOSS_PCT:.1%}")
        print(f"  止盈: {config.TAKE_PROFIT_PCT:.1%}")
        print(f"  仓位: {config.POSITION_SIZE:.1%}")
        print(f"  启用策略: {[s.name for s in config.get_enabled_strategies()]}")


def example_6_custom_strategy_combination():
    """示例6：自定义策略组合"""
    print("\n" + "=" * 60)
    print("示例6：自定义策略组合")
    print("=" * 60)
    
    # 创建自定义配置
    config = PluggableConfig()
    
    # 清空默认策略
    config.STRATEGIES = []
    
    # 添加自定义策略组合
    config.add_strategy(StrategyConfig(
        name='ma',
        weight=0.5,
        enabled=True,
        params={'fast_period': 50, 'slow_period': 200}
    ))
    
    config.add_strategy(StrategyConfig(
        name='rsi',
        weight=0.3,
        enabled=True,
        params={'period': 14, 'oversold': 25, 'overbought': 75}
    ))
    
    config.add_strategy(StrategyConfig(
        name='ut_bot',
        weight=0.2,
        enabled=True,
        params={'atr_period': 10, 'key_value': 1.5}
    ))
    
    print("自定义策略组合:")
    config.print_config()


def example_7_strategy_weight_optimization():
    """示例7：策略权重优化"""
    print("\n" + "=" * 60)
    print("示例7：策略权重优化示例")
    print("=" * 60)
    
    # 创建策略组合器
    strategies = [
        StrategyFactory.create('ma', weight=0.3),
        StrategyFactory.create('rsi', weight=0.3),
        StrategyFactory.create('macd', weight=0.4),
    ]
    
    composer = StrategyComposer(strategies=strategies)
    
    print("初始权重:")
    print(composer.get_strategy_weights())
    
    # 调整权重
    print("\n调整权重...")
    composer.set_strategy_weight('MA_Strategy', 0.4)
    composer.set_strategy_weight('RSI_Strategy', 0.2)
    composer.set_strategy_weight('MACD_Strategy', 0.4)
    
    print("\n调整后权重:")
    print(composer.get_strategy_weights())


def example_8_enable_disable_strategies():
    """示例8：启用/禁用策略"""
    print("\n" + "=" * 60)
    print("示例8：启用/禁用策略")
    print("=" * 60)
    
    strategies = [
        StrategyFactory.create('ma', weight=0.25),
        StrategyFactory.create('rsi', weight=0.25),
        StrategyFactory.create('macd', weight=0.25),
        StrategyFactory.create('bollinger', weight=0.25),
    ]
    
    composer = StrategyComposer(strategies=strategies)
    
    print(f"初始启用策略数: {len(composer.get_enabled_strategies())}")
    
    # 禁用某些策略
    print("\n禁用 bollinger 策略...")
    composer.disable_strategy('Bollinger_Strategy')
    
    print(f"当前启用策略数: {len(composer.get_enabled_strategies())}")
    print(f"启用的策略: {[s.name for s in composer.get_enabled_strategies()]}")
    
    # 重新启用
    print("\n重新启用 bollinger 策略...")
    composer.enable_strategy('Bollinger_Strategy')
    
    print(f"当前启用策略数: {len(composer.get_enabled_strategies())}")


if __name__ == "__main__":
    print("🎯 可插拔式策略使用示例")
    print("=" * 60)
    
    examples = [
        ("列出所有可用策略", example_1_list_strategies),
        ("创建单个策略", example_2_create_single_strategy),
        ("创建策略组合器", example_3_create_strategy_composer),
        ("动态策略管理", example_4_dynamic_strategy_management),
        ("使用预设配置", example_5_preset_configs),
        ("自定义策略组合", example_6_custom_strategy_combination),
        ("策略权重优化", example_7_strategy_weight_optimization),
        ("启用/禁用策略", example_8_enable_disable_strategies),
    ]
    
    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    choice = input("\n请选择要运行的示例 (1-8, 或 'all' 运行所有): ").strip()
    
    if choice.lower() == 'all':
        for name, func in examples:
            func()
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        examples[int(choice) - 1][1]()
    else:
        print("❌ 无效选项")

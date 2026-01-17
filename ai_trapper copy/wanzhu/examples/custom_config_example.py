"""
自定义配置示例
演示如何使用不同的配置模式运行策略
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wanzhu.strategy.songsong_strategy import SongSongStrategy
from wanzhu.config.strategy_config import (
    StrategyConfig,
    AGGRESSIVE_CONFIG,
    CONSERVATIVE_CONFIG,
    CONVERTIBLE_BOND_CONFIG
)


def run_with_mode(mode_name: str, custom_config: dict):
    """
    使用指定模式运行策略
    
    Args:
        mode_name: 模式名称
        custom_config: 自定义配置
    """
    print(f"\n{'='*60}")
    print(f"运行模式: {mode_name}")
    print(f"{'='*60}")
    
    # 获取基础配置
    config = StrategyConfig.get_config(mode='backtest')
    
    # 合并自定义配置
    for key, value in custom_config.items():
        if key in config and isinstance(value, dict):
            config[key].update(value)
        else:
            config[key] = value
    
    # 打印关键配置
    print(f"\n关键配置:")
    print(f"  最大仓位: {config['risk']['max_position_ratio']*100:.0f}%")
    print(f"  止损比例: {config['risk']['max_single_loss_pct']*100:.2f}%")
    print(f"  每日最大交易数: {config['risk']['max_daily_trades']}")
    print(f"  市场情绪阈值: {config['risk']['market_sentiment_threshold']}")
    
    # 初始化并运行策略
    strategy = SongSongStrategy(config)
    
    results = strategy.run(
        start_date=config['backtest']['start_date'],
        end_date=config['backtest']['end_date']
    )
    
    # 输出结果摘要
    if len(results) > 0:
        final_value = results.iloc[-1]['total_value']
        initial_value = config['initial_capital']
        total_return = (final_value - initial_value) / initial_value
        
        print(f"\n结果摘要:")
        print(f"  总收益率: {total_return*100:.2f}%")
        
        report = strategy.get_performance_report()
        print(f"  胜率: {report['胜率']}")
        print(f"  夏普比率: {report['夏普比率']}")


def main():
    """主函数"""
    
    print("=" * 60)
    print("松松策略 - 多配置模式对比")
    print("=" * 60)
    
    # 1. 标准半仓滚动模式（默认）
    print("\n【模式 1】标准半仓滚动模式")
    print("说明: 松松在2025年采用的核心策略，半仓滚动，每天只买一只")
    run_with_mode("标准模式", {})
    
    # 2. 激进模式
    print("\n\n【模式 2】激进模式")
    print("说明: 更高仓位，追求更高收益，适合牛市行情")
    run_with_mode("激进模式", AGGRESSIVE_CONFIG)
    
    # 3. 保守模式
    print("\n\n【模式 3】保守模式")
    print("说明: 更低仓位，更严格止损，适合震荡市或熊市")
    run_with_mode("保守模式", CONSERVATIVE_CONFIG)
    
    # 4. 可转债高频模式
    print("\n\n【模式 4】可转债高频模式")
    print("说明: 纪念松松的债神时代，高频交易，30秒止损")
    run_with_mode("可转债模式", CONVERTIBLE_BOND_CONFIG)
    
    print("\n" + "=" * 60)
    print("所有模式回测完成")
    print("=" * 60)


if __name__ == '__main__':
    main()

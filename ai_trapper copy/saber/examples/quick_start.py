"""
快速开始示例
演示如何使用Saber策略
"""

from saber import SaberStrategy, StrategyConfig


def main():
    """主函数"""
    
    print("="*60)
    print("Saber 慢牛双模组期权策略 - 快速开始")
    print("="*60)
    
    # 1. 获取配置
    config = StrategyConfig.get_config(mode='backtest')
    
    print("\n策略配置:")
    print(f"  初始资金: ${config['initial_capital']:,.2f}")
    print(f"  单仓位限制: {config['single_position_limit']:.0%}")
    print(f"  总仓位限制: {config['total_position_limit']:.0%}")
    print(f"  IV低位阈值: {config['iv_low_percentile']}%")
    print(f"  IV高位阈值: {config['iv_high_percentile']}%")
    
    # 2. 初始化策略
    strategy = SaberStrategy(config)
    
    # 3. 运行单日策略
    print("\n开始执行策略...")
    print("注意: 这是演示模式，使用模拟数据")
    
    result = strategy.run_daily(
        symbol='BTC',
        date='2024-06-20'
    )
    
    # 4. 显示结果
    print("\n" + "="*60)
    print("执行完成")
    print("="*60)
    
    if result.get('signals'):
        print(f"\n发现 {len(result['signals'])} 个信号")
    
    if result.get('actions'):
        print(f"执行了 {len(result['actions'])} 个操作")
    
    # 5. 获取绩效报告
    report = strategy.get_performance_report()
    
    print("\n策略表现:")
    portfolio = report['portfolio']
    print(f"  当前资金: ${portfolio['current_capital']:,.2f}")
    print(f"  持仓数量: {portfolio['position_count']}")
    print(f"  总收益: {portfolio['total_return']:+.2%}")


if __name__ == '__main__':
    main()

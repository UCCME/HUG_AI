"""
单日测试示例
测试策略在特定日期的表现
"""

from datetime import datetime
from mancang import MancangStrategy, StrategyConfig


def main():
    """主函数"""
    
    print("="*60)
    print("满仓大佬交易策略 - 单日测试")
    print("="*60)
    
    # 1. 获取配置
    config = StrategyConfig.get_config(mode='backtest')
    
    # 2. 初始化策略
    strategy = MancangStrategy(config)
    
    # 3. 指定测试日期（可以修改为任意交易日）
    test_date = '2024-06-20'
    
    print(f"\n测试日期: {test_date}")
    print("正在执行策略...")
    
    # 4. 执行单日策略
    result = strategy.run_daily(test_date)
    
    # 5. 显示详细结果
    print("\n" + "="*60)
    print("执行结果")
    print("="*60)
    
    if result.get('signals'):
        print(f"\n发现 {len(result['signals'])} 个买入信号:")
        for i, signal in enumerate(result['signals'], 1):
            print(f"\n信号 {i}:")
            print(f"  股票代码: {signal['symbol']}")
            print(f"  信号类型: {signal['type']}")
            print(f"  原因: {signal['reason']}")
            print(f"  评分: {signal['score']:.1f}")
            print(f"  建议仓位: {signal['position_ratio']:.1%}")
    else:
        print("\n未发现买入信号")
    
    if result.get('actions'):
        print(f"\n执行了 {len(result['actions'])} 个操作:")
        for action in result['actions']:
            print(f"  - {action}")
    else:
        print("\n未执行任何操作")
    
    # 6. 显示组合状态
    portfolio = result.get('portfolio', {})
    if portfolio:
        print(f"\n组合状态:")
        print(f"  总资产: ¥{portfolio['total_value']:,.2f}")
        print(f"  持仓市值: ¥{portfolio['position_value']:,.2f}")
        print(f"  可用资金: ¥{portfolio['available_cash']:,.2f}")
        print(f"  总收益: {portfolio['total_return']:+.2%}")
        print(f"  仓位比例: {portfolio['position_ratio']:.1%}")
        print(f"  持仓数量: {portfolio['position_count']}")


if __name__ == '__main__':
    main()

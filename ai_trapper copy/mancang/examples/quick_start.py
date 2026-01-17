"""
快速开始示例
演示如何使用满仓大佬策略进行回测
"""

from mancang import MancangStrategy, StrategyConfig


def main():
    """主函数"""
    
    print("="*60)
    print("满仓大佬交易策略 - 快速开始")
    print("="*60)
    
    # 1. 获取配置
    config = StrategyConfig.get_config(mode='backtest')
    
    print("\n策略配置:")
    print(f"  初始资金: ¥{config['initial_capital']:,.2f}")
    print(f"  最大仓位: {config['max_total_pos']:.0%}")
    print(f"  单只仓位: {config['single_pos_limit']:.0%}")
    print(f"  止损线: MA{config['ma_stop_loss']}")
    print(f"  连板限制: {config['chase_limit']}板")
    
    # 2. 初始化策略
    strategy = MancangStrategy(config)
    
    # 3. 运行回测
    print("\n开始回测...")
    print("注意: 首次运行需要下载数据，可能需要一些时间")
    
    results = strategy.backtest(
        start_date='2024-01-01',
        end_date='2024-12-31'
    )
    
    # 4. 显示结果
    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    
    portfolio = results['portfolio']
    print(f"\n资金情况:")
    print(f"  初始资金: ¥{portfolio['initial_capital']:,.2f}")
    print(f"  最终资金: ¥{portfolio['total_value']:,.2f}")
    print(f"  总收益: ¥{portfolio['total_pnl']:,.2f}")
    print(f"  收益率: {portfolio['total_return']:.2%}")
    
    trade_stats = results['trade_statistics']
    if trade_stats:
        print(f"\n交易统计:")
        print(f"  总交易次数: {trade_stats.get('total_trades', 0)}")
        print(f"  盈利次数: {trade_stats.get('win_trades', 0)}")
        print(f"  亏损次数: {trade_stats.get('loss_trades', 0)}")
        print(f"  胜率: {trade_stats.get('win_rate', 0):.1%}")
        print(f"  平均盈利: ¥{trade_stats.get('avg_win', 0):,.2f}")
        print(f"  平均亏损: ¥{trade_stats.get('avg_loss', 0):,.2f}")
    
    print("\n" + "="*60)
    print("回测完成！")
    print("="*60)


if __name__ == '__main__':
    main()

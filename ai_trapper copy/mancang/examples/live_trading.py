"""
实盘交易示例
演示如何使用定时调度器进行实盘交易
"""

from mancang import MancangStrategy, StrategyConfig
from mancang.scheduler import TaskScheduler


def main():
    """主函数"""
    
    print("="*60)
    print("满仓大佬交易策略 - 实盘交易")
    print("="*60)
    
    # 1. 获取配置
    config = StrategyConfig.get_config(mode='live')
    
    print("\n策略配置:")
    print(f"  初始资金: ¥{config['initial_capital']:,.2f}")
    print(f"  最大仓位: {config['max_total_pos']:.0%}")
    print(f"  单只仓位: {config['single_pos_limit']:.0%}")
    print(f"  止损线: MA{config['ma_stop_loss']}")
    
    # 2. 初始化策略
    strategy = MancangStrategy(config)
    
    # 3. 创建调度器
    scheduler = TaskScheduler(strategy)
    
    print("\n" + "="*60)
    print("⚠️  重要提示")
    print("="*60)
    print("1. 本系统仅用于信号提醒，不会自动下单")
    print("2. 请根据信号提示，在交易软件中手动操作")
    print("3. 严格遵守止损纪律，跌破5日线立即卖出")
    print("4. 控制仓位，单只股票不超过10%")
    print("5. 本金安全第一，盈利第二")
    
    input("\n按回车键启动实盘监控...")
    
    # 4. 启动调度器
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n实盘监控已停止")


if __name__ == '__main__':
    main()

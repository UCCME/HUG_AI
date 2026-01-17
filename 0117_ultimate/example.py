"""
究极策略使用示例
演示如何使用究极策略进行回测
"""
from config import UltimateConfig
from data_handler import DataHandler
from backtest_engine import BacktestEngine
from performance_analyzer import PerformanceAnalyzer


def example_basic_backtest():
    """基础回测示例"""
    print("=" * 60)
    print("示例1：基础回测")
    print("=" * 60)
    
    # 1. 创建配置
    config = UltimateConfig()
    config.INITIAL_CAPITAL = 100000
    config.DATA_PROVIDER = "yfinance"
    config.SYMBOL = "GC=F"  # 黄金期货
    
    # 2. 准备数据
    data_handler = DataHandler(config)
    data = data_handler.prepare_data('2023-01-01', '2024-01-01')
    
    # 3. 运行回测
    engine = BacktestEngine(config)
    result = engine.run(data)
    
    # 4. 分析结果
    analyzer = PerformanceAnalyzer(result)
    analyzer.print_summary()
    analyzer.generate_report()
    
    print("\n✅ 基础回测完成！")


def example_custom_parameters():
    """自定义参数示例"""
    print("\n" + "=" * 60)
    print("示例2：自定义参数回测")
    print("=" * 60)
    
    # 创建自定义配置
    config = UltimateConfig()
    
    # 修改策略参数
    config.INITIAL_CAPITAL = 50000
    config.STOP_LOSS_PCT = 0.03  # 3%止损
    config.TAKE_PROFIT_PCT = 0.15  # 15%止盈
    config.TIME_STOP_DAYS = 5  # 5天时间止损
    
    # 修改信号权重
    config.WEIGHT_MA = 0.30  # 增加MA权重
    config.WEIGHT_RSI = 0.20  # 增加RSI权重
    config.WEIGHT_STOCH_RSI = 0.15  # 增加StochRSI权重
    
    # 修改技术指标参数
    config.FAST_MA_PERIOD = 50
    config.SLOW_MA_PERIOD = 200
    config.RSI_OVERSOLD = 25
    config.RSI_OVERBOUGHT = 75
    
    print(f"自定义配置：")
    print(f"  - 初始资金: ${config.INITIAL_CAPITAL:,}")
    print(f"  - 止损: {config.STOP_LOSS_PCT:.1%}")
    print(f"  - 止盈: {config.TAKE_PROFIT_PCT:.1%}")
    print(f"  - MA周期: {config.FAST_MA_PERIOD}/{config.SLOW_MA_PERIOD}")
    
    # 运行回测
    data_handler = DataHandler(config)
    data = data_handler.prepare_data('2023-01-01', '2024-01-01')
    
    engine = BacktestEngine(config)
    result = engine.run(data)
    
    analyzer = PerformanceAnalyzer(result)
    analyzer.print_summary()
    
    print("\n✅ 自定义参数回测完成！")


def example_local_data():
    """使用本地数据示例"""
    print("\n" + "=" * 60)
    print("示例3：使用本地数据回测")
    print("=" * 60)
    
    config = UltimateConfig()
    config.DATA_PROVIDER = "local"
    config.LOCAL_DATA_PATH = "../ai_trapper/XAU_5m_data.csv"  # 本地数据路径
    
    try:
        data_handler = DataHandler(config)
        data = data_handler.prepare_data('2023-01-01', '2024-01-01')
        
        engine = BacktestEngine(config)
        result = engine.run(data)
        
        analyzer = PerformanceAnalyzer(result)
        analyzer.print_summary()
        
        print("\n✅ 本地数据回测完成！")
    except FileNotFoundError:
        print("⚠️  本地数据文件不存在，请确保路径正确")
    except Exception as e:
        print(f"❌ 错误: {str(e)}")


def example_compare_strategies():
    """策略对比示例"""
    print("\n" + "=" * 60)
    print("示例4：策略参数对比")
    print("=" * 60)
    
    # 准备数据（共用）
    config_base = UltimateConfig()
    data_handler = DataHandler(config_base)
    data = data_handler.prepare_data('2023-01-01', '2024-01-01')
    
    strategies = [
        {"name": "保守策略", "stop_loss": 0.03, "take_profit": 0.08, "position_size": 0.70},
        {"name": "平衡策略", "stop_loss": 0.05, "take_profit": 0.10, "position_size": 0.85},
        {"name": "激进策略", "stop_loss": 0.08, "take_profit": 0.15, "position_size": 0.95},
    ]
    
    results = []
    
    for strategy in strategies:
        print(f"\n测试 {strategy['name']}...")
        
        config = UltimateConfig()
        config.STOP_LOSS_PCT = strategy['stop_loss']
        config.TAKE_PROFIT_PCT = strategy['take_profit']
        config.POSITION_SIZE = strategy['position_size']
        
        engine = BacktestEngine(config)
        result = engine.run(data)
        
        results.append({
            'name': strategy['name'],
            'total_return': result.total_return,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate
        })
    
    # 打印对比结果
    print("\n" + "=" * 60)
    print("策略对比结果")
    print("=" * 60)
    print(f"{'策略名称':<12} {'总收益率':<12} {'夏普比率':<12} {'最大回撤':<12} {'胜率':<12}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['name']:<12} {r['total_return']:>10.2%} {r['sharpe_ratio']:>10.2f} {r['max_drawdown']:>10.2%} {r['win_rate']:>10.2%}")
    
    print("\n✅ 策略对比完成！")


if __name__ == "__main__":
    # 运行示例
    print("🚀 究极策略使用示例")
    print("=" * 60)
    
    # 选择要运行的示例
    print("\n请选择要运行的示例：")
    print("1. 基础回测")
    print("2. 自定义参数回测")
    print("3. 使用本地数据回测")
    print("4. 策略参数对比")
    print("5. 运行所有示例")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    if choice == "1":
        example_basic_backtest()
    elif choice == "2":
        example_custom_parameters()
    elif choice == "3":
        example_local_data()
    elif choice == "4":
        example_compare_strategies()
    elif choice == "5":
        example_basic_backtest()
        example_custom_parameters()
        example_local_data()
        example_compare_strategies()
    else:
        print("❌ 无效选项")

"""
究极策略主程序
整合所有策略模块的完整回测系统
"""
import sys
import argparse
from datetime import datetime, timedelta

from config import UltimateConfig
from data_handler import DataHandler
from backtest_engine import BacktestEngine
from performance_analyzer import PerformanceAnalyzer


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='究极策略回测系统')
    parser.add_argument('--start-date', type=str, help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--data-provider', type=str, choices=['local', 'yfinance', 'akshare'],
                       help='数据源选择')
    parser.add_argument('--symbol', type=str, help='交易品种代码')
    parser.add_argument('--initial-capital', type=float, help='初始资金')
    parser.add_argument('--no-plot', action='store_true', help='不显示图表')
    
    args = parser.parse_args()
    
    # 创建配置
    config = UltimateConfig()
    
    # 应用命令行参数
    if args.data_provider:
        config.DATA_PROVIDER = args.data_provider
    if args.symbol:
        config.SYMBOL = args.symbol
    if args.initial_capital:
        config.INITIAL_CAPITAL = args.initial_capital
    
    # 设置回测日期
    if args.start_date:
        config.START_DATE = args.start_date
    else:
        # 默认回测最近1年
        config.START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    if args.end_date:
        config.END_DATE = args.end_date
    else:
        config.END_DATE = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print("🚀 究极策略回测系统")
    print("=" * 60)
    print(f"数据源: {config.DATA_PROVIDER}")
    print(f"交易品种: {config.SYMBOL}")
    print(f"回测期间: {config.START_DATE} 到 {config.END_DATE}")
    print(f"初始资金: ${config.INITIAL_CAPITAL:,.2f}")
    print("=" * 60)
    
    try:
        # 1. 数据处理
        data_handler = DataHandler(config)
        data = data_handler.prepare_data(config.START_DATE, config.END_DATE)
        
        if data.empty:
            print("❌ 错误：无法获取有效数据")
            sys.exit(1)
        
        # 2. 执行回测
        backtest_engine = BacktestEngine(config)
        result = backtest_engine.run(data)
        
        # 3. 性能分析
        analyzer = PerformanceAnalyzer(result)
        analyzer.print_summary()
        
        # 4. 生成图表
        if not args.no_plot:
            print("\n正在生成分析图表...")
            analyzer.plot_equity_curve()
            analyzer.plot_return_distribution()
            analyzer.plot_trade_analysis()
        
        print("\n" + "=" * 60)
        print("✅ 回测完成！")
        print("=" * 60)
        print(f"交易日志: {config.TRADES_LOG_PATH}")
        print(f"图表保存在: 0117_ultimate/ 目录")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

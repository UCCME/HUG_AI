"""
可插拔式策略主程序
使用策略工厂和组合器的灵活架构
"""
import sys
import argparse
from datetime import datetime, timedelta

from pluggable_config import (
    PluggableConfig,
    get_conservative_config,
    get_balanced_config,
    get_aggressive_config,
    get_trend_following_config,
    get_mean_reversion_config
)
from strategy_factory import StrategyFactory
from strategy_composer import StrategyComposer
from data_handler import DataHandler
from backtest_engine import BacktestEngine
from performance_analyzer import PerformanceAnalyzer


def create_strategies_from_config(config: PluggableConfig):
    """从配置创建策略实例"""
    strategies = []
    
    for strategy_config in config.get_enabled_strategies():
        try:
            strategy = StrategyFactory.create(
                strategy_config.name,
                weight=strategy_config.weight,
                enabled=strategy_config.enabled,
                **strategy_config.params
            )
            strategies.append(strategy)
            print(f"✅ 创建策略: {strategy.name} (权重: {strategy.weight})")
        except Exception as e:
            print(f"❌ 创建策略 {strategy_config.name} 失败: {str(e)}")
    
    return strategies


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='可插拔式策略回测系统')
    parser.add_argument('--config', type=str, choices=['conservative', 'balanced', 'aggressive', 'trend', 'mean_reversion'],
                       default='balanced', help='配置方案选择')
    parser.add_argument('--start-date', type=str, help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--data-provider', type=str, choices=['local', 'yfinance', 'akshare'],
                       help='数据源选择')
    parser.add_argument('--symbol', type=str, help='交易品种代码')
    parser.add_argument('--list-strategies', action='store_true', help='列出所有可用策略')
    parser.add_argument('--no-plot', action='store_true', help='不显示图表')
    
    args = parser.parse_args()
    
    # 列出策略
    if args.list_strategies:
        StrategyFactory.list_strategies()
        return
    
    # 选择配置方案
    config_map = {
        'conservative': get_conservative_config,
        'balanced': get_balanced_config,
        'aggressive': get_aggressive_config,
        'trend': get_trend_following_config,
        'mean_reversion': get_mean_reversion_config
    }
    
    config = config_map[args.config]()
    
    # 应用命令行参数
    if args.data_provider:
        config.DATA_PROVIDER = args.data_provider
    if args.symbol:
        config.SYMBOL = args.symbol
    
    # 设置回测日期
    if args.start_date:
        config.START_DATE = args.start_date
    else:
        config.START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    if args.end_date:
        config.END_DATE = args.end_date
    else:
        config.END_DATE = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print("🚀 可插拔式策略回测系统")
    print("=" * 60)
    print(f"配置方案: {args.config}")
    print(f"数据源: {config.DATA_PROVIDER}")
    print(f"交易品种: {config.SYMBOL}")
    print(f"回测期间: {config.START_DATE} 到 {config.END_DATE}")
    print(f"初始资金: ${config.INITIAL_CAPITAL:,.2f}")
    print("=" * 60)
    
    try:
        # 1. 创建策略实例
        print("\n📦 步骤 1/5: 创建策略实例")
        print("-" * 60)
        strategies = create_strategies_from_config(config)
        
        if not strategies:
            print("❌ 错误：没有可用的策略")
            sys.exit(1)
        
        # 2. 创建策略组合器
        print("\n🎯 步骤 2/5: 创建策略组合器")
        print("-" * 60)
        composer = StrategyComposer(
            strategies=strategies,
            signal_threshold=config.SIGNAL_THRESHOLD,
            min_signal_count=config.MIN_SIGNAL_COUNT
        )
        composer.print_info()
        
        # 3. 数据处理
        print("\n📊 步骤 3/5: 数据获取和处理")
        print("-" * 60)
        data_handler = DataHandler(config)
        data = data_handler.prepare_data(config.START_DATE, config.END_DATE)
        
        if data.empty:
            print("❌ 错误：无法获取有效数据")
            sys.exit(1)
        
        # 4. 执行回测（使用组合器）
        print("\n🔄 步骤 4/5: 执行回测")
        print("-" * 60)
        
        # 更新SMC结构（如果启用）
        for strategy in strategies:
            if hasattr(strategy, 'update_structure'):
                strategy.update_structure(data)
        
        # 使用组合器进行回测
        backtest_engine = BacktestEngine(config)
        
        # 遍历数据执行回测
        for i in range(len(data)):
            current_date = data.index[i]
            current_price = data.iloc[i]['close']
            
            # 使用组合器生成综合信号
            composite_signal = composer.generate_composite_signal(data, i)
            
            # 转换为回测引擎可用的信号格式
            from ultimate_strategy import TradingSignal, SignalType as OriginalSignalType
            
            signal = TradingSignal(
                timestamp=composite_signal.timestamp,
                signal_type=OriginalSignalType[composite_signal.signal_type.value],
                confidence=composite_signal.confidence,
                price=composite_signal.price,
                reasons=composite_signal.contributing_strategies,
                indicators={
                    'buy_score': composite_signal.buy_score,
                    'sell_score': composite_signal.sell_score,
                    'buy_count': composite_signal.buy_count,
                    'sell_count': composite_signal.sell_count
                }
            )
            
            # 检查止损止盈
            if backtest_engine.current_position > 0:
                stop_reason = backtest_engine.check_stop_loss_take_profit(current_price, signal)
                if stop_reason:
                    backtest_engine.execute_sell(signal, stop_reason)
            
            # 执行交易信号
            if signal.signal_type.value == 'BUY' and backtest_engine.current_position == 0:
                backtest_engine.execute_buy(signal)
            elif signal.signal_type.value == 'SELL' and backtest_engine.current_position > 0:
                backtest_engine.execute_sell(signal, "卖出信号触发")
            
            # 更新权益
            total_equity = backtest_engine.available_cash + backtest_engine.current_position * current_price
            backtest_engine.current_capital = total_equity
            
            backtest_engine.equity_history.append({
                'date': current_date,
                'equity': total_equity,
                'cash': backtest_engine.available_cash,
                'position_value': backtest_engine.current_position * current_price,
                'position': backtest_engine.current_position
            })
        
        # 计算回测结果
        result = backtest_engine._calculate_results(data)
        
        print(f"\n✅ 回测完成，共执行 {result.total_trades} 笔交易")
        
        # 5. 性能分析
        print("\n📈 步骤 5/5: 性能分析")
        print("-" * 60)
        analyzer = PerformanceAnalyzer(result)
        analyzer.print_summary()
        
        # 生成图表
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

"""
黄金策略回测脚本
读取历史数据，计算技术指标，运行策略回测并展示结果
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
from gold_strategy import GoldTradingStrategy, StrategyConfig, SignalType

def calculate_technical_indicators(df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """
    计算所有需要的技术指标
    
    Args:
        df: 原始OHLCV数据
        config: 策略配置
        
    Returns:
        添加了技术指标的DataFrame
    """
    print("正在计算技术指标...")
    
    # 确保数据按时间排序
    df = df.sort_values('Date').reset_index(drop=True)
    
    # 1. 移动平均线
    df[f'MA_{config.FAST_MA_PERIOD}'] = df['Close'].rolling(window=config.FAST_MA_PERIOD).mean()
    df[f'MA_{config.SLOW_MA_PERIOD}'] = df['Close'].rolling(window=config.SLOW_MA_PERIOD).mean()
    
    # 2. RSI
    def calculate_rsi(prices, period=14):
        deltas = prices.diff()
        gain = deltas.where(deltas > 0, 0).rolling(window=period).mean()
        loss = -deltas.where(deltas < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    df['RSI'] = calculate_rsi(df['Close'], period=14)
    
    # 3. MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # 4. 布林带
    bb_period = 20
    df['BB_Middle'] = df['Close'].rolling(window=bb_period).mean()
    bb_std = df['Close'].rolling(window=bb_period).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    # 5. ATR (Average True Range)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()
    
    # 6. 成交量指标
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
    df['Volume_Ratio'] = df['Volume_Ratio'].fillna(1.0)
    
    # 7. 价格变化率
    df['Price_Change'] = df['Close'].pct_change()
    
    # 删除包含NaN的行（指标计算初期）
    df = df.dropna().reset_index(drop=True)
    
    print(f"技术指标计算完成，有效数据行数: {len(df)}")
    return df


def load_data(file_path: str) -> pd.DataFrame:
    """
    加载CSV数据
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        DataFrame
    """
    print(f"正在加载数据: {file_path}")
    
    # 读取CSV，使用分号分隔符
    df = pd.read_csv(file_path, sep=';')
    
    # 转换日期列
    df['Date'] = pd.to_datetime(df['Date'], format='%Y.%m.%d %H:%M')
    
    print(f"数据加载完成:")
    print(f"  - 数据行数: {len(df)}")
    print(f"  - 时间范围: {df['Date'].min()} 至 {df['Date'].max()}")
    print(f"  - 列名: {df.columns.tolist()}")
    
    return df


def print_backtest_results(strategy: GoldTradingStrategy, signals, trades):
    """
    打印回测结果
    
    Args:
        strategy: 策略实例
        signals: 信号列表
        trades: 交易列表
    """
    stats = strategy.get_strategy_stats()
    
    print("\n" + "="*60)
    print("📊 回测结果统计")
    print("="*60)
    
    print(f"\n【交易统计】")
    print(f"  总交易次数: {stats['total_trades']}")
    print(f"  盈利交易: {stats['profitable_trades']}")
    print(f"  亏损交易: {stats['losing_trades']}")
    print(f"  胜率: {stats['win_rate']*100:.2f}%")
    
    print(f"\n【收益统计】")
    print(f"  总收益率: {stats['total_pnl']*100:.2f}%")
    print(f"  平均收益率: {stats['avg_return']*100:.2f}%")
    print(f"  最大回撤: {stats['max_drawdown']*100:.2f}%")
    print(f"  盈利因子: {stats['profit_factor']:.2f}")
    
    print(f"\n【仓位统计】")
    print(f"  平均仓位: {stats['avg_position_size']:.2f}手")
    print(f"  当前持仓: {stats['current_position']}")
    
    # 打印最近的几笔交易
    if trades:
        print(f"\n【最近10笔交易】")
        print("-" * 60)
        for trade in trades[-10:]:
            timestamp = trade.get('timestamp', 'N/A')
            action = trade.get('action', 'N/A')
            price = trade.get('price', 0)
            pnl = trade.get('pnl', 0) if 'pnl' in trade else None
            
            if pnl is not None:
                pnl_str = f"盈亏: {pnl*100:+.2f}%"
            else:
                pnl_str = ""
            
            print(f"{timestamp} | {action:20s} | 价格: {price:.2f} | {pnl_str}")
    
    # 信号统计
    buy_signals = sum(1 for s in signals if s.signal_type == SignalType.BUY)
    sell_signals = sum(1 for s in signals if s.signal_type == SignalType.SELL)
    hold_signals = sum(1 for s in signals if s.signal_type == SignalType.HOLD)
    
    print(f"\n【信号统计】")
    print(f"  总信号数: {len(signals)}")
    print(f"  买入信号: {buy_signals} ({buy_signals/len(signals)*100:.1f}%)")
    print(f"  卖出信号: {sell_signals} ({sell_signals/len(signals)*100:.1f}%)")
    print(f"  持有信号: {hold_signals} ({hold_signals/len(signals)*100:.1f}%)")
    
    print("\n" + "="*60)


def export_results(signals, trades, output_path='backtest_results.csv'):
    """
    导出回测结果到CSV
    
    Args:
        signals: 信号列表
        trades: 交易列表
        output_path: 输出文件路径
    """
    try:
        # 导出交易记录
        if trades:
            trades_df = pd.DataFrame(trades)
            trades_path = output_path.replace('.csv', '_trades.csv')
            trades_df.to_csv(trades_path, index=False)
            print(f"\n✅ 交易记录已导出到: {trades_path}")
        
        # 导出信号记录
        if signals:
            signals_data = []
            for signal in signals:
                signals_data.append({
                    'timestamp': signal.timestamp,
                    'signal_type': signal.signal_type.name,
                    'price': signal.price,
                    'confidence': signal.confidence,
                    'reason': signal.reason
                })
            signals_df = pd.DataFrame(signals_data)
            signals_path = output_path.replace('.csv', '_signals.csv')
            signals_df.to_csv(signals_path, index=False)
            print(f"✅ 信号记录已导出到: {signals_path}")
            
    except Exception as e:
        print(f"❌ 导出结果时出错: {e}")


def main():
    """主函数"""
    print("="*60)
    print("🏆 黄金交易策略回测系统")
    print("="*60)
    
    # 1. 配置策略参数
    config = StrategyConfig(
        FAST_MA_PERIOD=10,
        SLOW_MA_PERIOD=20,
        RSI_OVERSOLD=30,
        RSI_OVERBOUGHT=70,
        STOP_LOSS_PCT=0.02,
        TAKE_PROFIT_PCT=0.03,
        ATR_STOP_MULTIPLIER=2.0,
        ATR_PROFIT_MULTIPLIER=3.0,
        POSITION_SIZE=0.3,
        MAX_POSITION_SIZE=0.5,
        RISK_PER_TRADE=0.01,
        SIGNAL_THRESHOLD=0.15,
        COMMISSION_RATE=0.0003,
        SLIPPAGE=0.0001,
        WEIGHTS={
            'ma': 0.30,
            'macd': 0.25,
            'rsi': 0.20,
            'bb': 0.15,
            'volume': 0.10
        }
    )
    
    # 2. 加载数据
    data_file = '/Users/_jholder/Desktop/ai_trapper/XAU_15m_data.csv'
    df = load_data(data_file)
    
    # 3. 计算技术指标
    df = calculate_technical_indicators(df, config)
    
    # 设置Date为索引
    df.set_index('Date', inplace=True)
    
    # 4. 初始化策略
    strategy = GoldTradingStrategy(config)
    
    # 5. 运行回测
    print(f"\n{'='*60}")
    print("⚡ 开始回测...")
    print(f"{'='*60}\n")
    
    initial_capital = 100000  # 初始资金10万
    signals, trades = strategy.backtest(
        df, 
        initial_capital=initial_capital,
        verbose=False  # 设为True可以看到详细交易日志
    )
    
    # 6. 打印结果
    print_backtest_results(strategy, signals, trades)
    
    # 7. 导出结果
    export_results(signals, trades)
    
    print("\n✨ 回测完成！\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断回测")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 回测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

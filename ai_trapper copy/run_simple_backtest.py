#!/usr/bin/env python3
"""
简化的黄金策略回测脚本
- 使用优化后的策略
- 修复资金计算bug
- 所有图表合并到一张图
- 修复中文乱码
"""

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体，修复乱码
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from gold_strategy import GoldTradingStrategy, StrategyConfig, SignalType
from config import Config

def calculate_technical_indicators(df: pd.DataFrame, config) -> pd.DataFrame:
    """计算技术指标"""
    print("正在计算技术指标...")
    df = df.sort_values('Date').reset_index(drop=True)
    
    # 移动平均线
    df[f'MA_{config.FAST_MA_PERIOD}'] = df['Close'].rolling(window=config.FAST_MA_PERIOD).mean()
    df[f'MA_{config.SLOW_MA_PERIOD}'] = df['Close'].rolling(window=config.SLOW_MA_PERIOD).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # 布林带
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    # ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()
    
    # 成交量
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
    df['Volume_Ratio'] = df['Volume_Ratio'].fillna(1.0)
    df['Price_Change'] = df['Close'].pct_change()
    
    df = df.dropna().reset_index(drop=True)
    print(f"✅ 技术指标计算完成，有效数据: {len(df)} 条")
    return df


def run_backtest_simple(data: pd.DataFrame, strategy: GoldTradingStrategy, initial_capital: float = 100000):
    """简化的回测引擎，修复资金计算bug"""
    
    print(f"\n开始回测...")
    print(f"数据期间：{data.index[0]} 到 {data.index[-1]}")
    print(f"初始资金：${initial_capital:,.2f}\n")
    
    # 初始化
    capital = initial_capital
    position = 0  # 持仓数量（手数）
    entry_price = 0
    trades = []
    equity_curve = []
    
    for i in range(len(data)):
        current_price = data.iloc[i]['Close']
        current_date = data.index[i]
        
        # 生成信号
        signal = strategy.generate_composite_signal(data, i)
        
        # 记录权益
        if position > 0:
            equity = capital + position * (current_price - entry_price)
        else:
            equity = capital
        equity_curve.append({'Date': current_date, 'Equity': equity})
        
        # 检查是否平仓
        if position != 0:
            # 简单的止损止盈
            pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price
            
            should_close = False
            close_reason = ""
            
            # 止损
            if pnl_pct < -strategy.config.STOP_LOSS_PCT:
                should_close = True
                close_reason = "止损"
            # 止盈
            elif pnl_pct > strategy.config.TAKE_PROFIT_PCT:
                should_close = True
                close_reason = "止盈"
            # 反向信号
            elif (position > 0 and signal.signal_type == SignalType.SELL) or \
                 (position < 0 and signal.signal_type == SignalType.BUY):
                should_close = True
                close_reason = "反向信号"
            
            if should_close:
                # 平仓
                pnl = position * (current_price - entry_price) if position > 0 else position * (entry_price - current_price)
                commission = abs(position * current_price * strategy.config.COMMISSION_RATE)
                net_pnl = pnl - commission
                
                capital += net_pnl
                
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': current_date,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'position': position,
                    'pnl': net_pnl,
                    'pnl_pct': pnl_pct,
                    'reason': close_reason
                })
                
                position = 0
                entry_price = 0
        
        # 开仓信号
        if position == 0 and signal.confidence > strategy.config.SIGNAL_THRESHOLD:
            if signal.signal_type == SignalType.BUY:
                # 计算仓位（固定比例）
                position_value = capital * strategy.config.POSITION_SIZE
                position = int(position_value / current_price)
                
                if position > 0:
                    entry_price = current_price
                    entry_date = current_date
                    commission = position * current_price * strategy.config.COMMISSION_RATE
                    capital -= commission
                    
            elif signal.signal_type == SignalType.SELL:
                # 做空（如果允许）
                position_value = capital * strategy.config.POSITION_SIZE
                position = -int(position_value / current_price)
                
                if position < 0:
                    entry_price = current_price
                    entry_date = current_date
                    commission = abs(position * current_price * strategy.config.COMMISSION_RATE)
                    capital -= commission
    
    # 最后一天如果还有持仓，强制平仓
    if position != 0:
        current_price = data.iloc[-1]['Close']
        pnl = position * (current_price - entry_price) if position > 0 else position * (entry_price - current_price)
        commission = abs(position * current_price * strategy.config.COMMISSION_RATE)
        capital += pnl - commission
        
        trades.append({
            'entry_date': entry_date,
            'exit_date': data.index[-1],
            'entry_price': entry_price,
            'exit_price': current_price,
            'position': position,
            'pnl': pnl - commission,
            'pnl_pct': (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price,
            'reason': '强制平仓'
        })
    
    return pd.DataFrame(trades), pd.DataFrame(equity_curve), capital


def save_trades_to_txt(trades_df, final_capital, initial_capital, filename='trade_details.txt'):
    """保存详细交易记录到txt文件"""
    print(f"正在保存交易详情到 {filename}...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("Gold Trading Strategy - Detailed Trade Log\n".center(100))
        f.write("="*100 + "\n\n")
        
        # 总结
        total_return = (final_capital - initial_capital) / initial_capital * 100
        f.write(f"Initial Capital: ${initial_capital:,.2f}\n")
        f.write(f"Final Capital: ${final_capital:,.2f}\n")
        f.write(f"Total Return: {total_return:.2f}%\n")
        f.write(f"Total Trades: {len(trades_df)}\n")
        f.write("\n" + "="*100 + "\n\n")
        
        # 详细交易记录
        f.write("DETAILED TRADE RECORDS:\n")
        f.write("-"*100 + "\n\n")
        
        cumulative_pnl = 0
        for idx, trade in trades_df.iterrows():
            cumulative_pnl += trade['pnl']
            
            # 计算持续时间（处理日期类型）
            try:
                entry_date = pd.to_datetime(trade['entry_date'])
                exit_date = pd.to_datetime(trade['exit_date'])
                duration_days = (exit_date - entry_date).days
            except:
                duration_days = 0
            
            f.write(f"Trade #{idx + 1}\n")
            f.write(f"  Entry Date:     {trade['entry_date']}\n")
            f.write(f"  Exit Date:      {trade['exit_date']}\n")
            f.write(f"  Direction:      {'LONG' if trade['position'] > 0 else 'SHORT'}\n")
            f.write(f"  Position Size:  {abs(trade['position'])} contracts\n")
            f.write(f"  Entry Price:    ${trade['entry_price']:,.2f}\n")
            f.write(f"  Exit Price:     ${trade['exit_price']:,.2f}\n")
            f.write(f"  P&L:            ${trade['pnl']:,.2f} ({trade['pnl_pct']*100:+.2f}%)\n")
            f.write(f"  Cumulative P&L: ${cumulative_pnl:,.2f}\n")
            f.write(f"  Exit Reason:    {trade['reason']}\n")
            f.write(f"  Duration:       {duration_days} days\n")
            f.write("-"*100 + "\n\n")
        
        # 统计摘要
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        f.write("\n" + "="*100 + "\n")
        f.write("TRADING STATISTICS SUMMARY\n".center(100))
        f.write("="*100 + "\n\n")
        
        f.write(f"Win Rate:           {len(winning_trades)/len(trades_df)*100:.2f}%\n")
        f.write(f"Winning Trades:     {len(winning_trades)}\n")
        f.write(f"Losing Trades:      {len(losing_trades)}\n")
        f.write(f"Average Win:        ${winning_trades['pnl'].mean():,.2f}\n" if len(winning_trades) > 0 else "Average Win:        $0.00\n")
        f.write(f"Average Loss:       ${losing_trades['pnl'].mean():,.2f}\n" if len(losing_trades) > 0 else "Average Loss:       $0.00\n")
        f.write(f"Largest Win:        ${trades_df['pnl'].max():,.2f}\n")
        f.write(f"Largest Loss:       ${trades_df['pnl'].min():,.2f}\n")
        
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        f.write(f"Profit Factor:      {profit_factor:.2f}\n")
        
        # 计算平均持仓天数（处理日期类型）
        try:
            entry_dates = pd.to_datetime(trades_df['entry_date'])
            exit_dates = pd.to_datetime(trades_df['exit_date'])
            avg_duration = (exit_dates - entry_dates).dt.days.mean()
        except:
            avg_duration = 0
        f.write(f"Avg Hold Duration:  {avg_duration:.1f} days\n")
        
        f.write("\n" + "="*100 + "\n")
    
    print(f"✅ 交易详情已保存到 {filename}\n")


def print_results(trades_df, equity_df, final_capital, initial_capital):
    """打印回测结果"""
    print("\n" + "="*80)
    print("回测结果汇总".center(80))
    print("="*80)
    
    # 资金表现
    total_return = (final_capital - initial_capital) / initial_capital * 100
    print(f"\n【资金表现】")
    print(f"  初始资金: ${initial_capital:,.2f}")
    print(f"  最终资金: ${final_capital:,.2f}")
    print(f"  总收益率: {total_return:.2f}%")
    
    if len(trades_df) > 0:
        # 交易统计
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        
        print(f"\n【交易统计】")
        print(f"  总交易次数: {len(trades_df)}")
        print(f"  盈利交易: {len(winning_trades)} ({len(winning_trades)/len(trades_df)*100:.1f}%)")
        print(f"  亏损交易: {len(losing_trades)} ({len(losing_trades)/len(trades_df)*100:.1f}%)")
        print(f"  胜率: {win_rate:.2f}%")
        print(f"  平均盈利: ${avg_win:,.2f}")
        print(f"  平均亏损: ${avg_loss:,.2f}")
        print(f"  盈亏比: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "  盈亏比: N/A")
        
        # 风险指标
        returns = equity_df['Equity'].pct_change().dropna()
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        running_max = equity_df['Equity'].expanding().max()
        drawdown = (equity_df['Equity'] - running_max) / running_max
        max_dd = drawdown.min() * 100
        
        print(f"\n【风险指标】")
        print(f"  夏普比率: {sharpe:.2f}")
        print(f"  最大回撤: {max_dd:.2f}%")
    
    print("\n" + "="*80 + "\n")


def plot_combined_results(trades_df, equity_df, data):
    """生成合并的图表（修复中文乱码）"""
    print("正在生成综合图表...")
    
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # 1. 权益曲线
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(equity_df['Date'], equity_df['Equity'], 'b-', linewidth=2, label='Account Equity')
    ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Equity ($)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. 收益分布
    ax2 = fig.add_subplot(gs[1, 0])
    if len(trades_df) > 0:
        ax2.hist(trades_df['pnl_pct'] * 100, bins=50, edgecolor='black', alpha=0.7)
        ax2.axvline(x=0, color='r', linestyle='--', linewidth=2)
        ax2.set_title('P&L Distribution (%)', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Return (%)', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.grid(True, alpha=0.3)
    
    # 3. 月度收益
    ax3 = fig.add_subplot(gs[1, 1])
    if len(equity_df) > 0:
        equity_df['Month'] = pd.to_datetime(equity_df['Date']).dt.to_period('M')
        monthly_returns = equity_df.groupby('Month')['Equity'].last().pct_change() * 100
        monthly_returns.plot(kind='bar', ax=ax3, color=['g' if x > 0 else 'r' for x in monthly_returns])
        ax3.set_title('Monthly Returns (%)', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Month', fontsize=12)
        ax3.set_ylabel('Return (%)', fontsize=12)
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.tick_params(axis='x', rotation=45)
    
    # 4. 累计收益
    ax4 = fig.add_subplot(gs[2, 0])
    if len(trades_df) > 0:
        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        ax4.plot(range(len(trades_df)), trades_df['cumulative_pnl'], 'g-', linewidth=2)
        ax4.set_title('Cumulative P&L', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Trade Number', fontsize=12)
        ax4.set_ylabel('Cumulative P&L ($)', fontsize=12)
        ax4.grid(True, alpha=0.3)
    
    # 5. 胜率统计
    ax5 = fig.add_subplot(gs[2, 1])
    if len(trades_df) > 0:
        win_count = len(trades_df[trades_df['pnl'] > 0])
        loss_count = len(trades_df[trades_df['pnl'] <= 0])
        ax5.pie([win_count, loss_count], labels=['Winning', 'Losing'], 
                autopct='%1.1f%%', startangle=90, colors=['green', 'red'])
        ax5.set_title('Win/Loss Ratio', fontsize=14, fontweight='bold')
    
    plt.suptitle('Gold Trading Strategy - Backtest Results', fontsize=16, fontweight='bold', y=0.995)
    
    # 保存
    plt.savefig('backtest_summary.png', dpi=150, bbox_inches='tight')
    print("✅ 图表已保存为 backtest_summary.png\n")
    plt.close()


def main():
    print("="*80)
    print("Gold Trading Strategy - Simplified Backtest".center(80))
    print("="*80)
    
    # 加载配置
    config = Config()
    
    # 读取数据
    print(f"\n正在加载数据...")
    df = pd.read_csv('XAU_15m_data.csv', sep=';')
    df['Date'] = pd.to_datetime(df['Date'], format='%Y.%m.%d %H:%M')
    df.set_index('Date', inplace=True)
    
    # 过滤日期
    df = df[(df.index >= config.START_DATE) & (df.index <= config.END_DATE)]
    print(f"数据范围: {df.index[0]} 至 {df.index[-1]}")
    print(f"数据条数: {len(df)}\n")
    
    # 计算指标
    df = calculate_technical_indicators(df, config)
    
    # 初始化策略
    print("初始化策略...")
    strategy = GoldTradingStrategy(config)
    print("✅ 策略初始化完成\n")
    
    # 运行回测
    trades_df, equity_df, final_capital = run_backtest_simple(
        df, strategy, config.INITIAL_CAPITAL
    )
    
    # 打印结果
    print_results(trades_df, equity_df, final_capital, config.INITIAL_CAPITAL)
    
    # 保存详细交易记录到txt文件
    if len(trades_df) > 0:
        save_trades_to_txt(trades_df, final_capital, config.INITIAL_CAPITAL, 'trade_details.txt')
        
        # 生成图表
        plot_combined_results(trades_df, equity_df, df)
    
    print("✅ 回测完成！")
    print(f"📁 交易详情已保存到: trade_details.txt")
    print(f"📊 回测图表已保存到: backtest_summary.png")

if __name__ == "__main__":
    main()

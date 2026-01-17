#!/usr/bin/env python3
"""
Luxy Momentum策略回测脚本
- 使用5分钟黄金数据
- 2016-2025年回测
- R-multiple分批止盈
- 完整性能分析和可视化
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from luxy_config import LuxyConfig
from luxy_strategy import LuxyStrategy, SignalType, Position


def load_data(csv_file: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    加载CSV数据并过滤日期范围
    
    Args:
        csv_file: CSV文件路径
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        DataFrame
    """
    print(f"\n{'='*80}")
    print(f"正在加载数据: {csv_file}")
    print(f"日期范围: {start_date} 至 {end_date}")
    print(f"{'='*80}\n")
    
    # 读取CSV（分号分隔）
    data = pd.read_csv(csv_file, sep=';')
    
    print(f"原始数据: {len(data)} 条")
    
    # 转换日期
    data['Date'] = pd.to_datetime(data['Date'], format='%Y.%m.%d %H:%M')
    data = data.set_index('Date')
    
    # 按日期排序
    data = data.sort_index()
    
    # 过滤日期范围
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    data = data[(data.index >= start_dt) & (data.index <= end_dt)]
    
    print(f"过滤后数据: {len(data)} 条")
    print(f"实际时间范围: {data.index[0]} 至 {data.index[-1]}")
    print(f"数据列: {data.columns.tolist()}\n")
    
    return data


def run_backtest(data: pd.DataFrame, strategy: LuxyStrategy, 
                config: LuxyConfig) -> tuple:
    """
    运行回测
    
    Args:
        data: 包含所有指标的数据
        strategy: 策略实例
        config: 配置
        
    Returns:
        (trades_df, equity_curve, final_capital)
    """
    print(f"\n{'='*80}")
    print("开始回测...")
    print(f"初始资金: ${config.INITIAL_CAPITAL:,.2f}")
    print(f"{'='*80}\n")
    
    # 初始化
    capital = config.INITIAL_CAPITAL
    position: Optional[Position] = None
    trades = []
    equity_curve = []
    
    # 统计信息
    total_signals = 0
    total_trades = 0
    
    for i in range(len(data)):
        current_price = data['Close'].iloc[i]
        current_time = data.index[i]
        
        # 生成信号
        signal = strategy.generate_signal(data, i)
        
        if signal.signal_type != SignalType.HOLD:
            total_signals += 1
        
        # 记录权益
        if position:
            pnl = position.calculate_pnl(current_price)
            equity = capital + pnl
        else:
            equity = capital
        
        equity_curve.append({
            'Date': current_time,
            'Equity': equity,
            'Capital': capital,
            'Position': 1 if position else 0
        })
        
        # 检查平仓条件
        if position:
            should_exit, exit_reason, exit_size = strategy.check_exit_conditions(
                data, i, position
            )
            
            if should_exit:
                # 平仓（可能是部分平仓）
                exit_price = current_price
                
                # 计算盈亏
                if position.direction == 1:  # 多头
                    pnl = (exit_price - position.entry_price) * exit_size
                else:  # 空头
                    pnl = (position.entry_price - exit_price) * exit_size
                
                # 扣除手续费
                commission = exit_size * exit_price * config.COMMISSION_RATE
                net_pnl = pnl - commission
                
                # 更新资金
                capital += net_pnl
                
                # 计算盈亏百分比
                pnl_pct = pnl / (position.entry_price * exit_size)
                r_multiple = position.get_r_multiple(exit_price)
                
                # 记录交易
                trades.append({
                    'entry_date': position.entry_time,
                    'exit_date': current_time,
                    'direction': 'LONG' if position.direction == 1 else 'SHORT',
                    'entry_price': position.entry_price,
                    'exit_price': exit_price,
                    'position_size': exit_size,
                    'stop_loss': position.stop_loss,
                    'trailing_stop': position.trailing_stop,
                    'pnl': net_pnl,
                    'pnl_pct': pnl_pct,
                    'r_multiple': r_multiple,
                    'exit_reason': exit_reason,
                    'commission': commission
                })
                
                total_trades += 1
                
                if config.VERBOSE:
                    print(f"[{current_time}] 平仓 {exit_reason}")
                    print(f"  方向: {trades[-1]['direction']}")
                    print(f"  入场: ${position.entry_price:.2f} → 出场: ${exit_price:.2f}")
                    print(f"  盈亏: ${net_pnl:,.2f} ({pnl_pct*100:+.2f}%) | R倍数: {r_multiple:.2f}R")
                    print(f"  资金: ${capital:,.2f}\n")
                
                # 更新持仓
                position.remaining_size -= exit_size
                
                # 如果完全平仓
                if position.remaining_size <= 0:
                    position = None
        
        # 开仓信号
        if position is None and signal.confidence >= config.SIGNAL_THRESHOLD:
            if signal.signal_type == SignalType.BUY:
                # 做多
                position_value = capital * config.POSITION_SIZE
                position_size = position_value / current_price
                
                if position_size > 0:
                    # 计算止损
                    stop_loss = strategy.calculate_stop_loss(
                        data, i, current_price, direction=1
                    )
                    
                    # 计算初始风险R
                    initial_risk = abs(current_price - stop_loss)
                    
                    # 创建持仓
                    position = Position(
                        entry_price=current_price,
                        entry_time=current_time,
                        direction=1,
                        size=position_size,
                        stop_loss=stop_loss,
                        initial_risk=initial_risk
                    )
                    
                    # 计算R-multiple止盈位
                    tp1, tp2, tp3 = strategy.calculate_take_profit_levels(
                        current_price, stop_loss, direction=1
                    )
                    position.tp1_price = tp1
                    position.tp2_price = tp2
                    position.tp3_price = tp3
                    
                    # 初始化追踪止损
                    position.trailing_stop = stop_loss
                    
                    # 扣除手续费
                    commission = position_size * current_price * config.COMMISSION_RATE
                    capital -= commission
                    
                    if config.VERBOSE:
                        print(f"[{current_time}] 开多仓")
                        print(f"  价格: ${current_price:.2f}")
                        print(f"  仓位: {position_size:.4f} ({config.POSITION_SIZE*100}%资金)")
                        print(f"  止损: ${stop_loss:.2f} (R=${initial_risk:.2f})")
                        print(f"  TP1: ${tp1:.2f} ({config.TP1_R_MULTIPLE}R)")
                        print(f"  TP2: ${tp2:.2f} ({config.TP2_R_MULTIPLE}R)")
                        print(f"  TP3: ${tp3:.2f} ({config.TP3_R_MULTIPLE}R)")
                        print(f"  手续费: ${commission:.2f}")
                        print(f"  剩余资金: ${capital:,.2f}\n")
            
            elif signal.signal_type == SignalType.SELL and config.ENABLE_SHORT:
                # 做空
                position_value = capital * config.POSITION_SIZE
                position_size = position_value / current_price
                
                if position_size > 0:
                    # 计算止损
                    stop_loss = strategy.calculate_stop_loss(
                        data, i, current_price, direction=-1
                    )
                    
                    # 计算初始风险R
                    initial_risk = abs(stop_loss - current_price)
                    
                    # 创建持仓
                    position = Position(
                        entry_price=current_price,
                        entry_time=current_time,
                        direction=-1,
                        size=position_size,
                        stop_loss=stop_loss,
                        initial_risk=initial_risk
                    )
                    
                    # 计算R-multiple止盈位
                    tp1, tp2, tp3 = strategy.calculate_take_profit_levels(
                        current_price, stop_loss, direction=-1
                    )
                    position.tp1_price = tp1
                    position.tp2_price = tp2
                    position.tp3_price = tp3
                    
                    # 初始化追踪止损
                    position.trailing_stop = stop_loss
                    
                    # 扣除手续费
                    commission = position_size * current_price * config.COMMISSION_RATE
                    capital -= commission
                    
                    if config.VERBOSE:
                        print(f"[{current_time}] 开空仓")
                        print(f"  价格: ${current_price:.2f}")
                        print(f"  仓位: {position_size:.4f}")
                        print(f"  止损: ${stop_loss:.2f} (R=${initial_risk:.2f})")
                        print(f"  TP1: ${tp1:.2f} ({config.TP1_R_MULTIPLE}R)")
                        print(f"  TP2: ${tp2:.2f} ({config.TP2_R_MULTIPLE}R)")
                        print(f"  TP3: ${tp3:.2f} ({config.TP3_R_MULTIPLE}R)\n")
    
    # 最后一天如果还有持仓，强制平仓
    if position:
        final_price = data['Close'].iloc[-1]
        pnl = position.calculate_pnl(final_price)
        commission = position.remaining_size * final_price * config.COMMISSION_RATE
        capital += pnl - commission
        
        trades.append({
            'entry_date': position.entry_time,
            'exit_date': data.index[-1],
            'direction': 'LONG' if position.direction == 1 else 'SHORT',
            'entry_price': position.entry_price,
            'exit_price': final_price,
            'position_size': position.remaining_size,
            'stop_loss': position.stop_loss,
            'trailing_stop': position.trailing_stop,
            'pnl': pnl - commission,
            'pnl_pct': position.calculate_pnl_pct(final_price),
            'r_multiple': position.get_r_multiple(final_price),
            'exit_reason': '强制平仓',
            'commission': commission
        })
    
    print(f"\n{'='*80}")
    print(f"回测完成！")
    print(f"总信号数: {total_signals}")
    print(f"总交易数: {total_trades}")
    print(f"最终资金: ${capital:,.2f}")
    print(f"{'='*80}\n")
    
    return pd.DataFrame(trades), pd.DataFrame(equity_curve), capital


def calculate_performance_metrics(trades_df: pd.DataFrame, equity_curve: pd.DataFrame,
                                  initial_capital: float, final_capital: float) -> dict:
    """计算性能指标"""
    
    if len(trades_df) == 0:
        return {
            'total_return': 0.0,
            'total_return_pct': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'sharpe_ratio': 0.0,
            'avg_r_multiple': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }
    
    # 基础指标
    total_return = final_capital - initial_capital
    total_return_pct = (total_return / initial_capital) * 100
    
    # 交易统计
    winning_trades = trades_df[trades_df['pnl'] > 0]
    losing_trades = trades_df[trades_df['pnl'] <= 0]
    
    win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
    
    avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
    
    total_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
    total_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else 0
    
    # R-multiple统计
    avg_r_multiple = trades_df['r_multiple'].mean()
    
    # 最大回撤
    equity_series = equity_curve['Equity']
    running_max = equity_series.expanding().max()
    drawdown = equity_series - running_max
    max_drawdown = drawdown.min()
    max_drawdown_pct = (max_drawdown / running_max.max()) * 100 if running_max.max() > 0 else 0
    
    # Sharpe Ratio（年化）
    equity_returns = equity_series.pct_change().dropna()
    if len(equity_returns) > 0 and equity_returns.std() > 0:
        # 假设5分钟数据，一年约有105120个5分钟周期（365*24*12）
        sharpe_ratio = (equity_returns.mean() / equity_returns.std()) * np.sqrt(105120)
    else:
        sharpe_ratio = 0
    
    return {
        'total_return': total_return,
        'total_return_pct': total_return_pct,
        'total_trades': len(trades_df),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'sharpe_ratio': sharpe_ratio,
        'avg_r_multiple': avg_r_multiple,
        'best_trade': trades_df['pnl'].max(),
        'worst_trade': trades_df['pnl'].min()
    }


def print_performance_report(metrics: dict, config: LuxyConfig):
    """打印性能报告"""
    
    print(f"\n{'='*80}")
    print("PERFORMANCE REPORT".center(80))
    print(f"{'='*80}\n")
    
    print(f"{'回报指标':-^80}")
    print(f"总收益:           ${metrics['total_return']:>15,.2f}")
    print(f"总收益率:         {metrics['total_return_pct']:>15.2f}%")
    print(f"夏普比率:         {metrics['sharpe_ratio']:>15.2f}")
    print(f"最大回撤:         ${metrics['max_drawdown']:>15,.2f}")
    print(f"最大回撤率:       {metrics['max_drawdown_pct']:>15.2f}%\n")
    
    print(f"{'交易统计':-^80}")
    print(f"总交易数:         {metrics['total_trades']:>15}")
    print(f"盈利交易:         {metrics['winning_trades']:>15}")
    print(f"亏损交易:         {metrics['losing_trades']:>15}")
    print(f"胜率:             {metrics['win_rate']:>15.2f}%\n")
    
    print(f"{'盈亏分析':-^80}")
    print(f"平均盈利:         ${metrics['avg_win']:>15,.2f}")
    print(f"平均亏损:         ${metrics['avg_loss']:>15,.2f}")
    print(f"盈亏比:           {abs(metrics['avg_win']/metrics['avg_loss']) if metrics['avg_loss'] != 0 else 0:>15.2f}")
    print(f"盈利因子:         {metrics['profit_factor']:>15.2f}")
    print(f"平均R倍数:        {metrics['avg_r_multiple']:>15.2f}R\n")
    
    print(f"{'极值统计':-^80}")
    print(f"最佳交易:         ${metrics['best_trade']:>15,.2f}")
    print(f"最差交易:         ${metrics['worst_trade']:>15,.2f}\n")
    
    print(f"{'='*80}\n")


def plot_results(data: pd.DataFrame, trades_df: pd.DataFrame, 
                equity_curve: pd.DataFrame, config: LuxyConfig):
    """绘制结果图表"""
    
    print("正在生成图表...")
    
    fig = plt.figure(figsize=(16, 12))
    
    # 1. 价格和信号
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(data.index, data['Close'], label='Price', linewidth=0.8, alpha=0.7)
    ax1.plot(data.index, data['UT_Stop'], label='UT Bot Stop', 
             linewidth=0.8, alpha=0.6, linestyle='--')
    ax1.plot(data.index, data['SuperTrend'], label='SuperTrend', 
             linewidth=0.8, alpha=0.6)
    
    # 标记交易
    for _, trade in trades_df.iterrows():
        if trade['direction'] == 'LONG':
            ax1.scatter(trade['entry_date'], trade['entry_price'], 
                       color='green', marker='^', s=100, zorder=5)
            ax1.scatter(trade['exit_date'], trade['exit_price'], 
                       color='red', marker='v', s=100, zorder=5)
        else:
            ax1.scatter(trade['entry_date'], trade['entry_price'], 
                       color='red', marker='v', s=100, zorder=5)
            ax1.scatter(trade['exit_date'], trade['exit_price'], 
                       color='green', marker='^', s=100, zorder=5)
    
    ax1.set_title('Gold Price & Trading Signals', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price ($)')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # 2. 权益曲线
    ax2 = plt.subplot(4, 1, 2)
    ax2.plot(equity_curve['Date'], equity_curve['Equity'], 
             label='Equity', linewidth=1.5, color='blue')
    ax2.axhline(y=config.INITIAL_CAPITAL, color='gray', 
                linestyle='--', linewidth=1, alpha=0.5)
    ax2.fill_between(equity_curve['Date'], config.INITIAL_CAPITAL, 
                     equity_curve['Equity'], 
                     where=equity_curve['Equity'] >= config.INITIAL_CAPITAL,
                     alpha=0.3, color='green', label='Profit')
    ax2.fill_between(equity_curve['Date'], config.INITIAL_CAPITAL, 
                     equity_curve['Equity'],
                     where=equity_curve['Equity'] < config.INITIAL_CAPITAL,
                     alpha=0.3, color='red', label='Loss')
    
    ax2.set_title('Equity Curve', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Equity ($)')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    
    # 3. ADX和成交量比率
    ax3 = plt.subplot(4, 1, 3)
    ax3.plot(data.index, data['ADX'], label='ADX', linewidth=1, color='purple')
    ax3.axhline(y=config.MIN_ADX, color='red', linestyle='--', 
                linewidth=1, alpha=0.5, label=f'ADX Threshold ({config.MIN_ADX})')
    ax3.set_title('ADX Trend Strength', fontsize=14, fontweight='bold')
    ax3.set_ylabel('ADX')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)
    
    # 4. 交易盈亏分布
    ax4 = plt.subplot(4, 1, 4)
    if len(trades_df) > 0:
        colors = ['green' if x > 0 else 'red' for x in trades_df['pnl']]
        ax4.bar(range(len(trades_df)), trades_df['pnl'], color=colors, alpha=0.6)
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax4.set_title('Trade P&L Distribution', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Trade Number')
        ax4.set_ylabel('P&L ($)')
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    filename = f'luxy_backtest_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"✅ 图表已保存: {filename}\n")
    
    plt.show()


def save_trades_detail(trades_df: pd.DataFrame, metrics: dict, 
                      config: LuxyConfig, filename: str = 'luxy_trades_detail.txt'):
    """保存详细交易记录"""
    
    print(f"正在保存交易详情到 {filename}...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("Luxy Momentum Strategy - Detailed Trade Log\n".center(100))
        f.write("="*100 + "\n\n")
        
        # 策略配置
        f.write("STRATEGY CONFIGURATION:\n")
        f.write("-"*100 + "\n")
        f.write(f"Data Period:        {config.START_DATE} to {config.END_DATE}\n")
        f.write(f"Initial Capital:    ${config.INITIAL_CAPITAL:,.2f}\n")
        f.write(f"Position Size:      {config.POSITION_SIZE*100}%\n")
        f.write(f"Commission Rate:    {config.COMMISSION_RATE*100}%\n")
        f.write(f"R-Multiple TP:      {config.TP1_R_MULTIPLE}R / {config.TP2_R_MULTIPLE}R / {config.TP3_R_MULTIPLE}R\n")
        f.write(f"ATR Stop Loss:      {config.ATR_SL_MULTIPLIER}×ATR\n")
        f.write(f"Min ADX:            {config.MIN_ADX}\n")
        f.write(f"Min Volume Ratio:   {config.MIN_VOLUME_RATIO}\n")
        f.write("\n" + "="*100 + "\n\n")
        
        # 性能摘要
        f.write("PERFORMANCE SUMMARY:\n")
        f.write("-"*100 + "\n")
        f.write(f"Total Return:       ${metrics['total_return']:,.2f} ({metrics['total_return_pct']:.2f}%)\n")
        f.write(f"Total Trades:       {metrics['total_trades']}\n")
        f.write(f"Win Rate:           {metrics['win_rate']:.2f}%\n")
        f.write(f"Profit Factor:      {metrics['profit_factor']:.2f}\n")
        f.write(f"Avg R-Multiple:     {metrics['avg_r_multiple']:.2f}R\n")
        f.write(f"Max Drawdown:       ${metrics['max_drawdown']:,.2f} ({metrics['max_drawdown_pct']:.2f}%)\n")
        f.write(f"Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}\n")
        f.write("\n" + "="*100 + "\n\n")
        
        # 详细交易记录
        f.write("DETAILED TRADE RECORDS:\n")
        f.write("-"*100 + "\n\n")
        
        cumulative_pnl = 0
        for idx, trade in trades_df.iterrows():
            cumulative_pnl += trade['pnl']
            
            f.write(f"Trade #{idx + 1}\n")
            f.write(f"  Direction:      {trade['direction']}\n")
            f.write(f"  Entry Date:     {trade['entry_date']}\n")
            f.write(f"  Exit Date:      {trade['exit_date']}\n")
            f.write(f"  Entry Price:    ${trade['entry_price']:,.2f}\n")
            f.write(f"  Exit Price:     ${trade['exit_price']:,.2f}\n")
            f.write(f"  Position Size:  {trade['position_size']:.4f} contracts\n")
            f.write(f"  Stop Loss:      ${trade['stop_loss']:,.2f}\n")
            f.write(f"  Trail Stop:     ${trade['trailing_stop']:,.2f}\n")
            f.write(f"  P&L:            ${trade['pnl']:,.2f} ({trade['pnl_pct']*100:+.2f}%)\n")
            f.write(f"  R-Multiple:     {trade['r_multiple']:.2f}R\n")
            f.write(f"  Cumulative P&L: ${cumulative_pnl:,.2f}\n")
            f.write(f"  Exit Reason:    {trade['exit_reason']}\n")
            f.write(f"  Commission:     ${trade['commission']:.2f}\n")
            f.write("-"*100 + "\n\n")
        
        f.write("="*100 + "\n")
        f.write("End of Report\n".center(100))
        f.write("="*100 + "\n")
    
    print(f"✅ 交易详情已保存: {filename}\n")


def main():
    """主函数"""
    
    # 创建配置和策略
    config = LuxyConfig()
    config.print_config()
    
    strategy = LuxyStrategy(config)
    
    # 加载数据
    data = load_data(config.DATA_FILE, config.START_DATE, config.END_DATE)
    
    # 计算技术指标
    data_with_indicators = strategy.calculate_all_indicators(data)
    
    # 运行回测
    trades_df, equity_curve, final_capital = run_backtest(
        data_with_indicators, strategy, config
    )
    
    # 计算性能指标
    metrics = calculate_performance_metrics(
        trades_df, equity_curve, config.INITIAL_CAPITAL, final_capital
    )
    
    # 打印性能报告
    print_performance_report(metrics, config)
    
    # 保存交易详情
    if config.SAVE_TRADES and len(trades_df) > 0:
        save_trades_detail(trades_df, metrics, config)
    
    # 绘制结果图表
    if config.PLOT_SIGNALS and len(trades_df) > 0:
        plot_results(data_with_indicators, trades_df, equity_curve, config)
    
    print("\n" + "="*80)
    print("回测完成！".center(80))
    print("="*80 + "\n")


if __name__ == '__main__':
    main()

"""
性能分析和可视化模块
分析回测结果并生成图表和报告
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.dates as mdates
import seaborn as sns
from typing import Optional
import warnings

from backtest_engine import BacktestResult

warnings.filterwarnings('ignore')

# 设置中文字体
_preferred_fonts = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'Sarasa Gothic SC', 'Noto Sans CJK SC', 'DejaVu Sans']
available_font_names = {f.name for f in font_manager.fontManager.ttflist}
for font_name in _preferred_fonts:
    if any(font_name in name for name in available_font_names):
        plt.rcParams['font.sans-serif'] = [font_name]
        break
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8-darkgrid')


class PerformanceAnalyzer:
    """性能分析器类"""
    
    def __init__(self, result: BacktestResult):
        self.result = result
        self.equity_curve = result.equity_curve
        self.trades_details = result.trades_details
        self.daily_returns = result.daily_returns
    
    def print_summary(self):
        """打印性能摘要报告"""
        print("\n" + "=" * 60)
        print("📈 步骤 4/4: 性能分析报告")
        print("=" * 60)
        
        # 基础信息
        print(f"\n回测期间: {self.result.start_date.strftime('%Y-%m-%d')} 到 {self.result.end_date.strftime('%Y-%m-%d')}")
        total_days = (self.result.end_date - self.result.start_date).days
        print(f"回测天数: {total_days} 天")
        
        print("\n" + "-" * 25 + " 资金表现 " + "-" * 25)
        print(f"初始资金: ${self.result.initial_capital:,.2f}")
        print(f"最终资金: ${self.result.final_capital:,.2f}")
        print(f"绝对收益: ${self.result.final_capital - self.result.initial_capital:,.2f}")
        print(f"总收益率: {self.result.total_return:.2%}")
        print(f"年化收益率: {self.result.annual_return:.2%}")
        
        print("\n" + "-" * 25 + " 风险指标 " + "-" * 25)
        print(f"夏普比率: {self.result.sharpe_ratio:.3f}")
        print(f"最大回撤: {self.result.max_drawdown:.2%}")
        
        # 波动率和卡尔玛比率
        if len(self.daily_returns) > 1:
            volatility = self.daily_returns.std() * np.sqrt(252)
            print(f"年化波动率: {volatility:.2%}")
            
            calmar_ratio = self.result.annual_return / abs(self.result.max_drawdown) if self.result.max_drawdown != 0 else 0
            print(f"卡尔玛比率: {calmar_ratio:.3f}")
        
        print("\n" + "-" * 25 + " 交易统计 " + "-" * 25)
        print(f"总交易次数: {self.result.total_trades}")
        print(f"盈利交易: {self.result.profitable_trades}")
        print(f"亏损交易: {self.result.losing_trades}")
        print(f"胜率: {self.result.win_rate:.2%}")
        
        if self.result.profit_factor != float('inf'):
            print(f"盈利因子: {self.result.profit_factor:.2f}")
        else:
            print(f"盈利因子: ∞ (无亏损交易)")
        
        if self.result.total_trades > 0:
            print(f"平均单笔收益率: {self.result.avg_trade_return:.2%}")
            print(f"平均盈利交易: ${self.result.avg_winning_trade:,.2f}")
            if self.result.avg_losing_trade < 0:
                print(f"平均亏损交易: ${self.result.avg_losing_trade:,.2f}")
            print(f"最大盈利交易: ${self.result.max_winning_trade:,.2f}")
            if self.result.max_losing_trade < 0:
                print(f"最大亏损交易: ${self.result.max_losing_trade:,.2f}")
            print(f"平均持仓天数: {self.result.avg_holding_period:.1f} 天")
            print(f"最长持仓天数: {self.result.max_holding_period} 天")
        
        print("\n" + "=" * 60)
    
    def plot_equity_curve(self, figsize=(14, 10)):
        """绘制权益曲线和回撤图"""
        if self.equity_curve.empty:
            print("⚠️  无权益数据可供绘制")
            return
        
        fig, axes = plt.subplots(3, 1, figsize=figsize, gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # 1. 权益曲线
        axes[0].plot(self.equity_curve.index, self.equity_curve['equity'], 
                    linewidth=2, color='#2E86AB', label='投资组合价值', alpha=0.9)
        axes[0].axhline(y=self.result.initial_capital, color='gray', linestyle='--', 
                       linewidth=1, alpha=0.5, label='初始资金')
        axes[0].fill_between(self.equity_curve.index, self.result.initial_capital, 
                            self.equity_curve['equity'], 
                            where=(self.equity_curve['equity'] >= self.result.initial_capital),
                            alpha=0.3, color='green', label='盈利区域')
        axes[0].fill_between(self.equity_curve.index, self.result.initial_capital, 
                            self.equity_curve['equity'], 
                            where=(self.equity_curve['equity'] < self.result.initial_capital),
                            alpha=0.3, color='red', label='亏损区域')
        axes[0].set_title('究极策略 - 投资组合权益曲线', fontsize=16, fontweight='bold', pad=15)
        axes[0].set_ylabel('资产价值 (USD)', fontsize=12)
        axes[0].legend(loc='upper left', fontsize=10)
        axes[0].grid(True, alpha=0.3, linestyle='--')
        
        # 2. 回撤曲线
        peak = self.equity_curve['equity'].expanding(min_periods=1).max()
        drawdown = (self.equity_curve['equity'] - peak) / peak * 100
        axes[1].fill_between(self.equity_curve.index, drawdown, 0, 
                            alpha=0.5, color='#A23B72', label='回撤')
        axes[1].axhline(y=self.result.max_drawdown * 100, color='red', 
                       linestyle='--', linewidth=1.5, alpha=0.7, 
                       label=f'最大回撤: {self.result.max_drawdown:.2%}')
        axes[1].set_title('回撤曲线', fontsize=14, fontweight='bold')
        axes[1].set_ylabel('回撤 (%)', fontsize=12)
        axes[1].legend(loc='lower left', fontsize=10)
        axes[1].grid(True, alpha=0.3, linestyle='--')
        
        # 3. 持仓情况
        axes[2].fill_between(self.equity_curve.index, 0, self.equity_curve['position'], 
                            alpha=0.4, color='#F18F01', label='持仓数量')
        axes[2].set_title('持仓变化', fontsize=14, fontweight='bold')
        axes[2].set_ylabel('持仓数量', fontsize=12)
        axes[2].set_xlabel('日期', fontsize=12)
        axes[2].legend(loc='upper left', fontsize=10)
        axes[2].grid(True, alpha=0.3, linestyle='--')
        
        # 格式化日期轴
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig('0117_ultimate/equity_curve.png', dpi=300, bbox_inches='tight')
        print("✅ 权益曲线图已保存: 0117_ultimate/equity_curve.png")
        plt.show()
    
    def plot_return_distribution(self, figsize=(12, 6)):
        """绘制收益分布图"""
        if self.daily_returns.empty:
            print("⚠️  无收益数据可供绘制")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # 1. 日收益率直方图
        ax1.hist(self.daily_returns, bins=50, alpha=0.7, color='#06A77D', 
                edgecolor='black', linewidth=0.5, density=True)
        
        mean_return = self.daily_returns.mean()
        ax1.axvline(mean_return, color='red', linestyle='--', linewidth=2, 
                   label=f'平均: {mean_return:.2%}')
        
        # 正态分布拟合
        x = np.linspace(self.daily_returns.min(), self.daily_returns.max(), 100)
        std = self.daily_returns.std()
        y = (1/(std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean_return) / std) ** 2)
        ax1.plot(x, y, 'r-', linewidth=2, label='正态分布拟合', alpha=0.7)
        
        ax1.set_title('日收益率分布', fontsize=14, fontweight='bold')
        ax1.set_xlabel('日收益率', fontsize=12)
        ax1.set_ylabel('密度', fontsize=12)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. 累计收益率曲线
        cumulative_returns = (1 + self.daily_returns).cumprod() - 1
        ax2.plot(cumulative_returns.index, cumulative_returns * 100, 
                linewidth=2, color='#D62246', alpha=0.8)
        ax2.fill_between(cumulative_returns.index, 0, cumulative_returns * 100, 
                        alpha=0.3, color='#D62246')
        ax2.set_title('累计收益率曲线', fontsize=14, fontweight='bold')
        ax2.set_xlabel('日期', fontsize=12)
        ax2.set_ylabel('累计收益率 (%)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig('0117_ultimate/return_distribution.png', dpi=300, bbox_inches='tight')
        print("✅ 收益分布图已保存: 0117_ultimate/return_distribution.png")
        plt.show()
    
    def plot_trade_analysis(self, figsize=(14, 10)):
        """绘制交易分析图"""
        if self.result.total_trades == 0:
            print("⚠️  无交易数据可供分析")
            return
        
        fig = plt.figure(figsize=figsize)
        
        # 1. 月度收益热力图
        ax1 = plt.subplot(2, 2, 1)
        monthly_returns = self.equity_curve['equity'].resample('M').last().pct_change().dropna()
        if len(monthly_returns) > 0:
            monthly_df = pd.DataFrame(monthly_returns)
            monthly_df.columns = ['return']
            monthly_df['year'] = monthly_df.index.year
            monthly_df['month'] = monthly_df.index.month
            pivot_table = monthly_df.pivot(index='year', columns='month', values='return')
            
            sns.heatmap(pivot_table, annot=True, fmt='.1%', cmap='RdYlGn', center=0,
                       cbar_kws={'label': '月度收益率'}, ax=ax1, linewidths=0.5)
            ax1.set_title('月度收益率热力图', fontsize=14, fontweight='bold')
            ax1.set_xlabel('月份', fontsize=11)
            ax1.set_ylabel('年份', fontsize=11)
        
        # 2. 关键绩效指标
        ax2 = plt.subplot(2, 2, 2)
        metrics = ['胜率', '盈利因子', '夏普比率']
        values = [
            self.result.win_rate * 100,
            min(self.result.profit_factor, 5) if self.result.profit_factor != float('inf') else 5,
            max(0, self.result.sharpe_ratio)
        ]
        colors = ['#06A77D', '#2E86AB', '#F18F01']
        
        bars = ax2.bar(metrics, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
        ax2.set_title('关键绩效指标', fontsize=14, fontweight='bold')
        ax2.set_ylabel('数值', fontsize=12)
        ax2.grid(True, alpha=0.3, axis='y')
        
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.2f}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # 3. 交易盈亏分布
        ax3 = plt.subplot(2, 2, 3)
        if not self.trades_details.empty:
            sell_trades = self.trades_details[self.trades_details['action'] == 'SELL']
            if len(sell_trades) > 0:
                winning_trades = sell_trades[sell_trades['pnl'] > 0]['pnl']
                losing_trades = sell_trades[sell_trades['pnl'] < 0]['pnl']
                
                ax3.hist([winning_trades, losing_trades], bins=20, 
                        label=['盈利交易', '亏损交易'],
                        color=['green', 'red'], alpha=0.7, edgecolor='black')
                ax3.set_title('交易盈亏分布', fontsize=14, fontweight='bold')
                ax3.set_xlabel('盈亏金额 (USD)', fontsize=12)
                ax3.set_ylabel('交易次数', fontsize=12)
                ax3.legend(fontsize=10)
                ax3.grid(True, alpha=0.3)
        
        # 4. 持仓时间分析
        ax4 = plt.subplot(2, 2, 4)
        if not self.trades_details.empty:
            sell_trades = self.trades_details[self.trades_details['action'] == 'SELL']
            if len(sell_trades) > 0 and 'holding_days' in sell_trades.columns:
                holding_days = sell_trades['holding_days']
                ax4.hist(holding_days, bins=20, color='#A23B72', alpha=0.7, 
                        edgecolor='black', linewidth=0.5)
                ax4.axvline(self.result.avg_holding_period, color='red', 
                           linestyle='--', linewidth=2, 
                           label=f'平均: {self.result.avg_holding_period:.1f}天')
                ax4.set_title('持仓时间分布', fontsize=14, fontweight='bold')
                ax4.set_xlabel('持仓天数', fontsize=12)
                ax4.set_ylabel('交易次数', fontsize=12)
                ax4.legend(fontsize=10)
                ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('0117_ultimate/trade_analysis.png', dpi=300, bbox_inches='tight')
        print("✅ 交易分析图已保存: 0117_ultimate/trade_analysis.png")
        plt.show()
    
    def generate_report(self):
        """生成完整的分析报告"""
        print("\n" + "=" * 60)
        print("📊 生成完整分析报告")
        print("=" * 60)
        
        self.print_summary()
        self.plot_equity_curve()
        self.plot_return_distribution()
        self.plot_trade_analysis()
        
        print("\n✅ 分析报告生成完成！")

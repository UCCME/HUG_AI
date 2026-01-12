"""
性能分析和可视化模块
用于分析回测结果并生成图表
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.dates as mdates
import seaborn as sns
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from backtest_engine import BacktestResult

# 设置中文字体和样式，自动选择可用的中文字体，避免乱码
_preferred_fonts = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'Sarasa Gothic SC', 'Noto Sans CJK SC', 'DejaVu Sans']
available_font_names = {f.name for f in font_manager.fontManager.ttflist}
for font_name in _preferred_fonts:
    # 一些字体名字在列表里带后缀，使用包含匹配
    if any(font_name in name for name in available_font_names):
        plt.rcParams['font.sans-serif'] = [font_name]
        break
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8')

class PerformanceAnalyzer:
    """
    性能分析器类
    分析回测结果并生成各种图表和报告
    """
    
    def __init__(self, backtest_result: BacktestResult):
        self.result = backtest_result
        self.equity_curve = backtest_result.equity_curve
        self.trades_details = backtest_result.trades_details
        self.daily_returns = backtest_result.daily_returns
    
    def print_performance_summary(self):
        """打印性能摘要报告"""
        print("=" * 60)
        print("                  回测性能报告")
        print("=" * 60)
        
        # 基础信息
        print(f"回测期间: {self.result.start_date.strftime('%Y-%m-%d')} 到 {self.result.end_date.strftime('%Y-%m-%d')}")
        total_days = (self.result.end_date - self.result.start_date).days
        print(f"回测天数: {total_days} 天")
        
        print("\n" + "-" * 30 + " 资金表现 " + "-" * 30)
        print(f"初始资金: ${self.result.initial_capital:,.2f}")
        print(f"最终资金: ${self.result.final_capital:,.2f}")
        print(f"绝对收益: ${self.result.final_capital - self.result.initial_capital:,.2f}")
        print(f"总收益率: {self.result.total_return:.2%}")
        print(f"年化收益率: {self.result.annual_return:.2%}")
        
        print("\n" + "-" * 30 + " 风险指标 " + "-" * 30)
        print(f"夏普比率: {self.result.sharpe_ratio:.3f}")
        print(f"最大回撤: {self.result.max_drawdown:.2%}")
        
        # 计算波动率
        if len(self.daily_returns) > 1:
            volatility = self.daily_returns.std() * np.sqrt(252)
            print(f"年化波动率: {volatility:.2%}")
            
            # 计算卡尔玛比率 (年化收益率 / 最大回撤)
            calmar_ratio = self.result.annual_return / abs(self.result.max_drawdown) if self.result.max_drawdown != 0 else 0
            print(f"卡尔玛比率: {calmar_ratio:.3f}")
        
        print("\n" + "-" * 30 + " 交易统计 " + "-" * 30)
        print(f"总交易次数: {self.result.total_trades}")
        print(f"盈利交易: {self.result.profitable_trades}")
        print(f"亏损交易: {self.result.losing_trades}")
        print(f"胜率: {self.result.win_rate:.2%}")
        
        if self.result.profit_factor != float('inf'):
            print(f"盈利因子: {self.result.profit_factor:.2f}")
        else:
            print(f"盈利因子: 无限大 (无亏损交易)")
        
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
    
    def plot_equity_curve(self, figsize=(12, 8)):
        """
        绘制权益曲线图
        
        Args:
            figsize: 图表尺寸
        """
        if self.equity_curve.empty:
            print("⚠️  无权益数据可供绘制")
            return
            
        fig, axes = plt.subplots(2, 1, figsize=figsize, gridspec_kw={'height_ratios': [3, 1]})
        
        # 权益曲线
        axes[0].plot(self.equity_curve.index, self.equity_curve['equity'], 
                    linewidth=2, color='blue', label='投资组合价值')
        axes[0].set_title('投资组合权益曲线', fontsize=16, fontweight='bold')
        axes[0].set_ylabel('资产价值 (USD)', fontsize=12)
        axes[0].legend(loc='upper left')
        axes[0].grid(True, alpha=0.3)
        
        # 添加回撤曲线
        peak = self.equity_curve['equity'].expanding(min_periods=1).max()
        drawdown = (self.equity_curve['equity'] - peak) / peak * 100
        axes[1].fill_between(self.equity_curve.index, drawdown, 0, 
                            alpha=0.3, color='red', label='回撤 (%)')
        axes[1].set_title('回撤曲线', fontsize=14, fontweight='bold')
        axes[1].set_ylabel('回撤 (%)', fontsize=12)
        axes[1].set_xlabel('日期', fontsize=12)
        axes[1].legend(loc='lower left')
        axes[1].grid(True, alpha=0.3)
        
        # 格式化日期轴
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def plot_return_distribution(self, figsize=(10, 6)):
        """
        绘制收益分布图
        
        Args:
            figsize: 图表尺寸
        """
        if self.daily_returns.empty:
            print("⚠️  无收益数据可供绘制")
            return
            
        fig, ax = plt.subplots(figsize=figsize)
        
        # 绘制直方图
        ax.hist(self.daily_returns, bins=50, alpha=0.7, color='skyblue', edgecolor='black', linewidth=0.5)
        
        # 添加均值线
        mean_return = self.daily_returns.mean()
        ax.axvline(mean_return, color='red', linestyle='--', linewidth=2, 
                  label=f'平均日收益: {mean_return:.2%}')
        
        # 添加正态分布拟合曲线
        x = np.linspace(self.daily_returns.min(), self.daily_returns.max(), 100)
        std = self.daily_returns.std()
        y = (1/(std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean_return) / std) ** 2)
        y_scaled = y * len(self.daily_returns) * (self.daily_returns.max() - self.daily_returns.min()) / 50
        ax.plot(x, y_scaled, 'r-', linewidth=2, label='正态分布拟合')
        
        ax.set_title('日收益率分布', fontsize=16, fontweight='bold')
        ax.set_xlabel('日收益率', fontsize=12)
        ax.set_ylabel('频次', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_trade_analysis(self, figsize=(12, 10)):
        """
        绘制交易分析图
        
        Args:
            figsize: 图表尺寸
        """
        # 创建子图
        fig = plt.figure(figsize=figsize)
        
        # 1. 月度收益热力图
        ax1 = plt.subplot(2, 2, 1)
        if not self.equity_curve.empty:
            monthly_returns = self.equity_curve['equity'].resample('M').last().pct_change()
            monthly_returns.index = monthly_returns.index.strftime('%Y-%m')
            
            # 转换为年度-月份矩阵
            monthly_df = pd.DataFrame(monthly_returns)
            monthly_df['year'] = pd.to_datetime(monthly_df.index).year
            monthly_df['month'] = pd.to_datetime(monthly_df.index).month
            pivot_table = monthly_df.pivot(index='year', columns='month', values='equity')
            
            # 绘制热力图
            sns.heatmap(pivot_table, annot=True, fmt='.2%', cmap='RdYlGn', center=0,
                       cbar_kws={'label': '月度收益率'}, ax=ax1)
            ax1.set_title('月度收益率热力图', fontsize=14, fontweight='bold')
        
        # 2. 累计收益曲线
        ax2 = plt.subplot(2, 2, 2)
        if not self.equity_curve.empty:
            cumulative_returns = (self.equity_curve['equity'] / self.result.initial_capital) - 1
            ax2.plot(cumulative_returns.index, cumulative_returns, linewidth=2, color='purple')
            ax2.set_title('累计收益率曲线', fontsize=14, fontweight='bold')
            ax2.set_ylabel('累计收益率', fontsize=12)
            ax2.grid(True, alpha=0.3)
        
        # 3. 胜率和盈亏比分析
        ax3 = plt.subplot(2, 2, 3)
        if self.result.total_trades > 0:
            metrics = ['胜率', '盈亏比', '夏普比率']
            values = [self.result.win_rate, 
                     self.result.profit_factor if self.result.profit_factor != float('inf') else 2.0,
                     max(0, self.result.sharpe_ratio)]  # 处理负夏普比率
            
            bars = ax3.bar(metrics, values, color=['green', 'blue', 'orange'])
            ax3.set_title('关键绩效指标', fontsize=14, fontweight='bold')
            ax3.set_ylabel('数值', fontsize=12)
            
            # 在柱状图上添加数值标签
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:.2f}' if value < 10 else f'{value:.1f}',
                        ha='center', va='bottom', fontsize=10)
        
        # 4. 持仓时间分布
        ax4 = plt.subplot(2, 2, 4)
        # 简化的持仓时间分布（使用平均值）
        holding_periods = [self.result.avg_holding_period, self.result.max_holding_period]
        labels = ['平均持仓', '最大持仓']
        ax4.bar(labels, holding_periods, color=['lightcoral', 'lightsalmon'])
        ax4.set_title('持仓时间分析', fontsize=14, fontweight='bold')
        ax4.set_ylabel('天数', fontsize=12)
        
        plt.tight_layout()
        plt.show()
    
    def plot_trades_analysis(self, figsize=(15, 10)):
        """
        绘制交易分析图
        
        Args:
            figsize: 图表尺寸
        """
        if self.trades_details.empty:
            print("无交易记录，无法绘制交易分析图")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # 盈亏分布
        profits = self.trades_details['pnl']
        colors = ['green' if x > 0 else 'red' for x in profits]
        
        axes[0, 0].bar(range(len(profits)), profits, color=colors, alpha=0.7)
        axes[0, 0].axhline(y=0, color='black', linestyle='-', linewidth=1)
        axes[0, 0].set_title('每笔交易盈亏', fontsize=12, fontweight='bold')
        axes[0, 0].set_xlabel('交易序号')
        axes[0, 0].set_ylabel('盈亏 ($)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 累积盈亏
        cumulative_pnl = profits.cumsum()
        axes[0, 1].plot(cumulative_pnl, linewidth=2, color='blue')
        axes[0, 1].fill_between(range(len(cumulative_pnl)), cumulative_pnl, 0, 
                               alpha=0.3, color='blue')
        axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=1)
        axes[0, 1].set_title('累积盈亏曲线', fontsize=12, fontweight='bold')
        axes[0, 1].set_xlabel('交易序号')
        axes[0, 1].set_ylabel('累积盈亏 ($)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 持仓天数分布
        holding_days = self.trades_details['holding_days']
        axes[1, 0].hist(holding_days, bins=20, alpha=0.7, color='orange', edgecolor='black')
        axes[1, 0].axvline(holding_days.mean(), color='red', linestyle='--', 
                          label=f'平均: {holding_days.mean():.1f}天')
        axes[1, 0].set_title('持仓天数分布', fontsize=12, fontweight='bold')
        axes[1, 0].set_xlabel('持仓天数')
        axes[1, 0].set_ylabel('频数')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 收益率分布
        return_pct = self.trades_details['return_pct'] * 100  # 转换为百分比
        axes[1, 1].hist(return_pct, bins=20, alpha=0.7, color='purple', edgecolor='black')
        axes[1, 1].axvline(return_pct.mean(), color='red', linestyle='--', 
                          label=f'平均: {return_pct.mean():.1f}%')
        axes[1, 1].axvline(0, color='black', linestyle='-', linewidth=1)
        axes[1, 1].set_title('单笔交易收益率分布', fontsize=12, fontweight='bold')
        axes[1, 1].set_xlabel('收益率 (%)')
        axes[1, 1].set_ylabel('频数')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_rolling_metrics(self, window=60, figsize=(12, 10)):
        """
        绘制滚动性能指标
        
        Args:
            window: 滚动窗口大小（天）
            figsize: 图表尺寸
        """
        if len(self.daily_returns) < window:
            print(f"数据不足，需要至少{window}天的数据")
            return
        
        fig, axes = plt.subplots(3, 1, figsize=figsize)
        
        # 滚动收益率
        rolling_returns = self.daily_returns.rolling(window=window).mean() * 252  # 年化
        axes[0].plot(rolling_returns.index, rolling_returns, linewidth=2, color='blue')
        axes[0].axhline(y=0, color='red', linestyle='--', alpha=0.7)
        axes[0].set_title(f'{window}日滚动年化收益率', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('年化收益率')
        axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        axes[0].grid(True, alpha=0.3)
        
        # 滚动波动率
        rolling_volatility = self.daily_returns.rolling(window=window).std() * np.sqrt(252)
        axes[1].plot(rolling_volatility.index, rolling_volatility, linewidth=2, color='orange')
        axes[1].set_title(f'{window}日滚动年化波动率', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('年化波动率')
        axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        axes[1].grid(True, alpha=0.3)
        
        # 滚动夏普比率
        rolling_sharpe = rolling_returns / rolling_volatility
        axes[2].plot(rolling_sharpe.index, rolling_sharpe, linewidth=2, color='green')
        axes[2].axhline(y=0, color='red', linestyle='--', alpha=0.7)
        axes[2].axhline(y=1, color='gray', linestyle=':', alpha=0.7, label='1.0')
        axes[2].set_title(f'{window}日滚动夏普比率', fontsize=12, fontweight='bold')
        axes[2].set_ylabel('夏普比率')
        axes[2].set_xlabel('日期')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        # 格式化日期轴
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def compare_with_benchmark(self, benchmark_returns: pd.Series, figsize=(12, 8)):
        """
        与基准对比分析
        
        Args:
            benchmark_returns: 基准收益率序列
            figsize: 图表尺寸
        """
        if len(self.daily_returns) <= 1:
            print("策略数据不足，无法进行基准对比")
            return
        
        # 对齐数据
        common_dates = self.daily_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) < 2:
            print("与基准没有足够的共同交易日")
            return
        
        strategy_aligned = self.daily_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # 计算累积收益
        strategy_cumulative = (1 + strategy_aligned).cumprod() - 1
        benchmark_cumulative = (1 + benchmark_aligned).cumprod() - 1
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # 累积收益对比
        axes[0, 0].plot(strategy_cumulative.index, strategy_cumulative, 
                       linewidth=2, label='策略', color='blue')
        axes[0, 0].plot(benchmark_cumulative.index, benchmark_cumulative, 
                       linewidth=2, label='基准', color='red')
        axes[0, 0].set_title('累积收益对比', fontsize=12, fontweight='bold')
        axes[0, 0].set_ylabel('累积收益率')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        # 超额收益
        excess_returns = strategy_aligned - benchmark_aligned
        excess_cumulative = (1 + excess_returns).cumprod() - 1
        axes[0, 1].plot(excess_cumulative.index, excess_cumulative, 
                       linewidth=2, color='green')
        axes[0, 1].axhline(y=0, color='black', linestyle='--', alpha=0.7)
        axes[0, 1].set_title('超额收益', fontsize=12, fontweight='bold')
        axes[0, 1].set_ylabel('超额收益率')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        # 收益散点图
        axes[1, 0].scatter(benchmark_aligned, strategy_aligned, alpha=0.6)
        
        # 拟合线性回归
        from scipy import stats
        slope, intercept, r_value, p_value, std_err = stats.linregress(benchmark_aligned, strategy_aligned)
        line_x = np.array([benchmark_aligned.min(), benchmark_aligned.max()])
        line_y = slope * line_x + intercept
        axes[1, 0].plot(line_x, line_y, 'r-', alpha=0.8, 
                       label=f'Beta: {slope:.2f}, R²: {r_value**2:.3f}')
        
        axes[1, 0].set_title('收益散点图', fontsize=12, fontweight='bold')
        axes[1, 0].set_xlabel('基准日收益率')
        axes[1, 0].set_ylabel('策略日收益率')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 统计对比
        stats_comparison = pd.DataFrame({
            '策略': [
                strategy_aligned.mean() * 252,  # 年化收益
                strategy_aligned.std() * np.sqrt(252),  # 年化波动率
                (strategy_aligned.mean() / strategy_aligned.std()) * np.sqrt(252),  # 夏普比率
                strategy_cumulative.iloc[-1]  # 总收益
            ],
            '基准': [
                benchmark_aligned.mean() * 252,
                benchmark_aligned.std() * np.sqrt(252),
                (benchmark_aligned.mean() / benchmark_aligned.std()) * np.sqrt(252),
                benchmark_cumulative.iloc[-1]
            ]
        }, index=['年化收益率', '年化波动率', '夏普比率', '总收益率'])
        
        # 绘制对比柱状图
        stats_comparison.plot(kind='bar', ax=axes[1, 1])
        axes[1, 1].set_title('关键指标对比', fontsize=12, fontweight='bold')
        axes[1, 1].tick_params(axis='x', rotation=45)
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        # 打印详细统计
        print("\n" + "="*50)
        print("与基准对比统计")
        print("="*50)
        print(f"Beta: {slope:.3f}")
        print(f"Alpha (年化): {(intercept * 252):.2%}")
        print(f"相关性: {r_value:.3f}")
        print(f"信息比率: {excess_returns.mean() / excess_returns.std() * np.sqrt(252):.3f}")
        print(f"跟踪误差: {excess_returns.std() * np.sqrt(252):.2%}")
    
    def plot_performance_dashboard(self, figsize=(15, 12)):
        """
        绘制综合性能仪表板
        
        Args:
            figsize: 图表尺寸
        """
        fig = plt.figure(figsize=figsize)
        
        # 1. 权益曲线和基准比较
        ax1 = plt.subplot(2, 3, 1)
        if not self.equity_curve.empty:
            # 投资组合权益曲线
            portfolio_cumulative = (self.equity_curve['equity'] / self.result.initial_capital) - 1
            ax1.plot(portfolio_cumulative.index, portfolio_cumulative, 
                    linewidth=2, color='blue', label='策略收益')
            
            # 添加一些关键水平线
            ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax1.axhline(y=self.result.total_return, color='green', linestyle='--', 
                       label=f'总收益: {self.result.total_return:.2%}')
            
            ax1.set_title('策略累计收益', fontsize=14, fontweight='bold')
            ax1.set_ylabel('累计收益率', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # 2. 最大回撤分析
        ax2 = plt.subplot(2, 3, 2)
        if not self.equity_curve.empty:
            peak = self.equity_curve['equity'].expanding(min_periods=1).max()
            drawdown = (self.equity_curve['equity'] - peak) / peak
            running_max_dd = drawdown.expanding(min_periods=1).min()
            
            ax2.plot(drawdown.index, drawdown, linewidth=2, color='red', label='回撤')
            ax2.plot(running_max_dd.index, running_max_dd, linewidth=2, color='darkred', 
                    linestyle='--', label='最大回撤')
            ax2.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red')
            
            ax2.set_title('回撤分析', fontsize=14, fontweight='bold')
            ax2.set_ylabel('回撤比例', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # 3. 收益风险散点图
        ax3 = plt.subplot(2, 3, 3)
        if len(self.daily_returns) > 1:
            annual_return_pct = self.result.annual_return * 100
            annual_volatility = self.daily_returns.std() * np.sqrt(252) * 100
            
            scatter = ax3.scatter(annual_volatility, annual_return_pct, 
                                s=100, c=self.result.sharpe_ratio, cmap='viridis',
                                edgecolors='black', linewidth=1)
            
            ax3.set_xlabel('年化波动率 (%)', fontsize=12)
            ax3.set_ylabel('年化收益率 (%)', fontsize=12)
            ax3.set_title('收益-风险散点图', fontsize=14, fontweight='bold')
            plt.colorbar(scatter, ax=ax3, label='夏普比率')
            
            # 添加数据点标注
            ax3.annotate(f'策略\nSR: {self.result.sharpe_ratio:.2f}', 
                        (annual_volatility, annual_return_pct),
                        xytext=(10, 0), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 4. 交易盈亏分布
        ax4 = plt.subplot(2, 3, 4)
        # 简化的盈亏分布（示例数据）
        if self.result.total_trades > 0:
            profits = [self.result.avg_winning_trade] * self.result.profitable_trades
            losses = [self.result.avg_losing_trade] * self.result.losing_trades
            all_trades = profits + losses
            
            if all_trades:
                ax4.hist(all_trades, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
                ax4.axvline(np.mean(all_trades), color='red', linestyle='--', 
                           label=f'平均收益: ${np.mean(all_trades):.2f}')
                ax4.set_xlabel('每笔交易收益 ($)', fontsize=12)
                ax4.set_ylabel('频次', fontsize=12)
                ax4.set_title('交易收益分布', fontsize=14, fontweight='bold')
                ax4.legend()
                ax4.grid(True, alpha=0.3)
        
        # 5. 关键指标雷达图
        ax5 = plt.subplot(2, 3, 5, projection='polar')
        if self.result.total_trades > 0:
            # 标准化指标（0-1之间）
            metrics = ['年化收益', '夏普比率', '胜率', '盈利因子', '回撤控制']
            values = [
                min(1, max(0, self.result.annual_return / 0.5)),  # 假设50%为高收益
                min(1, max(0, self.result.sharpe_ratio / 3)),     # 假设3为高夏普比率
                self.result.win_rate,
                min(1, max(0, self.result.profit_factor / 5)),    # 假设5为高盈利因子
                1 - min(1, max(0, abs(self.result.max_drawdown) / 0.3))  # 假设30%回撤容忍度
            ]
            
            # 闭合图形
            values += values[:1]
            metrics += metrics[:1]
            
            # 计算角度
            angles = [n / float(len(metrics) - 1) * 2 * np.pi for n in range(len(metrics))]
            
            # 绘制雷达图
            ax5.plot(angles, values, linewidth=2, linestyle='solid', label='策略表现')
            ax5.fill(angles, values, alpha=0.4)
            
            # 添加标签
            ax5.set_xticks(angles[:-1])
            ax5.set_xticklabels(metrics[:-1], fontsize=10)
            ax5.set_title('策略综合表现雷达图', fontsize=14, fontweight='bold', pad=20)
        
        # 6. 滚动夏普比率
        ax6 = plt.subplot(2, 3, 6)
        if len(self.daily_returns) > 30:
            rolling_sharpe = self.daily_returns.rolling(window=30).apply(
                lambda x: (x.mean() / x.std()) * np.sqrt(252) if x.std() > 0 else 0
            )
            
            ax6.plot(rolling_sharpe.index, rolling_sharpe, linewidth=2, color='purple')
            ax6.axhline(y=self.result.sharpe_ratio, color='red', linestyle='--', 
                       label=f'整体夏普比率: {self.result.sharpe_ratio:.2f}')
            
            ax6.set_title('滚动夏普比率 (30天)', fontsize=14, fontweight='bold')
            ax6.set_ylabel('夏普比率', fontsize=12)
            ax6.legend()
            ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

    def generate_full_report(self, save_plots=True, plots_dir='plots'):
        """
        生成完整的分析报告
        
        Args:
            save_plots: 是否保存图表
            plots_dir: 图表保存目录
        """
        import os
        
        if save_plots:
            os.makedirs(plots_dir, exist_ok=True)
            plt.ioff()  # 关闭交互模式
        
        # 打印性能摘要
        self.print_performance_summary()
        
        # 生成所有图表
        print("\n正在生成权益曲线图...")
        self.plot_equity_curve()
        if save_plots:
            plt.savefig(f'{plots_dir}/equity_curve.png', dpi=300, bbox_inches='tight')
        
        print("正在生成收益分布图...")
        self.plot_return_distribution()
        if save_plots:
            plt.savefig(f'{plots_dir}/returns_distribution.png', dpi=300, bbox_inches='tight')
        
        print("正在生成交易分析图...")
        self.plot_trade_analysis()
        if save_plots:
            plt.savefig(f'{plots_dir}/trade_analysis.png', dpi=300, bbox_inches='tight')
        
        print("正在生成综合性能仪表板...")
        self.plot_performance_dashboard()
        if save_plots:
            plt.savefig(f'{plots_dir}/performance_dashboard.png', dpi=300, bbox_inches='tight')
        
        if save_plots:
            plt.ion()  # 重新开启交互模式
            print(f"\n所有图表已保存到 {plots_dir}/ 目录")
        
        print("\n分析报告生成完成！")

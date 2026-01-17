"""
回测引擎模块
执行策略回测并记录交易详情
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import os

from config import UltimateConfig
from ultimate_strategy import UltimateStrategy, TradingSignal, SignalType


@dataclass
class BacktestResult:
    """回测结果数据类"""
    # 基础信息
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # 性能指标
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    
    # 交易统计
    total_trades: int
    profitable_trades: int
    losing_trades: int
    avg_trade_return: float
    avg_winning_trade: float
    avg_losing_trade: float
    max_winning_trade: float
    max_losing_trade: float
    avg_holding_period: float
    max_holding_period: float
    
    # 详细数据
    equity_curve: pd.DataFrame
    trades_details: pd.DataFrame
    daily_returns: pd.Series


class BacktestEngine:
    """回测引擎类"""
    
    def __init__(self, config: UltimateConfig):
        self.config = config
        self.strategy = UltimateStrategy(config)
        
        # 回测状态
        self.initial_capital = config.INITIAL_CAPITAL
        self.current_capital = config.INITIAL_CAPITAL
        self.available_cash = config.INITIAL_CAPITAL
        self.current_position = 0
        self.position_value = 0
        self.entry_price = 0
        self.entry_date = None
        
        # 记录数据
        self.equity_history = []
        self.trades_history = []
        self.daily_pnl = []
        
        # 交易日志
        self.trade_log_path = config.TRADES_LOG_PATH
        self._init_trade_log()
    
    def _init_trade_log(self):
        """初始化交易日志文件"""
        os.makedirs(os.path.dirname(self.trade_log_path), exist_ok=True)
        with open(self.trade_log_path, "w", encoding="utf-8") as f:
            f.write("timestamp\taction\tprice\tquantity\tvalue\tcash\tposition\treason\n")
    
    def _log_trade(self, trade_record: Dict):
        """记录交易到日志文件"""
        try:
            with open(self.trade_log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"{trade_record.get('timestamp')}\t"
                    f"{trade_record.get('action')}\t"
                    f"{trade_record.get('price', 0):.2f}\t"
                    f"{trade_record.get('quantity', 0)}\t"
                    f"{trade_record.get('value', 0):.2f}\t"
                    f"{self.available_cash:.2f}\t"
                    f"{self.current_position}\t"
                    f"{trade_record.get('reason', '')}\n"
                )
        except Exception as e:
            print(f"⚠️  记录交易日志失败: {str(e)}")
    
    def execute_buy(self, signal: TradingSignal):
        """执行买入操作"""
        price = signal.price
        
        # 计算仓位大小
        quantity = self.strategy.calculate_position_size(signal, self.available_cash)
        
        # 计算交易成本
        cost = quantity * price * (1 + self.config.COMMISSION_RATE + self.config.SLIPPAGE)
        
        if cost <= self.available_cash:
            # 更新持仓
            old_position = self.current_position
            self.current_position += quantity
            
            # 计算平均入场价
            if old_position > 0:
                self.entry_price = (self.entry_price * old_position + price * quantity) / self.current_position
            else:
                self.entry_price = price
                self.entry_date = signal.timestamp
            
            # 更新资金
            self.available_cash -= cost
            self.position_value = self.current_position * price
            
            # 记录交易
            trade_record = {
                'timestamp': signal.timestamp,
                'action': 'BUY',
                'price': price,
                'quantity': quantity,
                'value': cost,
                'reason': ', '.join(signal.reasons[:3])  # 只记录前3个原因
            }
            self.trades_history.append(trade_record)
            self._log_trade(trade_record)
            
            # 更新策略状态
            self.strategy.current_position = self.current_position
            self.strategy.entry_price = self.entry_price
            self.strategy.entry_date = self.entry_date
    
    def execute_sell(self, signal: TradingSignal, reason: str = "信号触发"):
        """执行卖出操作"""
        if self.current_position == 0:
            return
        
        price = signal.price
        quantity = self.current_position
        
        # 计算交易收入
        revenue = quantity * price * (1 - self.config.COMMISSION_RATE - self.config.SLIPPAGE)
        
        # 计算盈亏
        pnl = (price - self.entry_price) * quantity
        pnl_pct = (price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0
        
        # 更新持仓
        self.current_position = 0
        self.position_value = 0
        
        # 更新资金
        self.available_cash += revenue
        
        # 记录交易
        trade_record = {
            'timestamp': signal.timestamp,
            'action': 'SELL',
            'price': price,
            'quantity': quantity,
            'value': revenue,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'holding_days': (signal.timestamp - self.entry_date).days if self.entry_date else 0,
            'reason': reason
        }
        self.trades_history.append(trade_record)
        self._log_trade(trade_record)
        
        # 更新策略状态
        self.strategy.current_position = 0
        self.strategy.entry_price = 0
        self.strategy.entry_date = None
        
        # 更新连续亏损计数
        if pnl < 0:
            self.strategy.consecutive_losses += 1
        else:
            self.strategy.consecutive_losses = 0
        
        self.strategy.last_trade_date = signal.timestamp
    
    def check_stop_loss_take_profit(self, current_price: float, signal: TradingSignal) -> Optional[str]:
        """检查止损止盈条件"""
        if self.current_position == 0 or self.entry_price == 0:
            return None
        
        # 计算当前盈亏
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # 固定止损
        if pnl_pct <= -self.config.STOP_LOSS_PCT:
            return f"固定止损触发({pnl_pct:.2%})"
        
        # 固定止盈
        if pnl_pct >= self.config.TAKE_PROFIT_PCT:
            return f"固定止盈触发({pnl_pct:.2%})"
        
        # ATR动态止损止盈
        if signal.stop_loss and current_price <= signal.stop_loss:
            return f"ATR止损触发(价格{current_price:.2f} <= 止损{signal.stop_loss:.2f})"
        
        if signal.take_profit and current_price >= signal.take_profit:
            return f"ATR止盈触发(价格{current_price:.2f} >= 止盈{signal.take_profit:.2f})"
        
        # 移动止损
        if self.config.TRAILING_STOP_ENABLED and pnl_pct >= self.config.TRAILING_STOP_ACTIVATION:
            trailing_stop_price = self.entry_price * (1 + pnl_pct - self.config.TRAILING_STOP_DISTANCE)
            if current_price <= trailing_stop_price:
                return f"移动止损触发({pnl_pct:.2%})"
        
        # 时间止损
        if self.strategy.check_time_stop(signal.timestamp):
            return f"时间止损触发(持仓{(signal.timestamp - self.entry_date).days}天)"
        
        return None
    
    def run(self, data: pd.DataFrame) -> BacktestResult:
        """
        运行回测
        
        Args:
            data: 包含所有指标的完整数据
            
        Returns:
            回测结果
        """
        print("\n" + "=" * 60)
        print("🚀 步骤 3/4: 执行回测")
        print("=" * 60)
        
        # 更新SMC结构
        self.strategy.update_smc_structure(data)
        
        # 遍历数据执行回测
        for i in range(len(data)):
            current_date = data.index[i]
            current_price = data.iloc[i]['close']
            
            # 检查冷却期
            if self.strategy.check_cooldown(current_date):
                # 在冷却期内，跳过交易
                pass
            else:
                # 生成交易信号
                signal = self.strategy.generate_composite_signal(data, i)
                
                # 检查止损止盈
                if self.current_position > 0:
                    stop_reason = self.check_stop_loss_take_profit(current_price, signal)
                    if stop_reason:
                        self.execute_sell(signal, stop_reason)
                
                # 检查动态移仓
                should_roll, defense_ratio, attack_ratio = self.strategy.should_roll_position(current_price)
                if should_roll and self.current_position > 0:
                    # 锁定部分利润
                    sell_quantity = int(self.current_position * defense_ratio)
                    if sell_quantity > 0:
                        # 部分平仓
                        partial_signal = TradingSignal(
                            timestamp=current_date,
                            signal_type=SignalType.SELL,
                            confidence=1.0,
                            price=current_price,
                            reasons=[f"动态移仓-锁定{defense_ratio:.0%}利润"],
                            indicators=signal.indicators
                        )
                        # 临时修改持仓数量执行部分卖出
                        original_position = self.current_position
                        self.current_position = sell_quantity
                        self.execute_sell(partial_signal, f"动态移仓-锁定{defense_ratio:.0%}利润")
                        self.current_position = original_position - sell_quantity
                
                # 执行交易信号
                if signal.signal_type == SignalType.BUY and self.current_position == 0:
                    self.execute_buy(signal)
                elif signal.signal_type == SignalType.SELL and self.current_position > 0:
                    self.execute_sell(signal, "卖出信号触发")
            
            # 更新权益
            total_equity = self.available_cash + self.current_position * current_price
            self.current_capital = total_equity
            
            self.equity_history.append({
                'date': current_date,
                'equity': total_equity,
                'cash': self.available_cash,
                'position_value': self.current_position * current_price,
                'position': self.current_position
            })
        
        # 计算回测结果
        result = self._calculate_results(data)
        
        print(f"\n✅ 回测完成，共执行 {result.total_trades} 笔交易")
        
        return result
    
    def _calculate_results(self, data: pd.DataFrame) -> BacktestResult:
        """计算回测结果指标"""
        # 转换为DataFrame
        equity_df = pd.DataFrame(self.equity_history)
        equity_df.set_index('date', inplace=True)
        
        trades_df = pd.DataFrame(self.trades_history)
        
        # 计算日收益率
        daily_returns = equity_df['equity'].pct_change().dropna()
        
        # 基础指标
        final_capital = equity_df['equity'].iloc[-1]
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        # 年化收益率
        days = (equity_df.index[-1] - equity_df.index[0]).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 夏普比率
        if len(daily_returns) > 1:
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        peak = equity_df['equity'].expanding(min_periods=1).max()
        drawdown = (equity_df['equity'] - peak) / peak
        max_drawdown = drawdown.min()
        
        # 交易统计
        sell_trades = trades_df[trades_df['action'] == 'SELL']
        total_trades = len(sell_trades)
        
        if total_trades > 0:
            profitable_trades = len(sell_trades[sell_trades['pnl'] > 0])
            losing_trades = len(sell_trades[sell_trades['pnl'] < 0])
            win_rate = profitable_trades / total_trades
            
            winning_pnl = sell_trades[sell_trades['pnl'] > 0]['pnl'].sum()
            losing_pnl = abs(sell_trades[sell_trades['pnl'] < 0]['pnl'].sum())
            profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
            
            avg_trade_return = sell_trades['pnl_pct'].mean()
            avg_winning_trade = sell_trades[sell_trades['pnl'] > 0]['pnl'].mean() if profitable_trades > 0 else 0
            avg_losing_trade = sell_trades[sell_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
            max_winning_trade = sell_trades['pnl'].max()
            max_losing_trade = sell_trades['pnl'].min()
            
            avg_holding_period = sell_trades['holding_days'].mean()
            max_holding_period = sell_trades['holding_days'].max()
        else:
            profitable_trades = 0
            losing_trades = 0
            win_rate = 0
            profit_factor = 0
            avg_trade_return = 0
            avg_winning_trade = 0
            avg_losing_trade = 0
            max_winning_trade = 0
            max_losing_trade = 0
            avg_holding_period = 0
            max_holding_period = 0
        
        return BacktestResult(
            start_date=equity_df.index[0],
            end_date=equity_df.index[-1],
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            losing_trades=losing_trades,
            avg_trade_return=avg_trade_return,
            avg_winning_trade=avg_winning_trade,
            avg_losing_trade=avg_losing_trade,
            max_winning_trade=max_winning_trade,
            max_losing_trade=max_losing_trade,
            avg_holding_period=avg_holding_period,
            max_holding_period=max_holding_period,
            equity_curve=equity_df,
            trades_details=trades_df,
            daily_returns=daily_returns
        )

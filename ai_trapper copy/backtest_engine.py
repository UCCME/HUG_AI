"""
回测引擎
用于执行策略回测并计算各项性能指标
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from gold_strategy import GoldTradingStrategy, SignalType
from data_handler import DataHandler

@dataclass
class BacktestResult:
    """回测结果类"""
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
    
    # 持仓统计
    avg_holding_period: float
    max_holding_period: float
    
    # 详细数据
    equity_curve: pd.DataFrame
    trades_details: pd.DataFrame
    daily_returns: pd.Series

class BacktestEngine:
    """
    回测引擎类
    执行策略回测并计算性能指标
    """
    
    def __init__(self, config):
        self.config = config
        self.initial_capital = config.INITIAL_CAPITAL
        self.commission_rate = config.COMMISSION_RATE
        self.slippage = config.SLIPPAGE
        self.position_size = config.POSITION_SIZE
        
        # 回测状态
        self.current_capital = self.initial_capital
        self.available_cash = self.initial_capital
        self.current_position = 0  # 当前持仓数量（股数/合约数）
        self.position_value = 0    # 持仓市值
        self.entry_price = 0       # 入场价格
        self.entry_time = None     # 入场时间
        
        # 记录数据
        self.equity_history = []
        self.trades_history = []
        self.position_history = []
        self.signal_history = []
        
    def calculate_position_size(self, price: float, signal_confidence: float) -> int:
        """
        计算开仓数量
        
        Args:
            price: 当前价格
            signal_confidence: 信号置信度
            
        Returns:
            开仓数量
        """
        # 根据信号置信度调整仓位大小
        adjusted_position_size = self.position_size * signal_confidence
        
        # 可用资金计算持仓数量
        available_for_position = self.available_cash * adjusted_position_size
        
        # 考虑手续费的实际可买数量
        position_count = int(available_for_position / (price * (1 + self.commission_rate + self.slippage)))
        
        return max(1, position_count)  # 至少1手
    
    def calculate_commission(self, trade_value: float) -> float:
        """
        计算交易手续费
        
        Args:
            trade_value: 交易金额
            
        Returns:
            手续费
        """
        return trade_value * self.commission_rate
    
    def calculate_slippage_cost(self, trade_value: float) -> float:
        """
        计算滑点成本
        
        Args:
            trade_value: 交易金额
            
        Returns:
            滑点成本
        """
        return trade_value * self.slippage
    
    def execute_trade(self, signal_type: SignalType, price: float, timestamp: datetime, 
                     confidence: float, reason: str) -> Dict:
        """
        执行交易
        
        Args:
            signal_type: 信号类型
            price: 交易价格
            timestamp: 交易时间
            confidence: 信号置信度
            reason: 交易原因
            
        Returns:
            交易记录
        """
        trade_record = {
            'timestamp': timestamp,
            'signal_type': signal_type.name,
            'price': price,
            'confidence': confidence,
            'reason': reason,
            'action': 'hold',
            'quantity': 0,
            'trade_value': 0,
            'commission': 0,
            'slippage_cost': 0,
            'pnl': 0,
            'capital_before': self.current_capital,
            'capital_after': self.current_capital,
            'position_before': self.current_position,
            'position_after': self.current_position
        }
        
        if signal_type == SignalType.BUY and self.current_position <= 0:
            # 买入信号处理
            if self.current_position < 0:
                # 先平空仓
                close_value = abs(self.current_position) * price
                close_commission = self.calculate_commission(close_value)
                close_slippage = self.calculate_slippage_cost(close_value)
                
                # 计算平仓盈亏
                pnl = (self.entry_price - price) * abs(self.current_position)
                self.available_cash += close_value + pnl - close_commission - close_slippage
                
                # 记录平仓交易
                self.trades_history.append({
                    'entry_time': self.entry_time,
                    'exit_time': timestamp,
                    'direction': 'short',
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'quantity': abs(self.current_position),
                    'pnl': pnl,
                    'return_pct': pnl / (self.entry_price * abs(self.current_position)),
                    'holding_days': (timestamp - self.entry_time).days,
                    'commission': close_commission,
                    'slippage_cost': close_slippage
                })
                
                self.current_position = 0
            
            # 开多仓
            position_count = self.calculate_position_size(price, confidence)
            if position_count > 0 and self.available_cash > position_count * price:
                trade_value = position_count * price
                commission = self.calculate_commission(trade_value)
                slippage_cost = self.calculate_slippage_cost(trade_value)
                total_cost = trade_value + commission + slippage_cost
                
                if self.available_cash >= total_cost:
                    self.current_position = position_count
                    self.available_cash -= total_cost
                    self.entry_price = price
                    self.entry_time = timestamp
                    
                    trade_record.update({
                        'action': 'buy',
                        'quantity': position_count,
                        'trade_value': trade_value,
                        'commission': commission,
                        'slippage_cost': slippage_cost,
                        'position_after': self.current_position
                    })
        
        elif signal_type == SignalType.SELL and self.current_position >= 0:
            # 卖出信号处理
            if self.current_position > 0:
                # 先平多仓
                close_value = self.current_position * price
                close_commission = self.calculate_commission(close_value)
                close_slippage = self.calculate_slippage_cost(close_value)
                
                # 计算平仓盈亏
                pnl = (price - self.entry_price) * self.current_position
                self.available_cash += close_value + pnl - close_commission - close_slippage
                
                # 记录平仓交易
                self.trades_history.append({
                    'entry_time': self.entry_time,
                    'exit_time': timestamp,
                    'direction': 'long',
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'quantity': self.current_position,
                    'pnl': pnl,
                    'return_pct': pnl / (self.entry_price * self.current_position),
                    'holding_days': (timestamp - self.entry_time).days,
                    'commission': close_commission,
                    'slippage_cost': close_slippage
                })
                
                self.current_position = 0
            
            # 开空仓
            position_count = self.calculate_position_size(price, confidence)
            if position_count > 0:
                # 空仓保证金计算（简化处理，假设保证金率为20%）
                margin_required = position_count * price * 0.2
                commission = self.calculate_commission(position_count * price)
                slippage_cost = self.calculate_slippage_cost(position_count * price)
                total_cost = margin_required + commission + slippage_cost
                
                if self.available_cash >= total_cost:
                    self.current_position = -position_count
                    self.available_cash -= total_cost
                    self.entry_price = price
                    self.entry_time = timestamp
                    
                    trade_record.update({
                        'action': 'sell',
                        'quantity': position_count,
                        'trade_value': position_count * price,
                        'commission': commission,
                        'slippage_cost': slippage_cost,
                        'position_after': self.current_position
                    })
        
        # 更新总资本
        if self.current_position > 0:
            self.position_value = self.current_position * price
        elif self.current_position < 0:
            # 空仓的浮动盈亏
            self.position_value = (self.entry_price - price) * abs(self.current_position)
        else:
            self.position_value = 0
        
        self.current_capital = self.available_cash + self.position_value
        trade_record['capital_after'] = self.current_capital
        
        return trade_record
    
    def force_close_position(self, price: float, timestamp: datetime, reason: str = "强制平仓"):
        """
        强制平仓（回测结束时使用）
        
        Args:
            price: 平仓价格
            timestamp: 平仓时间
            reason: 平仓原因
        """
        if self.current_position == 0:
            return
        
        if self.current_position > 0:
            # 平多仓
            close_value = self.current_position * price
            pnl = (price - self.entry_price) * self.current_position
            direction = 'long'
        else:
            # 平空仓
            close_value = abs(self.current_position) * price
            pnl = (self.entry_price - price) * abs(self.current_position)
            direction = 'short'
        
        close_commission = self.calculate_commission(close_value)
        close_slippage = self.calculate_slippage_cost(close_value)
        
        # 记录最终平仓交易
        self.trades_history.append({
            'entry_time': self.entry_time,
            'exit_time': timestamp,
            'direction': direction,
            'entry_price': self.entry_price,
            'exit_price': price,
            'quantity': abs(self.current_position),
            'pnl': pnl,
            'return_pct': pnl / (self.entry_price * abs(self.current_position)),
            'holding_days': (timestamp - self.entry_time).days,
            'commission': close_commission,
            'slippage_cost': close_slippage,
            'exit_reason': reason
        })
        
        # 更新资金状态
        net_proceeds = close_value + pnl - close_commission - close_slippage
        if self.current_position < 0:
            # 空仓返还保证金
            margin_return = abs(self.current_position) * self.entry_price * 0.2
            net_proceeds += margin_return
        
        self.available_cash += net_proceeds
        self.current_capital = self.available_cash
        self.current_position = 0
        self.position_value = 0
    
    def run_backtest(self, data: pd.DataFrame, strategy: GoldTradingStrategy) -> BacktestResult:
        """
        执行回测
        
        Args:
            data: 包含技术指标的数据
            strategy: 交易策略实例
            
        Returns:
            回测结果
        """
        print(f"开始回测，数据期间：{data.index[0]} 到 {data.index[-1]}")
        print(f"初始资金：${self.initial_capital:,.2f}")
        
        # 重置回测状态
        self.current_capital = self.initial_capital
        self.available_cash = self.initial_capital
        self.current_position = 0
        self.position_value = 0
        self.equity_history = []
        self.trades_history = []
        self.signal_history = []
        
        # 逐日执行策略
        for i in range(len(data)):
            timestamp = data.index[i]
            current_price = data.iloc[i]['Close']
            
            # 检查是否需要强制平仓（风控）
            should_close, close_reason = strategy.should_close_position(data, i)
            
            if should_close and self.current_position != 0:
                # 执行强制平仓
                if self.current_position > 0:
                    close_signal = SignalType.SELL
                else:
                    close_signal = SignalType.BUY
                
                trade_record = self.execute_trade(
                    close_signal, current_price, timestamp, 1.0, close_reason
                )
                self.signal_history.append(trade_record)
            else:
                # 生成交易信号
                signal = strategy.generate_composite_signal(data, i)
                self.signal_history.append({
                    'timestamp': timestamp,
                    'signal_type': signal.signal_type.name,
                    'price': signal.price,
                    'confidence': signal.confidence,
                    'reason': signal.reason
                })
                
                # 执行交易
                if signal.signal_type != SignalType.HOLD:
                    trade_record = self.execute_trade(
                        signal.signal_type, current_price, timestamp,
                        signal.confidence, signal.reason
                    )
            
            # 更新持仓市值
            if self.current_position > 0:
                self.position_value = self.current_position * current_price
            elif self.current_position < 0:
                self.position_value = (self.entry_price - current_price) * abs(self.current_position)
            else:
                self.position_value = 0
            
            self.current_capital = self.available_cash + self.position_value
            
            # 记录每日权益
            self.equity_history.append({
                'date': timestamp,
                'equity': self.current_capital,
                'cash': self.available_cash,
                'position_value': self.position_value,
                'position': self.current_position,
                'price': current_price
            })
        
        # 回测结束，强制平仓
        if self.current_position != 0:
            final_price = data.iloc[-1]['Close']
            final_timestamp = data.index[-1]
            self.force_close_position(final_price, final_timestamp, "回测结束强制平仓")
        
        print(f"回测完成，最终资金：${self.current_capital:,.2f}")
        print(f"总收益率：{((self.current_capital - self.initial_capital) / self.initial_capital * 100):.2f}%")
        
        # 计算性能指标
        return self.calculate_performance_metrics(data.index[0], data.index[-1])
    
    def calculate_performance_metrics(self, start_date: datetime, end_date: datetime) -> BacktestResult:
        """
        计算性能指标
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
            
        Returns:
            回测结果
        """
        # 基础指标
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        days = (end_date - start_date).days
        annual_return = (1 + total_return) ** (365.25 / days) - 1 if days > 0 else 0
        
        # 创建权益曲线DataFrame
        equity_df = pd.DataFrame(self.equity_history)
        equity_df.set_index('date', inplace=True)
        
        # 计算日收益率
        equity_df['daily_return'] = equity_df['equity'].pct_change()
        daily_returns = equity_df['daily_return'].dropna()
        
        # 夏普比率
        if len(daily_returns) > 1 and daily_returns.std() != 0:
            risk_free_rate = 0.02 / 365.25  # 假设年化无风险利率2%
            excess_returns = daily_returns - risk_free_rate
            sharpe_ratio = excess_returns.mean() / daily_returns.std() * np.sqrt(365.25)
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        running_max = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 交易统计
        if self.trades_history:
            trades_df = pd.DataFrame(self.trades_history)
            
            total_trades = len(trades_df)
            profitable_trades = len(trades_df[trades_df['pnl'] > 0])
            losing_trades = len(trades_df[trades_df['pnl'] < 0])
            win_rate = profitable_trades / total_trades if total_trades > 0 else 0
            
            # 盈亏比
            winning_trades = trades_df[trades_df['pnl'] > 0]['pnl']
            losing_trades_pnl = trades_df[trades_df['pnl'] < 0]['pnl']
            
            avg_winning_trade = winning_trades.mean() if len(winning_trades) > 0 else 0
            avg_losing_trade = losing_trades_pnl.mean() if len(losing_trades_pnl) > 0 else 0
            max_winning_trade = winning_trades.max() if len(winning_trades) > 0 else 0
            max_losing_trade = losing_trades_pnl.min() if len(losing_trades_pnl) > 0 else 0
            
            # 盈利因子
            gross_profit = winning_trades.sum() if len(winning_trades) > 0 else 0
            gross_loss = abs(losing_trades_pnl.sum()) if len(losing_trades_pnl) > 0 else 0
            profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
            
            avg_trade_return = trades_df['return_pct'].mean()
            avg_holding_period = trades_df['holding_days'].mean()
            max_holding_period = trades_df['holding_days'].max()
            
        else:
            total_trades = 0
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
            trades_df = pd.DataFrame()
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=self.current_capital,
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

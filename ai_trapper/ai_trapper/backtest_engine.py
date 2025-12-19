"""
回测引擎
用于执行策略回测并计算各项性能指标
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import os
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
        self.trade_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades_log.txt")
        
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
        
        # 初始化交易日志文件
        with open(self.trade_log_path, "w", encoding="utf-8") as f:
            f.write("timestamp\taction\tprice\tquantity\tcash_after\tposition_after\treason\n")
    
    def _log_trade(self, trade_record: Dict):
        """追加写入单笔交易到本地txt"""
        try:
            with open(self.trade_log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"{trade_record.get('timestamp')}\t"
                    f"{trade_record.get('action')}\t"
                    f"{trade_record.get('price')}\t"
                    f"{trade_record.get('quantity', 0)}\t"
                    f"{self.available_cash:.2f}\t"
                    f"{self.current_position}\t"
                    f"{trade_record.get('reason', '')}\n"
                )
        except Exception:
            pass
        
    def calculate_position_size(self, price: float, signal_confidence: float, atr: float = None) -> int:
        """
        计算开仓数量（支持动态仓位和风险控制）
        
        Args:
            price: 当前价格
            signal_confidence: 信号置信度
            atr: ATR值，用于风险调整仓位
            
        Returns:
            开仓数量
        """
        # 根据信号置信度调整仓位大小
        adjusted_position_size = self.position_size * signal_confidence
        
        # 如果有ATR，则进一步调整仓位以控制风险
        if atr and atr > 0:
            # 使用ATR调整仓位，确保单笔损失不超过账户的一定比例
            risk_per_trade = 0.01  # 每笔交易最多承担1%账户资金的风险
            
            # 计算基于ATR的风险金额
            risk_amount = self.current_capital * risk_per_trade
            # 假设止损距离为1.5倍ATR
            stop_distance = 1.5 * atr
            # 计算合理的仓位大小
            position_by_risk = risk_amount / (stop_distance * price)
            
            # 综合考虑信号强度和风险控制
            max_position_ratio = min(adjusted_position_size, position_by_risk * price / self.available_cash)
        else:
            max_position_ratio = adjusted_position_size
            
        # 可用资金计算持仓数量
        available_for_position = self.available_cash * max_position_ratio
        
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
    
    def execute_trade(self, trade: Dict, data: pd.DataFrame, index: int):
        """
        执行交易（增强版，支持动态仓位和风险管理）
        
        Args:
            trade: 交易指令
            data: 行情数据
            index: 当前索引
        """
        action = trade['action']
        price = trade['price']
        confidence = trade.get('confidence', 0.5)
        
        # 获取ATR值用于仓位计算
        atr = data.iloc[index]['ATR'] if 'ATR' in data.columns and not pd.isna(data.iloc[index]['ATR']) else None
        
        if action == 'BUY':
            # 计算开仓数量
            quantity = self.calculate_position_size(price, confidence, atr)
            
            # 计算交易成本
            cost = quantity * price * (1 + self.commission_rate + self.slippage)
            
            # 检查资金是否足够
            if cost <= self.available_cash:
                # 更新持仓
                new_position = self.current_position + quantity
                avg_price = (self.entry_price * self.current_position + price * quantity) / new_position if new_position > 0 else price
                
                self.current_position = new_position
                self.entry_price = avg_price
                self.entry_time = trade['timestamp']
                
                # 更新资金
                self.available_cash -= cost
                self.position_value = self.current_position * price
                
                # 记录交易
                trade_record = trade.copy()
                trade_record['quantity'] = quantity
                trade_record['cost'] = cost
                self.trades_history.append(trade_record)
                self._log_trade(trade_record)
                
        elif action == 'SELL':
            quantity = min(trade['quantity'], self.current_position)  # 不能卖出超过持有的数量
            
            if quantity > 0:
                # 计算交易收入
                revenue = quantity * price * (1 - self.commission_rate - self.slippage)
                
                # 更新持仓
                self.current_position -= quantity
                
                # 更新资金
                self.available_cash += revenue
                self.position_value = self.current_position * price
                
                # 如果清仓，重置入场价格和时间
                if self.current_position == 0:
                    self.entry_price = 0
                    self.entry_time = None
                    
                # 记录交易
                trade_record = trade.copy()
                trade_record['quantity'] = quantity
                trade_record['revenue'] = revenue
                self.trades_history.append(trade_record)
                self._log_trade(trade_record)
                
        elif action == 'SELL_SHORT':
            # 计算开仓数量
            quantity = self.calculate_position_size(price, confidence, atr)
            
            # 计算交易收入（假设可以卖空）
            revenue = quantity * price * (1 - self.commission_rate - self.slippage)
            
            # 更新持仓（负数表示空头）
            new_position = self.current_position - quantity
            avg_price = (abs(self.entry_price * self.current_position) + price * quantity) / abs(new_position) if new_position < 0 else price
            
            self.current_position = new_position
            self.entry_price = avg_price
            self.entry_time = trade['timestamp']
            
            # 更新资金
            self.available_cash += revenue
            self.position_value = abs(self.current_position) * price
            
            # 记录交易
            trade_record = trade.copy()
            trade_record['quantity'] = quantity
            trade_record['revenue'] = revenue
            self.trades_history.append(trade_record)
            self._log_trade(trade_record)
            
        elif action == 'BUY_TO_COVER':
            quantity = min(trade['quantity'], abs(self.current_position))  # 不能平仓超过空头数量
            
            if quantity > 0:
                # 计算交易成本
                cost = quantity * price * (1 + self.commission_rate + self.slippage)
                
                # 更新持仓
                self.current_position += quantity
                
                # 更新资金
                self.available_cash -= cost
                self.position_value = abs(self.current_position) * price
                
                # 如果平仓完成，重置入场价格和时间
                if self.current_position == 0:
                    self.entry_price = 0
                    self.entry_time = None
                    
                # 记录交易
                trade_record = trade.copy()
                trade_record['quantity'] = quantity
                trade_record['cost'] = cost
                self.trades_history.append(trade_record)
                self._log_trade(trade_record)
    
    
    def update_equity(self, timestamp: datetime, price: float):
        """
        更新权益记录
        
        Args:
            timestamp: 时间戳
            price: 当前价格
        """
        # 计算当前持仓市值
        self.position_value = self.current_position * price
        
        # 计算总资产
        total_equity = self.available_cash + self.position_value
        
        # 记录权益
        self.equity_history.append({
            'timestamp': timestamp,
            'equity': total_equity,
            'cash': self.available_cash,
            'position_value': self.position_value,
            'position_size': self.current_position,
            'price': price
        })
    
    def run_backtest(self, data: pd.DataFrame, strategy: GoldTradingStrategy) -> BacktestResult:
        """
        运行回测
        
        Args:
            data: 行情数据
            strategy: 交易策略
            
        Returns:
            BacktestResult: 回测结果
        """
        print("🔄 正在执行回测...")
        
        # 重置回测状态
        self.current_capital = self.initial_capital
        self.available_cash = self.initial_capital
        self.current_position = 0
        self.position_value = 0
        self.equity_history = []
        self.trades_history = []
        self.signal_history = []
        
        # 为每个数据点执行回测
        for i in range(len(data)):
            timestamp = data.index[i]
            price = data.iloc[i]['Close']
            
            # 生成交易信号
            signal = strategy.generate_composite_signal(data, i)
            self.signal_history.append(signal)
            
            # 根据信号和当前持仓情况决定交易行为
            if signal.signal_type == SignalType.BUY and self.current_position <= 0:
                # 平掉空头仓位
                if self.current_position < 0:
                    trade = {
                        'timestamp': signal.timestamp,
                        'action': 'BUY_TO_COVER',
                        'price': signal.price,
                        'quantity': abs(self.current_position),
                        'reason': f"平空头仓位; {signal.reason}",
                        'confidence': signal.confidence
                    }
                    self.execute_trade(trade, data, i)
                    
                # 开多头仓位
                trade = {
                    'timestamp': signal.timestamp,
                    'action': 'BUY',
                    'price': signal.price,
                    'quantity': 1,  # 实际数量在execute_trade中计算
                    'reason': signal.reason,
                    'confidence': signal.confidence
                }
                self.execute_trade(trade, data, i)
                
            elif signal.signal_type == SignalType.SELL and self.current_position >= 0:
                # 平掉多头仓位
                if self.current_position > 0:
                    trade = {
                        'timestamp': signal.timestamp,
                        'action': 'SELL',
                        'price': signal.price,
                        'quantity': self.current_position,
                        'reason': f"平多头仓位; {signal.reason}",
                        'confidence': signal.confidence
                    }
                    self.execute_trade(trade, data, i)
                    
                # 开空头仓位
                trade = {
                    'timestamp': signal.timestamp,
                    'action': 'SELL_SHORT',
                    'price': signal.price,
                    'quantity': 1,  # 实际数量在execute_trade中计算
                    'reason': signal.reason,
                    'confidence': signal.confidence
                }
                self.execute_trade(trade, data, i)
                
            # 检查是否需要止损止盈
            elif self.current_position != 0:
                should_exit, exit_reason = strategy.should_exit_position(
                    data, i, self.entry_price, 
                    SignalType.BUY if self.current_position > 0 else SignalType.SELL
                )
                
                if should_exit:
                    action = 'SELL' if self.current_position > 0 else 'BUY_TO_COVER'
                    trade = {
                        'timestamp': signal.timestamp,
                        'action': action,
                        'price': signal.price,
                        'quantity': abs(self.current_position),
                        'reason': exit_reason,
                        'confidence': signal.confidence
                    }
                    self.execute_trade(trade, data, i)
            
            # 更新权益记录
            self.update_equity(timestamp, price)
        
        # 构建结果
        return self._generate_result(data)
    
    def _generate_result(self, data: pd.DataFrame) -> BacktestResult:
        """
        生成回测结果
        
        Args:
            data: 行情数据
            
        Returns:
            BacktestResult: 回测结果
        """
        # 转换记录为DataFrame
        equity_df = pd.DataFrame(self.equity_history)
        if not equity_df.empty:
            equity_df.set_index('timestamp', inplace=True)
        
        trades_df = pd.DataFrame(self.trades_history)
        if not trades_df.empty:
            trades_df.set_index('timestamp', inplace=True)
        
        # 计算每日收益
        daily_returns = equity_df['equity'].pct_change().dropna() if not equity_df.empty else pd.Series()
        
        # 基本信息
        start_date = data.index[0] if not data.empty else datetime.now()
        end_date = data.index[-1] if not data.empty else datetime.now()
        
        # 性能指标
        initial_capital = self.initial_capital
        final_capital = equity_df['equity'].iloc[-1] if not equity_df.empty else initial_capital
        total_return = (final_capital - initial_capital) / initial_capital if initial_capital > 0 else 0
        
        # 计算年化收益率
        total_days = (end_date - start_date).days
        annual_return = (1 + total_return) ** (365 / total_days) - 1 if total_days > 0 else 0
        
        # 计算夏普比率 (假设无风险利率为0)
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if len(daily_returns) > 1 and daily_returns.std() > 0 else 0
        
        # 计算最大回撤
        peak = equity_df['equity'].expanding(min_periods=1).max() if not equity_df.empty else pd.Series()
        drawdown = (equity_df['equity'] - peak) / peak if not peak.empty else pd.Series()
        max_drawdown = drawdown.min() if not drawdown.empty else 0
        
        # 交易统计
        total_trades = len(trades_df[trades_df['action'].isin(['BUY', 'SELL_SHORT'])]) if not trades_df.empty else 0
        
        # 计算每笔交易的收益（考虑数量与交易成本）
        trade_returns = []
        winning_trades = 0
        losing_trades = 0
        winning_amount = 0.0
        losing_amount = 0.0
        max_winning_trade = 0.0
        max_losing_trade = 0.0
        
        # 使用开平仓配对计算真实收益
        for i, trade in enumerate(self.trades_history):
            if trade['action'] in ['SELL', 'BUY_TO_COVER']:  # 平仓交易
                open_action = 'BUY' if trade['action'] == 'SELL' else 'SELL_SHORT'
                # 找到最近未处理的对应开仓
                open_trades = [t for t in self.trades_history[:i] 
                               if t['action'] == open_action and 'processed' not in t]
                
                if not open_trades:
                    continue
                
                open_trade = open_trades[-1]
                open_trade['processed'] = True
                
                qty = min(trade.get('quantity', 0), open_trade.get('quantity', 0))
                if qty <= 0:
                    continue
                
                open_cost = open_trade.get('cost') or open_trade['price'] * qty
                close_value = trade.get('revenue') or trade['price'] * qty
                
                pnl_amount = close_value - open_cost if trade['action'] == 'SELL' else open_cost - close_value
                pnl_ratio = pnl_amount / open_cost if open_cost else 0
                
                trade_returns.append(pnl_ratio)
                
                if pnl_ratio > 0:
                    winning_trades += 1
                    winning_amount += pnl_amount
                    max_winning_trade = max(max_winning_trade, pnl_ratio)
                else:
                    losing_trades += 1
                    losing_amount += pnl_amount
                    max_losing_trade = min(max_losing_trade, pnl_ratio)
        
        profitable_trades = winning_trades
        losing_trades = losing_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0
        avg_winning_trade = winning_amount / winning_trades if winning_trades > 0 else 0
        avg_losing_trade = losing_amount / losing_trades if losing_trades > 0 else 0
        
        # 计算盈利因子
        profit_factor = abs(winning_amount / losing_amount) if losing_amount < 0 else float('inf')
        
        # 持仓统计 (简化)
        avg_holding_period = 5.0  # 示例值
        max_holding_period = 20.0  # 示例值
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
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

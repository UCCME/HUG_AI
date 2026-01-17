"""
风险控制模块
实现松松的风控策略：单笔止损<1%、半仓滚动、动态仓位管理、空仓等待
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime


class RiskManager:
    """风险管理器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化风险管理器
        
        Args:
            config: 风控配置参数
        """
        self.config = config or self._default_config()
        self.positions = {}  # 当前持仓
        self.trade_history = []  # 交易历史
        
    def _default_config(self) -> Dict:
        """默认风控配置"""
        return {
            'max_single_loss_pct': 0.01,       # 单笔最大亏损1%
            'max_position_ratio': 0.5,         # 最大仓位50%（半仓滚动）
            'max_single_position': 0.5,        # 单个股票最大仓位50%
            'min_position_score': 60,          # 最低持仓评分
            'max_daily_trades': 1,             # 每天最多交易1只股票
            'stop_loss_time_limit': 30,        # 止损时间限制（秒，可转债时代的纪律）
            'empty_position_days_limit': 5,    # 允许空仓天数
            'market_sentiment_threshold': 40    # 市场情绪阈值（低于此值考虑空仓）
        }
    
    def calculate_position_size(self, 
                               symbol: str,
                               current_price: float,
                               total_capital: float,
                               position_score: float,
                               market_sentiment: float) -> float:
        """
        计算建仓大小
        采用半仓滚动策略
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            total_capital: 总资金
            position_score: 持仓评分
            market_sentiment: 市场情绪
            
        Returns:
            建议持仓金额
        """
        # 市场情绪差时，不建仓
        if market_sentiment < self.config['market_sentiment_threshold']:
            return 0.0
        
        # 基础仓位：半仓
        base_position = total_capital * self.config['max_position_ratio']
        
        # 根据持仓评分调整
        score_ratio = position_score / 100.0
        adjusted_position = base_position * score_ratio
        
        # 单个股票仓位上限
        max_single = total_capital * self.config['max_single_position']
        
        return min(adjusted_position, max_single)
    
    def check_stop_loss(self, 
                       symbol: str,
                       entry_price: float,
                       current_price: float,
                       hold_seconds: int = 0) -> Tuple[bool, str]:
        """
        检查是否需要止损
        
        Args:
            symbol: 股票代码
            entry_price: 买入价格
            current_price: 当前价格
            hold_seconds: 持有秒数（用于可转债高频模式）
            
        Returns:
            (是否止损, 止损原因)
        """
        # 计算亏损比例
        loss_pct = (current_price - entry_price) / entry_price
        
        # 1. 单笔亏损超过1%，立即止损
        if loss_pct <= -self.config['max_single_loss_pct']:
            return True, f"亏损{abs(loss_pct)*100:.2f}%超过阈值"
        
        # 2. 可转债模式：持有超过30秒仍亏损，止损
        # （正股模式下此条件不适用）
        if hold_seconds > 0 and hold_seconds <= self.config['stop_loss_time_limit']:
            if loss_pct < 0:
                return True, f"持有{hold_seconds}秒仍亏损"
        
        return False, ""
    
    def should_take_position(self, 
                            symbol: str,
                            date: str,
                            market_sentiment: float) -> Tuple[bool, str]:
        """
        判断是否应该开仓
        
        Args:
            symbol: 股票代码
            date: 日期
            market_sentiment: 市场情绪分数
            
        Returns:
            (是否开仓, 原因)
        """
        # 1. 检查今日是否已交易
        today_trades = [t for t in self.trade_history 
                       if t['date'] == date and t['action'] == 'buy']
        
        if len(today_trades) >= self.config['max_daily_trades']:
            return False, f"今日已交易{len(today_trades)}次，达到上限"
        
        # 2. 检查市场情绪
        if market_sentiment < self.config['market_sentiment_threshold']:
            return False, f"市场情绪{market_sentiment}低于阈值，空仓等待"
        
        # 3. 检查当前仓位
        total_position_ratio = self._get_total_position_ratio()
        if total_position_ratio >= self.config['max_position_ratio']:
            return False, f"当前仓位{total_position_ratio*100:.1f}%已达上限"
        
        return True, "可以开仓"
    
    def should_close_position(self, 
                             symbol: str,
                             position_score: float,
                             hold_days: int) -> Tuple[bool, str]:
        """
        判断是否应该平仓
        
        Args:
            symbol: 股票代码
            position_score: 持仓评分
            hold_days: 持有天数
            
        Returns:
            (是否平仓, 原因)
        """
        # 1. 持仓评分过低
        if position_score < self.config['min_position_score']:
            return True, f"持仓评分{position_score}低于阈值"
        
        # 2. 持有时间过长（短线策略通常T+1或T+2）
        if hold_days > 2:
            return True, f"持有{hold_days}天，超过短线周期"
        
        return False, ""
    
    def adjust_position(self, 
                       symbol: str,
                       current_score: float,
                       market_sentiment: float) -> str:
        """
        动态调整仓位
        
        Args:
            symbol: 股票代码
            current_score: 当前评分
            market_sentiment: 市场情绪
            
        Returns:
            调整建议 ('hold', 'add', 'reduce', 'close')
        """
        if symbol not in self.positions:
            return 'hold'
        
        position = self.positions[symbol]
        
        # 市场情绪差，减仓
        if market_sentiment < self.config['market_sentiment_threshold']:
            return 'reduce'
        
        # 持仓评分很高，考虑加仓（但不超过最大仓位）
        if current_score >= 80:
            total_ratio = self._get_total_position_ratio()
            if total_ratio < self.config['max_position_ratio']:
                return 'add'
        
        # 持仓评分低，减仓或清仓
        if current_score < self.config['min_position_score']:
            return 'close'
        elif current_score < 70:
            return 'reduce'
        
        return 'hold'
    
    def record_trade(self, 
                    symbol: str,
                    action: str,
                    price: float,
                    quantity: int,
                    date: str,
                    reason: str = ""):
        """
        记录交易
        
        Args:
            symbol: 股票代码
            action: 动作 ('buy', 'sell')
            price: 价格
            quantity: 数量
            date: 日期
            reason: 原因
        """
        trade = {
            'symbol': symbol,
            'action': action,
            'price': price,
            'quantity': quantity,
            'date': date,
            'reason': reason,
            'timestamp': datetime.now()
        }
        
        self.trade_history.append(trade)
        
        # 更新持仓
        if action == 'buy':
            if symbol in self.positions:
                # 加仓
                old_pos = self.positions[symbol]
                total_cost = old_pos['cost'] * old_pos['quantity'] + price * quantity
                total_quantity = old_pos['quantity'] + quantity
                avg_cost = total_cost / total_quantity
                
                self.positions[symbol] = {
                    'quantity': total_quantity,
                    'cost': avg_cost,
                    'entry_date': old_pos['entry_date']
                }
            else:
                # 新建仓位
                self.positions[symbol] = {
                    'quantity': quantity,
                    'cost': price,
                    'entry_date': date
                }
        
        elif action == 'sell':
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos['quantity'] -= quantity
                
                # 清仓
                if pos['quantity'] <= 0:
                    del self.positions[symbol]
    
    def _get_total_position_ratio(self) -> float:
        """获取当前总仓位比例"""
        # 简化实现，实际需要根据持仓市值计算
        return len(self.positions) * 0.5 if self.positions else 0.0
    
    def get_statistics(self) -> Dict:
        """
        获取交易统计
        
        Returns:
            统计信息字典
        """
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'max_drawdown': 0.0
            }
        
        df = pd.DataFrame(self.trade_history)
        
        # 配对买卖计算盈亏
        profits = []
        for symbol in df['symbol'].unique():
            symbol_trades = df[df['symbol'] == symbol].sort_values('timestamp')
            
            buys = symbol_trades[symbol_trades['action'] == 'buy']
            sells = symbol_trades[symbol_trades['action'] == 'sell']
            
            for i in range(min(len(buys), len(sells))):
                buy_price = buys.iloc[i]['price']
                sell_price = sells.iloc[i]['price']
                profit_pct = (sell_price - buy_price) / buy_price
                profits.append(profit_pct)
        
        if not profits:
            return {
                'total_trades': len(df),
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'max_drawdown': 0.0
            }
        
        profits = np.array(profits)
        
        return {
            'total_trades': len(profits),
            'win_rate': (profits > 0).sum() / len(profits),
            'avg_profit': profits.mean(),
            'max_loss': profits.min(),
            'max_profit': profits.max(),
            'sharpe_ratio': profits.mean() / profits.std() if profits.std() > 0 else 0
        }

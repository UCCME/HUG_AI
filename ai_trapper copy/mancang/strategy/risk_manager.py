"""
风控和仓位管理模块
负责仓位计算、风险控制和资金管理
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional


class RiskManager:
    """风险管理器"""
    
    def __init__(self, config: Dict, initial_capital: float):
        """
        初始化风险管理器
        
        Args:
            config: 策略配置字典
            initial_capital: 初始资金
        """
        self.config = config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # {symbol: {'shares': int, 'entry_price': float, 'entry_date': str}}
        self.trade_history = []
        self.daily_pnl = []
    
    def calculate_position_size(self, symbol: str, price: float, 
                               signal_strength: float = 1.0) -> int:
        """
        计算建议买入数量
        
        Args:
            symbol: 股票代码
            price: 当前价格
            signal_strength: 信号强度（0-1）
            
        Returns:
            建议买入股数（手数的整数倍）
        """
        # 1. 检查是否已达最大持仓数
        if len(self.positions) >= self.config['max_positions']:
            return 0
        
        # 2. 检查总仓位
        total_position_value = sum(
            pos['shares'] * price for pos in self.positions.values()
        )
        position_ratio = total_position_value / self.current_capital
        
        if position_ratio >= self.config['max_total_pos']:
            return 0
        
        # 3. 计算单只股票可用资金
        single_pos_capital = self.current_capital * self.config['single_pos_limit']
        
        # 4. 根据信号强度调整
        adjusted_capital = single_pos_capital * signal_strength
        
        # 5. 计算股数（A股最小单位100股）
        shares = int(adjusted_capital / price / 100) * 100
        
        # 6. 确保不超过可用资金
        available_cash = self.current_capital - total_position_value
        max_shares = int(available_cash / price / 100) * 100
        
        shares = min(shares, max_shares)
        
        return shares
    
    def can_open_position(self, symbol: str) -> Tuple[bool, str]:
        """
        检查是否可以开仓
        
        Args:
            symbol: 股票代码
            
        Returns:
            (是否可以开仓, 原因)
        """
        # 1. 检查是否已持有该股票
        if symbol in self.positions:
            return False, "已持有该股票"
        
        # 2. 检查持仓数量
        if len(self.positions) >= self.config['max_positions']:
            return False, f"已达最大持仓数({self.config['max_positions']})"
        
        # 3. 检查总仓位
        total_position_value = sum(
            pos['shares'] * pos.get('current_price', pos['entry_price']) 
            for pos in self.positions.values()
        )
        position_ratio = total_position_value / self.current_capital
        
        if position_ratio >= self.config['max_total_pos']:
            return False, f"总仓位已达上限({position_ratio:.1%})"
        
        # 4. 检查累计亏损
        total_pnl = self.calculate_total_pnl()
        loss_ratio = abs(total_pnl) / self.initial_capital if total_pnl < 0 else 0
        
        if loss_ratio >= self.config['stop_trading_loss']:
            return False, f"累计亏损达到停止交易阈值({loss_ratio:.1%})"
        
        # 5. 检查当日亏损
        if self.daily_pnl:
            today_pnl = self.daily_pnl[-1]
            today_loss_ratio = abs(today_pnl) / self.current_capital if today_pnl < 0 else 0
            
            if today_loss_ratio >= self.config['max_daily_loss']:
                return False, f"当日亏损达到上限({today_loss_ratio:.1%})"
        
        return True, "可以开仓"
    
    def add_position(self, symbol: str, shares: int, price: float, date: str):
        """
        添加持仓
        
        Args:
            symbol: 股票代码
            shares: 股数
            price: 买入价格
            date: 买入日期
        """
        self.positions[symbol] = {
            'shares': shares,
            'entry_price': price,
            'entry_date': date,
            'current_price': price,
            'position_ratio': 1.0  # 初始持仓比例100%
        }
        
        # 记录交易
        self.trade_history.append({
            'date': date,
            'symbol': symbol,
            'action': 'BUY',
            'shares': shares,
            'price': price,
            'amount': shares * price
        })
        
        # 更新资金
        self.current_capital -= shares * price
    
    def reduce_position(self, symbol: str, ratio: float, price: float, date: str) -> int:
        """
        减仓
        
        Args:
            symbol: 股票代码
            ratio: 减仓比例（0-1）
            price: 卖出价格
            date: 卖出日期
            
        Returns:
            实际卖出股数
        """
        if symbol not in self.positions:
            return 0
        
        position = self.positions[symbol]
        sell_shares = int(position['shares'] * ratio / 100) * 100  # 保证是100的整数倍
        
        if sell_shares <= 0:
            return 0
        
        # 更新持仓
        position['shares'] -= sell_shares
        position['position_ratio'] = position['shares'] / (position['shares'] + sell_shares)
        
        # 如果全部卖出，删除持仓
        if position['shares'] <= 0:
            del self.positions[symbol]
        
        # 记录交易
        self.trade_history.append({
            'date': date,
            'symbol': symbol,
            'action': 'SELL',
            'shares': sell_shares,
            'price': price,
            'amount': sell_shares * price,
            'pnl': (price - position['entry_price']) * sell_shares
        })
        
        # 更新资金
        self.current_capital += sell_shares * price
        
        return sell_shares
    
    def close_position(self, symbol: str, price: float, date: str) -> int:
        """
        平仓
        
        Args:
            symbol: 股票代码
            price: 卖出价格
            date: 卖出日期
            
        Returns:
            卖出股数
        """
        return self.reduce_position(symbol, 1.0, price, date)
    
    def update_position_price(self, symbol: str, current_price: float):
        """
        更新持仓价格
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
        """
        if symbol in self.positions:
            self.positions[symbol]['current_price'] = current_price
    
    def calculate_position_pnl(self, symbol: str) -> Dict:
        """
        计算单个持仓盈亏
        
        Args:
            symbol: 股票代码
            
        Returns:
            盈亏信息字典
        """
        if symbol not in self.positions:
            return {}
        
        position = self.positions[symbol]
        current_price = position.get('current_price', position['entry_price'])
        
        pnl = (current_price - position['entry_price']) * position['shares']
        pnl_ratio = (current_price - position['entry_price']) / position['entry_price']
        
        return {
            'symbol': symbol,
            'shares': position['shares'],
            'entry_price': position['entry_price'],
            'current_price': current_price,
            'pnl': pnl,
            'pnl_ratio': pnl_ratio,
            'position_value': current_price * position['shares']
        }
    
    def calculate_total_pnl(self) -> float:
        """
        计算总盈亏
        
        Returns:
            总盈亏金额
        """
        total_pnl = 0.0
        
        for symbol in self.positions:
            pnl_info = self.calculate_position_pnl(symbol)
            total_pnl += pnl_info.get('pnl', 0)
        
        return total_pnl
    
    def get_portfolio_status(self) -> Dict:
        """
        获取组合状态
        
        Returns:
            组合状态字典
        """
        total_position_value = sum(
            pos['shares'] * pos.get('current_price', pos['entry_price'])
            for pos in self.positions.values()
        )
        
        total_value = self.current_capital + total_position_value
        total_pnl = total_value - self.initial_capital
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'position_value': total_position_value,
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_return': total_pnl / self.initial_capital,
            'position_ratio': total_position_value / total_value,
            'position_count': len(self.positions),
            'available_cash': self.current_capital
        }
    
    def check_single_loss_limit(self, symbol: str, current_price: float) -> bool:
        """
        检查单笔亏损是否超限
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            
        Returns:
            是否超限
        """
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        loss = (current_price - position['entry_price']) / position['entry_price']
        
        return loss < -self.config['max_single_loss']
    
    def adjust_position_for_high_risk(self):
        """
        高风险期调整仓位（降低至30%）
        """
        target_ratio = self.config['max_total_pos_high_risk']
        
        total_position_value = sum(
            pos['shares'] * pos.get('current_price', pos['entry_price'])
            for pos in self.positions.values()
        )
        
        current_ratio = total_position_value / (self.current_capital + total_position_value)
        
        if current_ratio > target_ratio:
            # 需要减仓
            reduce_ratio = 1 - (target_ratio / current_ratio)
            return reduce_ratio
        
        return 0.0
    
    def get_trade_statistics(self) -> Dict:
        """
        获取交易统计
        
        Returns:
            交易统计字典
        """
        if not self.trade_history:
            return {}
        
        buy_trades = [t for t in self.trade_history if t['action'] == 'BUY']
        sell_trades = [t for t in self.trade_history if t['action'] == 'SELL']
        
        win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
        loss_trades = [t for t in sell_trades if t.get('pnl', 0) < 0]
        
        return {
            'total_trades': len(buy_trades),
            'win_trades': len(win_trades),
            'loss_trades': len(loss_trades),
            'win_rate': len(win_trades) / len(sell_trades) if sell_trades else 0,
            'avg_win': sum(t['pnl'] for t in win_trades) / len(win_trades) if win_trades else 0,
            'avg_loss': sum(t['pnl'] for t in loss_trades) / len(loss_trades) if loss_trades else 0,
            'total_pnl': sum(t.get('pnl', 0) for t in sell_trades),
        }

"""
风控和仓位管理模块
"""

from typing import Dict, List, Tuple
from datetime import datetime


class RiskManager:
    """风险管理器"""
    
    def __init__(self, config: Dict, initial_capital: float):
        """
        初始化风险管理器
        
        Args:
            config: 策略配置
            initial_capital: 初始资金
        """
        self.config = config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # {position_id: position_info}
        self.trade_history = []
        self.profits_for_hedge = 0.0  # 累计利润用于尾部对冲
    
    def calculate_position_size(self, max_loss: float) -> float:
        """
        计算建议仓位大小
        
        Args:
            max_loss: 策略最大亏损
            
        Returns:
            建议投入资金
        """
        # 单笔限制
        single_limit = self.current_capital * self.config['single_position_limit']
        
        # 基于最大亏损计算
        # 确保即使全部亏损也不超过单笔限制
        suggested_size = min(single_limit, single_limit / max_loss * single_limit)
        
        return suggested_size
    
    def can_open_position(self) -> Tuple[bool, str]:
        """
        检查是否可以开新仓
        
        Returns:
            (是否可以, 原因)
        """
        # 1. 检查持仓数量
        if len(self.positions) >= self.config['max_positions']:
            return False, f"已达最大持仓数({self.config['max_positions']})"
        
        # 2. 检查总仓位
        total_exposure = sum(pos['invested_capital'] for pos in self.positions.values())
        exposure_ratio = total_exposure / self.current_capital
        
        if exposure_ratio >= self.config['total_position_limit']:
            return False, f"总仓位已达上限({exposure_ratio:.1%})"
        
        return True, "可以开仓"
    
    def add_position(self, position_id: str, position_info: Dict):
        """
        添加持仓
        
        Args:
            position_id: 持仓ID
            position_info: 持仓信息
        """
        self.positions[position_id] = {
            **position_info,
            'open_time': datetime.now(),
            'status': 'open'
        }
        
        # 记录交易
        self.trade_history.append({
            'time': datetime.now(),
            'position_id': position_id,
            'action': 'OPEN',
            'details': position_info
        })
    
    def close_position(self, position_id: str, close_info: Dict):
        """
        平仓
        
        Args:
            position_id: 持仓ID
            close_info: 平仓信息
        """
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        position['status'] = 'closed'
        position['close_time'] = datetime.now()
        position['close_info'] = close_info
        
        # 计算盈亏
        pnl = close_info.get('pnl', 0)
        self.current_capital += pnl
        
        # 如果盈利，累计用于尾部对冲的资金
        if pnl > 0:
            self.profits_for_hedge += pnl * self.config['tail_hedge_ratio']
        
        # 记录交易
        self.trade_history.append({
            'time': datetime.now(),
            'position_id': position_id,
            'action': 'CLOSE',
            'pnl': pnl,
            'details': close_info
        })
        
        # 从活跃持仓中移除
        del self.positions[position_id]
    
    def should_add_tail_hedge(self) -> Tuple[bool, float]:
        """
        检查是否应该添加尾部对冲
        
        Returns:
            (是否添加, 可用资金)
        """
        if self.profits_for_hedge >= self.current_capital * 0.01:  # 至少1%资金
            return True, self.profits_for_hedge
        
        return False, 0.0
    
    def add_tail_hedge(self, hedge_cost: float):
        """
        添加尾部对冲
        
        Args:
            hedge_cost: 对冲成本
        """
        self.profits_for_hedge -= hedge_cost
        self.current_capital -= hedge_cost
        
        self.trade_history.append({
            'time': datetime.now(),
            'action': 'TAIL_HEDGE',
            'cost': hedge_cost
        })
    
    def get_portfolio_status(self) -> Dict:
        """
        获取组合状态
        
        Returns:
            组合状态字典
        """
        total_exposure = sum(pos['invested_capital'] for pos in self.positions.values())
        total_pnl = self.current_capital - self.initial_capital
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_exposure': total_exposure,
            'exposure_ratio': total_exposure / self.current_capital,
            'position_count': len(self.positions),
            'total_pnl': total_pnl,
            'total_return': total_pnl / self.initial_capital,
            'profits_for_hedge': self.profits_for_hedge
        }
    
    def get_trade_statistics(self) -> Dict:
        """
        获取交易统计
        
        Returns:
            交易统计字典
        """
        closed_trades = [t for t in self.trade_history if t['action'] == 'CLOSE']
        
        if not closed_trades:
            return {}
        
        win_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        loss_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
        
        return {
            'total_trades': len(closed_trades),
            'win_trades': len(win_trades),
            'loss_trades': len(loss_trades),
            'win_rate': len(win_trades) / len(closed_trades) if closed_trades else 0,
            'avg_win': sum(t['pnl'] for t in win_trades) / len(win_trades) if win_trades else 0,
            'avg_loss': sum(t['pnl'] for t in loss_trades) / len(loss_trades) if loss_trades else 0,
            'total_pnl': sum(t.get('pnl', 0) for t in closed_trades)
        }

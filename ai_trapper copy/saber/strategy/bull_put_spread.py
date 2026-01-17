"""
牛市认沽价差策略（模式B：高波防御）
Bull Put Spread - 卖出OTM Put + 买入更低行权价Put
"""

import pandas as pd
from typing import Dict, Tuple, Optional
from saber.utils.options_pricing import OptionsPricing
from saber.utils.market_data import MarketDataLoader


class BullPutSpread:
    """牛市认沽价差策略"""
    
    def __init__(self, config: Dict):
        """
        初始化策略
        
        Args:
            config: 策略配置
        """
        self.config = config
        self.data_loader = MarketDataLoader(config)
        self.pricer = OptionsPricing()
    
    def select_strikes(self, spot_price: float, support: float) -> Tuple[float, float]:
        """
        选择行权价
        
        Args:
            spot_price: 现货价格
            support: 支撑位
            
        Returns:
            (卖出Put行权价, 买入Put行权价)
        """
        # 卖出腿：支撑位上方的虚值Put
        short_moneyness = self.config['put_spread_short_moneyness']
        short_strike_target = spot_price * (1 + short_moneyness)  # 负值，所以是虚值
        
        # 如果有明确支撑位，优先使用支撑位
        if support and support < spot_price:
            short_strike = max(short_strike_target, support)
        else:
            short_strike = short_strike_target
        
        # 买入腿：更低的行权价，锁定最大亏损
        long_moneyness = self.config['put_spread_long_moneyness']
        long_strike = spot_price * (1 + long_moneyness)  # 更负的值
        
        return short_strike, long_strike
    
    def calculate_position_metrics(self, spot_price: float, short_strike: float,
                                  long_strike: float, expiry_date: str,
                                  current_iv: float) -> Dict:
        """
        计算持仓指标
        
        Args:
            spot_price: 现货价格
            short_strike: 卖出Put行权价
            long_strike: 买入Put行权价
            expiry_date: 到期日
            current_iv: 当前IV
            
        Returns:
            持仓指标字典
        """
        # 计算到期时间
        T = self.pricer.days_to_expiry(expiry_date)
        r = 0.0
        
        # 计算期权价格
        short_put_price = self.pricer.black_scholes(
            spot_price, short_strike, T, r, current_iv, 'put'
        )
        long_put_price = self.pricer.black_scholes(
            spot_price, long_strike, T, r, current_iv, 'put'
        )
        
        # 计算Greeks
        short_greeks = self.pricer.calculate_greeks(
            spot_price, short_strike, T, r, current_iv, 'put'
        )
        long_greeks = self.pricer.calculate_greeks(
            spot_price, long_strike, T, r, current_iv, 'put'
        )
        
        # 组合Greeks（注意：卖出期权的Greeks要取反）
        spread_greeks = {
            'delta': -short_greeks['delta'] + long_greeks['delta'],
            'gamma': -short_greeks['gamma'] + long_greeks['gamma'],
            'theta': -short_greeks['theta'] + long_greeks['theta'],
            'vega': -short_greeks['vega'] + long_greeks['vega'],
            'rho': -short_greeks['rho'] + long_greeks['rho']
        }
        
        # 计算最大盈亏
        max_profit, max_loss = self.pricer.calculate_max_profit_loss(
            long_strike, short_strike, long_put_price, short_put_price, 'put'
        )
        
        # 计算盈亏平衡点
        breakeven = self.pricer.calculate_breakeven(
            long_strike, short_strike, long_put_price, short_put_price, 'put'
        )
        
        return {
            'short_strike': short_strike,
            'long_strike': long_strike,
            'short_premium': short_put_price,
            'long_premium': long_put_price,
            'net_credit': short_put_price - long_put_price,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'profit_loss_ratio': max_profit / max_loss if max_loss > 0 else 0,
            'breakeven': breakeven,
            'greeks': spread_greeks,
            'expiry_date': expiry_date,
            'days_to_expiry': T * 365
        }
    
    def check_entry_conditions(self, spot_price: float, metrics: Dict,
                              initial_iv: float) -> Tuple[bool, str]:
        """
        检查开仓条件
        
        Args:
            spot_price: 现货价格
            metrics: 持仓指标
            initial_iv: 开仓时IV
            
        Returns:
            (是否可以开仓, 原因)
        """
        # 1. 检查是否收到权利金
        if metrics['net_credit'] <= 0:
            return False, "未收到权利金"
        
        # 2. 检查到期时间
        dte_min = self.config['put_spread_dte_min']
        dte_max = self.config['put_spread_dte_max']
        
        if not (dte_min <= metrics['days_to_expiry'] <= dte_max):
            return False, f"到期天数({metrics['days_to_expiry']:.0f})不在目标区间"
        
        # 3. 检查Delta（应为正或接近0，表示看涨或中性）
        if metrics['greeks']['delta'] < -0.2:
            return False, f"Delta过度负值({metrics['greeks']['delta']:.2f})"
        
        # 4. 检查Theta（应为正值，时间流逝有利）
        if metrics['greeks']['theta'] <= 0:
            return False, "Theta为负，时间流逝不利"
        
        # 5. 检查Vega（应为负值，受益于IV下降）
        if metrics['greeks']['vega'] >= 0:
            return False, "Vega为正，不受益于IV下降"
        
        return True, "满足开仓条件"
    
    def check_exit_conditions(self, spot_price: float, metrics: Dict,
                             entry_metrics: Dict, current_iv: float,
                             support: float) -> Tuple[bool, str, float]:
        """
        检查平仓条件
        
        Args:
            spot_price: 当前现货价格
            metrics: 当前持仓指标
            entry_metrics: 开仓时指标
            current_iv: 当前IV
            support: 支撑位
            
        Returns:
            (是否平仓, 原因, 平仓比例)
        """
        # 1. 止盈：权利金衰减达到目标
        current_value = metrics['short_premium'] - metrics['long_premium']
        profit = entry_metrics['net_credit'] - current_value
        profit_ratio = profit / entry_metrics['max_profit'] if entry_metrics['max_profit'] > 0 else 0
        
        if profit_ratio >= self.config['take_profit_ratio']:
            return True, f"达到止盈目标({profit_ratio:.1%})", 1.0
        
        # 2. 止损：跌破支撑位（卖出Put行权价）
        if self.config['stop_loss_support_break']:
            if spot_price < entry_metrics['short_strike']:
                return True, "跌破卖出Put行权价", 1.0
        
        # 3. 止损：IV逻辑背离（IV不跌反涨）
        iv_change = (current_iv - entry_metrics.get('initial_iv', current_iv)) / entry_metrics.get('initial_iv', current_iv)
        
        if iv_change > self.config['put_spread_iv_rise_threshold']:
            return True, f"IV逻辑背离(上涨{iv_change:.1%})", 1.0
        
        # 4. 止损：亏损超限
        loss = current_value - entry_metrics['net_credit']
        loss_ratio = loss / entry_metrics['max_loss'] if loss > 0 and entry_metrics['max_loss'] > 0 else 0
        
        if loss_ratio >= self.config['stop_loss_max_loss']:
            return True, f"亏损超限({loss_ratio:.1%})", 1.0
        
        # 5. 时间止损
        if metrics['days_to_expiry'] <= self.config['stop_loss_dte_threshold']:
            if profit < entry_metrics['max_profit'] * 0.5:
                return True, "临近到期且盈利不足，避免Gamma风险", 1.0
        
        return False, "持有", 0.0

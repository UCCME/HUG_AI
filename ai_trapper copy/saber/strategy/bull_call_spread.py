"""
牛市认购价差策略（模式A：低波进攻）
Bull Call Spread - 买入ATM Call + 卖出OTM Call
"""

import pandas as pd
from typing import Dict, Tuple, Optional
from saber.utils.options_pricing import OptionsPricing
from saber.utils.market_data import MarketDataLoader


class BullCallSpread:
    """牛市认购价差策略"""
    
    def __init__(self, config: Dict):
        """
        初始化策略
        
        Args:
            config: 策略配置
        """
        self.config = config
        self.data_loader = MarketDataLoader(config)
        self.pricer = OptionsPricing()
    
    def select_strikes(self, spot_price: float, support: float, 
                      resistance: float) -> Tuple[float, float]:
        """
        选择行权价
        
        Args:
            spot_price: 现货价格
            support: 支撑位
            resistance: 阻力位
            
        Returns:
            (买入Call行权价, 卖出Call行权价)
        """
        # 买入腿：ATM或轻度虚值
        long_moneyness = self.config['call_spread_long_moneyness']
        long_strike = spot_price * (1 + long_moneyness)
        
        # 卖出腿：阻力位或5%-10%虚值
        short_moneyness = self.config['call_spread_short_moneyness']
        short_strike_target = spot_price * (1 + short_moneyness)
        
        # 如果有明确阻力位，优先使用阻力位
        if resistance and resistance > long_strike:
            short_strike = min(short_strike_target, resistance)
        else:
            short_strike = short_strike_target
        
        return long_strike, short_strike
    
    def calculate_position_metrics(self, spot_price: float, long_strike: float,
                                  short_strike: float, expiry_date: str,
                                  current_iv: float) -> Dict:
        """
        计算持仓指标
        
        Args:
            spot_price: 现货价格
            long_strike: 买入Call行权价
            short_strike: 卖出Call行权价
            expiry_date: 到期日
            current_iv: 当前IV
            
        Returns:
            持仓指标字典
        """
        # 计算到期时间
        T = self.pricer.days_to_expiry(expiry_date)
        r = 0.0  # 加密货币无风险利率近似为0
        
        # 计算期权价格
        long_call_price = self.pricer.black_scholes(
            spot_price, long_strike, T, r, current_iv, 'call'
        )
        short_call_price = self.pricer.black_scholes(
            spot_price, short_strike, T, r, current_iv, 'call'
        )
        
        # 计算Greeks
        long_greeks = self.pricer.calculate_greeks(
            spot_price, long_strike, T, r, current_iv, 'call'
        )
        short_greeks = self.pricer.calculate_greeks(
            spot_price, short_strike, T, r, current_iv, 'call'
        )
        
        # 组合Greeks
        spread_greeks = self.pricer.calculate_spread_greeks(long_greeks, short_greeks)
        
        # 计算最大盈亏
        max_profit, max_loss = self.pricer.calculate_max_profit_loss(
            long_strike, short_strike, long_call_price, short_call_price, 'call'
        )
        
        # 计算盈亏平衡点
        breakeven = self.pricer.calculate_breakeven(
            long_strike, short_strike, long_call_price, short_call_price, 'call'
        )
        
        return {
            'long_strike': long_strike,
            'short_strike': short_strike,
            'long_premium': long_call_price,
            'short_premium': short_call_price,
            'net_debit': long_call_price - short_call_price,
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
        # 1. 检查盈亏比
        if metrics['profit_loss_ratio'] < 1.0:
            return False, f"盈亏比过低({metrics['profit_loss_ratio']:.2f})"
        
        # 2. 检查到期时间
        dte_min = self.config['call_spread_dte_min']
        dte_max = self.config['call_spread_dte_max']
        
        if not (dte_min <= metrics['days_to_expiry'] <= dte_max):
            return False, f"到期天数({metrics['days_to_expiry']:.0f})不在目标区间"
        
        # 3. 检查Delta（应为正值，表示看涨）
        if metrics['greeks']['delta'] <= 0:
            return False, "Delta为负，不符合看涨预期"
        
        # 4. 检查Vega（应为正值，受益于IV上涨）
        if metrics['greeks']['vega'] <= 0:
            return False, "Vega为负，不受益于IV上涨"
        
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
        # 1. 止盈：达到最大利润的目标比例
        current_profit = (metrics['short_premium'] - metrics['long_premium']) - entry_metrics['net_debit']
        profit_ratio = current_profit / entry_metrics['max_profit'] if entry_metrics['max_profit'] > 0 else 0
        
        if profit_ratio >= self.config['take_profit_ratio']:
            return True, f"达到止盈目标({profit_ratio:.1%})", 1.0
        
        # 2. 止盈：触及阻力位
        if self.config['resistance_take_profit']:
            if spot_price >= entry_metrics['short_strike'] * 0.98:  # 接近卖出行权价
                return True, "接近阻力位(卖出行权价)", 1.0
        
        # 3. 止损：跌破支撑位
        if self.config['stop_loss_support_break']:
            if support and spot_price < support:
                return True, "跌破支撑位，趋势失效", 1.0
        
        # 4. 止损：权利金亏损超限
        loss_ratio = abs(current_profit) / entry_metrics['net_debit'] if current_profit < 0 else 0
        
        if loss_ratio >= self.config['stop_loss_max_loss']:
            return True, f"权利金亏损超限({loss_ratio:.1%})", 1.0
        
        # 5. 止损：IV逻辑背离（IV不涨反跌）
        iv_change = (current_iv - entry_metrics.get('initial_iv', current_iv)) / entry_metrics.get('initial_iv', current_iv)
        
        if iv_change < self.config['call_spread_iv_drop_threshold']:
            return True, f"IV逻辑背离(下跌{abs(iv_change):.1%})", 1.0
        
        # 6. 时间止损：临近到期
        if metrics['days_to_expiry'] <= self.config['stop_loss_dte_threshold']:
            if current_profit < 0:
                return True, "临近到期且未盈利，避免Gamma风险", 1.0
        
        return False, "持有", 0.0

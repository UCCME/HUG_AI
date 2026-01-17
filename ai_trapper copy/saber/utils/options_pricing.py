"""
期权定价和Greeks计算模块
使用Black-Scholes模型
"""

import numpy as np
from scipy.stats import norm
from typing import Dict, Tuple
from datetime import datetime


class OptionsPricing:
    """期权定价类"""
    
    @staticmethod
    def black_scholes(S: float, K: float, T: float, r: float, sigma: float, 
                     option_type: str = 'call') -> float:
        """
        Black-Scholes期权定价公式
        
        Args:
            S: 标的资产当前价格
            K: 行权价
            T: 到期时间（年）
            r: 无风险利率
            sigma: 波动率
            option_type: 期权类型 'call' 或 'put'
            
        Returns:
            期权价格
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return price
    
    @staticmethod
    def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float,
                        option_type: str = 'call') -> Dict[str, float]:
        """
        计算期权Greeks
        
        Args:
            S: 标的资产当前价格
            K: 行权价
            T: 到期时间（年）
            r: 无风险利率
            sigma: 波动率
            option_type: 期权类型
            
        Returns:
            Greeks字典
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Delta
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:
            delta = -norm.cdf(-d1)
        
        # Gamma（Call和Put相同）
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Theta
        if option_type == 'call':
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    - r * K * np.exp(-r * T) * norm.cdf(d2))
        else:
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    + r * K * np.exp(-r * T) * norm.cdf(-d2))
        
        # Vega（Call和Put相同）
        vega = S * norm.pdf(d1) * np.sqrt(T)
        
        # Rho
        if option_type == 'call':
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta / 365,  # 日Theta
            'vega': vega / 100,    # 1%波动率变化的影响
            'rho': rho / 100       # 1%利率变化的影响
        }
    
    @staticmethod
    def calculate_spread_greeks(long_option: Dict, short_option: Dict) -> Dict[str, float]:
        """
        计算价差组合的Greeks
        
        Args:
            long_option: 买入期权的Greeks
            short_option: 卖出期权的Greeks
            
        Returns:
            组合Greeks
        """
        return {
            'delta': long_option['delta'] - short_option['delta'],
            'gamma': long_option['gamma'] - short_option['gamma'],
            'theta': long_option['theta'] - short_option['theta'],
            'vega': long_option['vega'] - short_option['vega'],
            'rho': long_option['rho'] - short_option['rho']
        }
    
    @staticmethod
    def calculate_max_profit_loss(long_strike: float, short_strike: float,
                                 long_premium: float, short_premium: float,
                                 spread_type: str = 'call') -> Tuple[float, float]:
        """
        计算价差策略的最大盈亏
        
        Args:
            long_strike: 买入期权行权价
            short_strike: 卖出期权行权价
            long_premium: 买入期权权利金
            short_premium: 卖出期权权利金
            spread_type: 价差类型 'call' 或 'put'
            
        Returns:
            (最大利润, 最大亏损)
        """
        if spread_type == 'call':
            # Bull Call Spread
            net_debit = long_premium - short_premium
            max_profit = (short_strike - long_strike) - net_debit
            max_loss = net_debit
        else:
            # Bull Put Spread
            net_credit = short_premium - long_premium
            max_profit = net_credit
            max_loss = (short_strike - long_strike) - net_credit
        
        return max_profit, max_loss
    
    @staticmethod
    def calculate_breakeven(long_strike: float, short_strike: float,
                          long_premium: float, short_premium: float,
                          spread_type: str = 'call') -> float:
        """
        计算盈亏平衡点
        
        Args:
            long_strike: 买入期权行权价
            short_strike: 卖出期权行权价
            long_premium: 买入期权权利金
            short_premium: 卖出期权权利金
            spread_type: 价差类型
            
        Returns:
            盈亏平衡点价格
        """
        if spread_type == 'call':
            # Bull Call Spread
            net_debit = long_premium - short_premium
            breakeven = long_strike + net_debit
        else:
            # Bull Put Spread
            net_credit = short_premium - long_premium
            breakeven = short_strike - net_credit
        
        return breakeven
    
    @staticmethod
    def days_to_expiry(expiry_date: str) -> float:
        """
        计算到期天数
        
        Args:
            expiry_date: 到期日期字符串 'YYYY-MM-DD'
            
        Returns:
            到期天数（年化）
        """
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        now = datetime.now()
        days = (expiry - now).days
        return max(days / 365.0, 0.001)  # 避免除零
    
    @staticmethod
    def calculate_moneyness(spot_price: float, strike: float) -> float:
        """
        计算期权价值度
        
        Args:
            spot_price: 现货价格
            strike: 行权价
            
        Returns:
            价值度（正数=实值，负数=虚值，0=平值）
        """
        return (spot_price - strike) / spot_price

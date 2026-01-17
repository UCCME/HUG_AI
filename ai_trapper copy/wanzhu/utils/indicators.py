"""
技术指标计算模块
实现松松策略中使用的各种技术指标：OBV、均线、MACD等
"""

import pandas as pd
import numpy as np
from typing import Union, Tuple


class TechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """
        计算能量潮指标（On Balance Volume）
        OBV是松松用来判断主力资金动向的核心指标
        
        Args:
            df: 包含'close'和'volume'列的DataFrame
            
        Returns:
            OBV指标序列
        """
        obv = pd.Series(index=df.index, dtype=float)
        obv.iloc[0] = df['volume'].iloc[0]
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
                
        return obv
    
    @staticmethod
    def calculate_ma(series: pd.Series, period: int) -> pd.Series:
        """
        计算简单移动平均线
        
        Args:
            series: 价格序列
            period: 周期
            
        Returns:
            均线序列
        """
        return series.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """
        计算指数移动平均线
        
        Args:
            series: 价格序列
            period: 周期
            
        Returns:
            指数均线序列
        """
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame, 
                       fast_period: int = 12, 
                       slow_period: int = 26, 
                       signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标
        用于判断趋势和背离
        
        Args:
            df: 包含'close'列的DataFrame
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            (DIF, DEA, MACD柱)的元组
        """
        close = df['close']
        
        # 计算快慢线
        ema_fast = TechnicalIndicators.calculate_ema(close, fast_period)
        ema_slow = TechnicalIndicators.calculate_ema(close, slow_period)
        
        # DIF线
        dif = ema_fast - ema_slow
        
        # DEA线（信号线）
        dea = dif.ewm(span=signal_period, adjust=False).mean()
        
        # MACD柱
        macd = (dif - dea) * 2
        
        return dif, dea, macd
    
    @staticmethod
    def calculate_turnover_rate(df: pd.DataFrame, 
                                 total_shares: float) -> pd.Series:
        """
        计算换手率
        
        Args:
            df: 包含'volume'列的DataFrame
            total_shares: 总股本
            
        Returns:
            换手率序列
        """
        return (df['volume'] / total_shares) * 100
    
    @staticmethod
    def is_limit_up(current_price: float, 
                    prev_close: float, 
                    limit_pct: float = 0.10) -> bool:
        """
        判断是否涨停
        
        Args:
            current_price: 当前价格
            prev_close: 前一日收盘价
            limit_pct: 涨停幅度（默认10%）
            
        Returns:
            是否涨停
        """
        limit_price = prev_close * (1 + limit_pct)
        return abs(current_price - limit_price) / limit_price < 0.001
    
    @staticmethod
    def calculate_money_flow(df: pd.DataFrame, 
                            period: int = 5) -> pd.Series:
        """
        计算资金流向指标
        正值表示资金流入，负值表示资金流出
        
        Args:
            df: 包含OHLCV数据的DataFrame
            period: 计算周期
            
        Returns:
            资金流向序列
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        # 判断资金流向
        positive_flow = pd.Series(0.0, index=df.index)
        negative_flow = pd.Series(0.0, index=df.index)
        
        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.iloc[i] = money_flow.iloc[i]
            else:
                negative_flow.iloc[i] = money_flow.iloc[i]
        
        # 计算资金流向比率
        positive_sum = positive_flow.rolling(window=period).sum()
        negative_sum = negative_flow.rolling(window=period).sum()
        
        mfi = 100 - (100 / (1 + positive_sum / negative_sum))
        
        return mfi
    
    @staticmethod
    def detect_divergence(price: pd.Series, 
                          indicator: pd.Series, 
                          window: int = 5) -> pd.Series:
        """
        检测背离信号
        用于判断顶背离或底背离
        
        Args:
            price: 价格序列
            indicator: 指标序列（如MACD）
            window: 检测窗口
            
        Returns:
            背离信号序列（1=底背离，-1=顶背离，0=无背离）
        """
        divergence = pd.Series(0, index=price.index)
        
        for i in range(window, len(price)):
            price_trend = price.iloc[i] - price.iloc[i-window]
            indicator_trend = indicator.iloc[i] - indicator.iloc[i-window]
            
            # 顶背离：价格创新高，指标未创新高
            if price_trend > 0 and indicator_trend < 0:
                divergence.iloc[i] = -1
            # 底背离：价格创新低，指标未创新低
            elif price_trend < 0 and indicator_trend > 0:
                divergence.iloc[i] = 1
                
        return divergence

"""
技术指标计算模块
包含均线、布林带、波动率等指标
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict


class TechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_ma(data: pd.DataFrame, periods: list) -> pd.DataFrame:
        """
        计算多条移动平均线
        
        Args:
            data: 价格数据
            periods: 周期列表
            
        Returns:
            包含均线的DataFrame
        """
        result = data.copy()
        for period in periods:
            result[f'ma{period}'] = data['close'].rolling(window=period).mean()
        return result
    
    @staticmethod
    def check_ma_bullish_alignment(data: pd.DataFrame, periods: list = [10, 20, 30, 60]) -> bool:
        """
        检查均线多头排列
        
        Args:
            data: 包含均线的价格数据
            periods: 均线周期列表
            
        Returns:
            是否多头排列
        """
        if len(data) < max(periods):
            return False
        
        # 确保均线已计算
        for period in periods:
            if f'ma{period}' not in data.columns:
                data[f'ma{period}'] = data['close'].rolling(window=period).mean()
        
        # 检查最新的均线排列
        latest = data.iloc[-1]
        
        # 多头排列：短期均线 > 长期均线
        for i in range(len(periods) - 1):
            if latest[f'ma{periods[i]}'] <= latest[f'ma{periods[i+1]}']:
                return False
        
        return True
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, 
                                 std: float = 2.0) -> pd.DataFrame:
        """
        计算布林带
        
        Args:
            data: 价格数据
            period: 周期
            std: 标准差倍数
            
        Returns:
            包含布林带的DataFrame
        """
        result = data.copy()
        
        # 中轨（移动平均线）
        result['bb_middle'] = data['close'].rolling(window=period).mean()
        
        # 标准差
        rolling_std = data['close'].rolling(window=period).std()
        
        # 上轨和下轨
        result['bb_upper'] = result['bb_middle'] + (rolling_std * std)
        result['bb_lower'] = result['bb_middle'] - (rolling_std * std)
        
        return result
    
    @staticmethod
    def check_price_in_bollinger_range(data: pd.DataFrame) -> bool:
        """
        检查价格是否在布林带中轨和上轨之间
        
        Args:
            data: 包含布林带的价格数据
            
        Returns:
            是否在合理区间
        """
        if 'bb_middle' not in data.columns or 'bb_upper' not in data.columns:
            data = TechnicalIndicators.calculate_bollinger_bands(data)
        
        latest_price = data['close'].iloc[-1]
        bb_middle = data['bb_middle'].iloc[-1]
        bb_upper = data['bb_upper'].iloc[-1]
        
        return bb_middle <= latest_price <= bb_upper
    
    @staticmethod
    def calculate_volume_surge(data: pd.DataFrame, ma_period: int = 20, 
                              threshold: float = 2.0) -> bool:
        """
        检测是否放量
        
        Args:
            data: 价格数据（包含volume）
            ma_period: 成交量均线周期
            threshold: 放量阈值（倍数）
            
        Returns:
            是否放量
        """
        if len(data) < ma_period:
            return False
        
        volume_ma = data['volume'].rolling(window=ma_period).mean()
        current_volume = data['volume'].iloc[-1]
        avg_volume = volume_ma.iloc[-1]
        
        return current_volume > avg_volume * threshold
    
    @staticmethod
    def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算平均真实波幅（ATR）
        
        Args:
            data: 价格数据
            period: 周期
            
        Returns:
            ATR序列
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算ATR
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def identify_trend(data: pd.DataFrame, ma_periods: list = [10, 20, 60]) -> str:
        """
        识别趋势方向
        
        Args:
            data: 价格数据
            ma_periods: 均线周期
            
        Returns:
            趋势方向：'bullish', 'bearish', 'neutral'
        """
        if TechnicalIndicators.check_ma_bullish_alignment(data, ma_periods):
            return 'bullish'
        
        # 检查空头排列
        for period in ma_periods:
            if f'ma{period}' not in data.columns:
                data[f'ma{period}'] = data['close'].rolling(window=period).mean()
        
        latest = data.iloc[-1]
        is_bearish = True
        for i in range(len(ma_periods) - 1):
            if latest[f'ma{ma_periods[i]}'] >= latest[f'ma{ma_periods[i+1]}']:
                is_bearish = False
                break
        
        if is_bearish:
            return 'bearish'
        
        return 'neutral'

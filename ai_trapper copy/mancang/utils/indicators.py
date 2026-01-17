"""
技术指标计算模块
包含均线、涨停板识别、资金流向等指标
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


class TechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_ma(data: pd.DataFrame, period: int = 5, column: str = 'close') -> pd.Series:
        """
        计算移动平均线
        
        Args:
            data: 股票数据
            period: 周期
            column: 计算列名
            
        Returns:
            MA序列
        """
        return data[column].rolling(window=period).mean()
    
    @staticmethod
    def calculate_multiple_ma(data: pd.DataFrame, periods: list = [5, 7, 10, 20, 60]) -> pd.DataFrame:
        """
        计算多条均线
        
        Args:
            data: 股票数据
            periods: 周期列表
            
        Returns:
            包含多条均线的DataFrame
        """
        result = data.copy()
        for period in periods:
            result[f'ma{period}'] = TechnicalIndicators.calculate_ma(data, period)
        return result
    
    @staticmethod
    def is_limit_up(data: pd.DataFrame, threshold: float = 0.095) -> pd.Series:
        """
        判断是否涨停
        
        Args:
            data: 股票数据（需包含open, close列）
            threshold: 涨停阈值（默认9.5%，考虑误差）
            
        Returns:
            布尔序列
        """
        pct_change = (data['close'] - data['close'].shift(1)) / data['close'].shift(1)
        return pct_change >= threshold
    
    @staticmethod
    def count_consecutive_limit_up(data: pd.DataFrame) -> pd.Series:
        """
        计算连续涨停天数
        
        Args:
            data: 股票数据
            
        Returns:
            连续涨停天数序列
        """
        limit_up = TechnicalIndicators.is_limit_up(data)
        
        # 计算连续涨停
        consecutive = pd.Series(0, index=data.index)
        count = 0
        
        for i in range(len(limit_up)):
            if limit_up.iloc[i]:
                count += 1
            else:
                count = 0
            consecutive.iloc[i] = count
            
        return consecutive
    
    @staticmethod
    def calculate_volume_ratio(data: pd.DataFrame, period: int = 5) -> pd.Series:
        """
        计算量比
        
        Args:
            data: 股票数据（需包含volume列）
            period: 平均周期
            
        Returns:
            量比序列
        """
        avg_volume = data['volume'].rolling(window=period).mean()
        return data['volume'] / avg_volume
    
    @staticmethod
    def detect_pullback_to_ma(data: pd.DataFrame, ma_period: int = 5, 
                             tolerance: float = 0.02) -> pd.Series:
        """
        检测回踩均线
        
        Args:
            data: 股票数据
            ma_period: 均线周期
            tolerance: 容忍度
            
        Returns:
            布尔序列，True表示回踩均线
        """
        ma = TechnicalIndicators.calculate_ma(data, ma_period)
        
        # 当前价格在均线附近（上下tolerance范围内）
        near_ma = (data['low'] <= ma * (1 + tolerance)) & (data['close'] > ma)
        
        return near_ma
    
    @staticmethod
    def detect_surge_and_pullback(data: pd.DataFrame, 
                                 surge_threshold: float = 0.08,
                                 pullback_threshold: float = 0.02) -> pd.Series:
        """
        检测冲高回落
        
        Args:
            data: 股票数据
            surge_threshold: 冲高阈值
            pullback_threshold: 回落阈值
            
        Returns:
            布尔序列，True表示冲高回落
        """
        # 当日最高价相对开盘价涨幅
        surge = (data['high'] - data['open']) / data['open']
        
        # 收盘价相对最高价回落幅度
        pullback = (data['high'] - data['close']) / data['high']
        
        # 冲高且回落
        return (surge >= surge_threshold) & (pullback >= pullback_threshold)
    
    @staticmethod
    def is_uptrend(data: pd.DataFrame, period: int = 3) -> pd.Series:
        """
        判断是否处于上升趋势
        
        Args:
            data: 股票数据
            period: 判断周期
            
        Returns:
            布尔序列
        """
        # 简单判断：最近N天收盘价递增
        uptrend = pd.Series(False, index=data.index)
        
        for i in range(period, len(data)):
            prices = data['close'].iloc[i-period:i+1].values
            if all(prices[j] <= prices[j+1] for j in range(len(prices)-1)):
                uptrend.iloc[i] = True
                
        return uptrend
    
    @staticmethod
    def calculate_turnover_rate(data: pd.DataFrame, total_shares: float) -> pd.Series:
        """
        计算换手率
        
        Args:
            data: 股票数据（需包含volume列）
            total_shares: 总股本
            
        Returns:
            换手率序列（百分比）
        """
        return (data['volume'] / total_shares) * 100
    
    @staticmethod
    def detect_ipo_rebound(data: pd.DataFrame, 
                          ipo_date: pd.Timestamp,
                          entry_day: int = 6,
                          min_decline_days: int = 3) -> Tuple[bool, str]:
        """
        检测IPO反包信号
        
        Args:
            data: 股票数据
            ipo_date: IPO上市日期
            entry_day: 介入日期（上市第N天）
            min_decline_days: 最少下跌天数
            
        Returns:
            (是否满足条件, 原因说明)
        """
        if len(data) < entry_day:
            return False, "数据不足"
        
        # 获取上市后的数据
        days_since_ipo = (data.index[-1] - ipo_date).days
        
        if days_since_ipo < entry_day:
            return False, f"未到介入时间窗口（第{entry_day}天）"
        
        # 检查是否经历下跌
        recent_data = data.iloc[-entry_day:]
        decline_days = (recent_data['close'] < recent_data['close'].shift(1)).sum()
        
        if decline_days < min_decline_days:
            return False, f"下跌天数不足（需要{min_decline_days}天）"
        
        # 检查是否出现反包阳线
        last_row = data.iloc[-1]
        prev_row = data.iloc[-2]
        
        # 反包条件：收盘价高于前一日开盘价，或吞没前一日阴线
        is_rebound = (last_row['close'] > prev_row['open']) or \
                     (last_row['close'] > prev_row['close'] and 
                      last_row['open'] < prev_row['close'])
        
        if is_rebound:
            return True, "满足IPO反包条件"
        else:
            return False, "未出现反包阳线"
    
    @staticmethod
    def calculate_macd(data: pd.DataFrame, 
                      fast: int = 12, 
                      slow: int = 26, 
                      signal: int = 9) -> pd.DataFrame:
        """
        计算MACD指标
        
        Args:
            data: 股票数据
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            包含MACD的DataFrame
        """
        result = data.copy()
        
        # 计算EMA
        ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
        
        # MACD线
        result['macd'] = ema_fast - ema_slow
        
        # 信号线
        result['macd_signal'] = result['macd'].ewm(span=signal, adjust=False).mean()
        
        # 柱状图
        result['macd_hist'] = result['macd'] - result['macd_signal']
        
        return result
    
    @staticmethod
    def detect_macd_divergence(data: pd.DataFrame, period: int = 5) -> Tuple[bool, str]:
        """
        检测MACD背离
        
        Args:
            data: 包含MACD的股票数据
            period: 检测周期
            
        Returns:
            (是否背离, 背离类型)
        """
        if 'macd' not in data.columns:
            data = TechnicalIndicators.calculate_macd(data)
        
        recent_data = data.iloc[-period:]
        
        # 顶背离：价格创新高，MACD未创新高
        price_high = recent_data['close'].iloc[-1] == recent_data['close'].max()
        macd_high = recent_data['macd'].iloc[-1] == recent_data['macd'].max()
        
        if price_high and not macd_high:
            return True, "顶背离"
        
        # 底背离：价格创新低，MACD未创新低
        price_low = recent_data['close'].iloc[-1] == recent_data['close'].min()
        macd_low = recent_data['macd'].iloc[-1] == recent_data['macd'].min()
        
        if price_low and not macd_low:
            return True, "底背离"
        
        return False, "无背离"

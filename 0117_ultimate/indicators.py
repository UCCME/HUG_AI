"""
技术指标计算模块
整合了所有策略的技术指标计算方法
"""
import numpy as np
import pandas as pd
import talib
from typing import Tuple, List, Optional
import math


class TechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_ma(data: pd.Series, period: int) -> pd.Series:
        """计算简单移动平均线"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """计算指数移动平均线"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD指标"""
        exp1 = data.ewm(span=fast, adjust=False).mean()
        exp2 = data.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        middle = data.rolling(window=period).mean()
        std_dev = data.rolling(window=period).std()
        upper = middle + std * std_dev
        lower = middle - std * std_dev
        return upper, middle, lower
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """计算ATR（真实波动幅度）"""
        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def calculate_stoch_rsi(close: pd.Series, period: int = 14, k_period: int = 3, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        计算Stochastic RSI指标
        来自StochRSI策略
        """
        # 先计算RSI
        rsi = TechnicalIndicators.calculate_rsi(close, period)
        
        # 将RSI归一化到0-100范围
        stoch_rsi_k = 100 * (rsi - rsi.rolling(period).min()) / (
            rsi.rolling(period).max() - rsi.rolling(period).min())
        
        # 平滑处理
        stoch_rsi_k = stoch_rsi_k.rolling(k_period).mean()
        stoch_rsi_d = stoch_rsi_k.rolling(d_period).mean()
        
        return stoch_rsi_k, stoch_rsi_d
    
    @staticmethod
    def calculate_fisher_transform(high: pd.Series, low: pd.Series, period: int = 10) -> Tuple[pd.Series, pd.Series]:
        """
        计算Fisher变换
        来自StochRSI策略
        """
        median_price = (high + low) / 2
        min_price = median_price.rolling(period).min()
        max_price = median_price.rolling(period).max()
        
        # 归一化到-0.5到0.5
        normalized = 0.66 * ((median_price - min_price) / (max_price - min_price) - 0.5)
        
        # Fisher变换
        fisher = 0.5 * np.log((1 + normalized) / (1 - normalized))
        fisher_signal = fisher.shift(1)
        
        return fisher, fisher_signal
    
    @staticmethod
    def calculate_hma(data: pd.Series, period: int) -> pd.Series:
        """
        计算Hull移动平均线
        来自Lucy策略
        """
        half_length = int(period / 2)
        sqrt_length = int(np.sqrt(period))
        
        wma_half = data.rolling(window=half_length).apply(
            lambda x: np.sum(x * np.arange(1, len(x) + 1)) / np.sum(np.arange(1, len(x) + 1)), raw=True)
        wma_full = data.rolling(window=period).apply(
            lambda x: np.sum(x * np.arange(1, len(x) + 1)) / np.sum(np.arange(1, len(x) + 1)), raw=True)
        
        raw_hma = 2 * wma_half - wma_full
        hma = raw_hma.rolling(window=sqrt_length).apply(
            lambda x: np.sum(x * np.arange(1, len(x) + 1)) / np.sum(np.arange(1, len(x) + 1)), raw=True)
        
        return hma
    
    @staticmethod
    def calculate_zlsma(data: pd.Series, length: int) -> pd.Series:
        """
        计算零延迟移动平均线（Zero Lag SMA）
        来自Lucy策略
        """
        ema_fast = TechnicalIndicators.calculate_ema(data, length // 2)
        ema_slow = TechnicalIndicators.calculate_ema(data, length)
        momentum_rate = (ema_fast - ema_slow) / length
        hull = TechnicalIndicators.calculate_hma(data, length)
        prediction = hull + momentum_rate * (length / 4)
        zlsma_val = prediction * 0.4 + ema_fast * 0.6
        return zlsma_val
    
    @staticmethod
    def calculate_ut_bot_trailing_stop(close: pd.Series, high: pd.Series, low: pd.Series, 
                                       volume: pd.Series, ut_atr_period: int = 10, 
                                       ut_key: float = 1.2) -> pd.Series:
        """
        计算UT Bot追踪止损线
        来自Lucy策略，自适应ATR止损
        """
        # 计算ATR
        atr = TechnicalIndicators.calculate_atr(high, low, close, ut_atr_period)
        
        # 计算动量
        momentum = close.pct_change(5).fillna(0)
        
        # 计算成交量比率
        vol_ratio = volume / volume.rolling(20).mean()
        
        # 自适应关键值
        adaptive_key = ut_key * (1 + np.abs(momentum) * 2) * vol_ratio.apply(
            lambda x: min(1.2, max(0.8, x)))
        
        trail_dist = atr * adaptive_key
        
        # 追踪止损线计算
        trail = pd.Series(index=close.index, dtype=float)
        trail.iloc[0] = close.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > trail.iloc[i - 1]:
                target = close.iloc[i] - trail_dist.iloc[i]
            else:
                target = close.iloc[i] + trail_dist.iloc[i]
            trail.iloc[i] = trail.iloc[i - 1] * 0.7 + target * 0.3
        
        return trail
    
    @staticmethod
    def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        计算VWAP（成交量加权平均价）
        来自Lucy策略
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap
    
    @staticmethod
    def find_swings(high: pd.Series, low: pd.Series, window: int = 3) -> Tuple[List[int], List[int]]:
        """
        检测摆动高点和低点
        来自SMC技术分析工具
        """
        highs, lows = [], []
        
        for i in range(window, len(high) - window):
            local_high = high.iloc[i - window : i + window + 1].max()
            local_low = low.iloc[i - window : i + window + 1].min()
            
            if high.iloc[i] == local_high:
                highs.append(i)
            if low.iloc[i] == local_low:
                lows.append(i)
        
        return highs, lows
    
    @staticmethod
    def detect_bos_ch(df: pd.DataFrame, swing_highs: List[int], swing_lows: List[int]) -> Tuple[List[int], List[int]]:
        """
        检测BOS（Break of Structure）和CH（Change of Character）
        来自SMC技术分析工具
        """
        bos_list, ch_list = [], []
        last_high, last_low = None, None
        last_dir = None
        
        for i in range(len(df)):
            if i in swing_highs:
                if last_high is not None and df['high'].iloc[i] > df['high'].iloc[last_high]:
                    bos_list.append(i)  # 突破前高
                    if last_dir == "down":
                        ch_list.append(i)  # 趋势反转
                    last_dir = "up"
                last_high = i
            
            if i in swing_lows:
                if last_low is not None and df['low'].iloc[i] < df['low'].iloc[last_low]:
                    bos_list.append(i)  # 突破前低
                    if last_dir == "up":
                        ch_list.append(i)  # 趋势反转
                    last_dir = "down"
                last_low = i
        
        return bos_list, ch_list
    
    @staticmethod
    def detect_order_blocks(df: pd.DataFrame, bos_idx: List[int]) -> List[Tuple[int, float, float]]:
        """
        检测订单块（Order Blocks）
        来自SMC技术分析工具
        """
        ob_zones = []
        
        for i in bos_idx:
            if i < 1:
                continue
            
            direction_up = df['close'].iloc[i] > df['open'].iloc[i]
            lookback = range(max(0, i - 10), i)[::-1]
            
            ob_candle = None
            # 寻找BOS前的最后一根反向K线
            for j in lookback:
                up_candle = df['close'].iloc[j] > df['open'].iloc[j]
                if direction_up and not up_candle:
                    ob_candle = j
                    break
                if not direction_up and up_candle:
                    ob_candle = j
                    break
            
            if ob_candle is not None:
                body_high = max(df['open'].iloc[ob_candle], df['close'].iloc[ob_candle])
                body_low = min(df['open'].iloc[ob_candle], df['close'].iloc[ob_candle])
                ob_zones.append((ob_candle, body_low, body_high))
        
        return ob_zones
    
    @staticmethod
    def detect_fvg(df: pd.DataFrame) -> List[Tuple[int, float, float]]:
        """
        检测公允价值缺口（Fair Value Gap）
        来自SMC技术分析工具
        """
        zones = []
        
        for i in range(2, len(df)):
            # 多头缺口
            if df['low'].iloc[i - 1] > df['high'].iloc[i - 2] and df['low'].iloc[i] > df['high'].iloc[i - 2]:
                zones.append((i, df['high'].iloc[i - 2], df['low'].iloc[i]))
            
            # 空头缺口
            if df['high'].iloc[i - 1] < df['low'].iloc[i - 2] and df['high'].iloc[i] < df['low'].iloc[i - 2]:
                zones.append((i, df['high'].iloc[i], df['low'].iloc[i - 2]))
        
        return zones
    
    @staticmethod
    def calculate_volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        """计算成交量比率"""
        volume_ma = volume.rolling(window=period).mean()
        volume_ratio = volume / volume_ma
        return volume_ratio
    
    @staticmethod
    def calculate_price_change(close: pd.Series) -> pd.Series:
        """计算价格变化率"""
        return close.pct_change()
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame, config) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            df: 包含OHLCV数据的DataFrame
            config: 配置对象
        
        Returns:
            添加了所有技术指标的DataFrame
        """
        data = df.copy()
        
        # 基础技术指标
        data[f'MA_{config.FAST_MA_PERIOD}'] = TechnicalIndicators.calculate_ma(data['close'], config.FAST_MA_PERIOD)
        data[f'MA_{config.SLOW_MA_PERIOD}'] = TechnicalIndicators.calculate_ma(data['close'], config.SLOW_MA_PERIOD)
        
        data['RSI'] = TechnicalIndicators.calculate_rsi(data['close'], config.RSI_PERIOD)
        
        macd, macd_signal, macd_hist = TechnicalIndicators.calculate_macd(
            data['close'], config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)
        data['MACD'] = macd
        data['MACD_Signal'] = macd_signal
        data['MACD_Hist'] = macd_hist
        
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(
            data['close'], config.BB_PERIOD, config.BB_STD)
        data['BB_Upper'] = bb_upper
        data['BB_Middle'] = bb_middle
        data['BB_Lower'] = bb_lower
        
        data['ATR'] = TechnicalIndicators.calculate_atr(
            data['high'], data['low'], data['close'], config.ATR_PERIOD)
        
        # 高级指标
        stoch_k, stoch_d = TechnicalIndicators.calculate_stoch_rsi(
            data['close'], config.STOCH_RSI_PERIOD, config.STOCH_K_PERIOD, config.STOCH_D_PERIOD)
        data['StochRSI_K'] = stoch_k
        data['StochRSI_D'] = stoch_d
        
        fisher, fisher_signal = TechnicalIndicators.calculate_fisher_transform(
            data['high'], data['low'], 10)
        data['Fisher'] = fisher
        data['Fisher_Signal'] = fisher_signal
        
        data['ZLSMA'] = TechnicalIndicators.calculate_zlsma(data['close'], config.FAST_MA_PERIOD)
        
        data['UT_Bot_Stop'] = TechnicalIndicators.calculate_ut_bot_trailing_stop(
            data['close'], data['high'], data['low'], data['volume'], 
            config.UT_ATR_PERIOD, config.UT_KEY_VALUE)
        
        data['VWAP'] = TechnicalIndicators.calculate_vwap(
            data['high'], data['low'], data['close'], data['volume'])
        
        # 成交量指标
        data['Volume_MA'] = data['volume'].rolling(window=20).mean()
        data['Volume_Ratio'] = TechnicalIndicators.calculate_volume_ratio(data['volume'])
        data['Price_Change'] = TechnicalIndicators.calculate_price_change(data['close'])
        
        return data

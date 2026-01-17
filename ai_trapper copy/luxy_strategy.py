"""
Luxy Momentum Trading Strategy
基于Pine Script Luxy Momentum V7策略的Python实现

核心特点：
1. UT Bot动态追踪止损系统
2. R-multiple固定盈亏比止盈
3. SuperTrend趋势确认
4. ADX趋势强度过滤
5. 成交量过滤
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
from enum import Enum
from luxy_config import LuxyConfig


class SignalType(Enum):
    """信号类型"""
    BUY = 1
    SELL = -1
    HOLD = 0


class Signal:
    """交易信号"""
    def __init__(self, signal_type: SignalType, confidence: float, price: float, timestamp):
        self.signal_type = signal_type
        self.confidence = confidence
        self.price = price
        self.timestamp = timestamp
        
    def __repr__(self):
        return f"Signal({self.signal_type.name}, conf={self.confidence:.2f}, price={self.price:.2f})"


class Position:
    """持仓信息"""
    def __init__(self, entry_price: float, entry_time, direction: int, size: float, 
                 stop_loss: float, initial_risk: float):
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.direction = direction  # 1=多头, -1=空头
        self.size = size
        self.stop_loss = stop_loss
        self.initial_risk = initial_risk  # R值
        
        # R-multiple止盈位
        self.tp1_price = None
        self.tp2_price = None
        self.tp3_price = None
        
        # 剩余仓位
        self.remaining_size = size
        
        # 追踪止损
        self.trailing_stop = stop_loss
        self.trailing_activated = False
        
    def calculate_pnl(self, current_price: float) -> float:
        """计算当前盈亏"""
        if self.direction == 1:  # 多头
            return (current_price - self.entry_price) * self.remaining_size
        else:  # 空头
            return (self.entry_price - current_price) * self.remaining_size
    
    def calculate_pnl_pct(self, current_price: float) -> float:
        """计算盈亏百分比"""
        if self.direction == 1:
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price
    
    def get_r_multiple(self, current_price: float) -> float:
        """计算当前R倍数"""
        pnl = self.calculate_pnl(current_price) / self.remaining_size
        return pnl / self.initial_risk if self.initial_risk > 0 else 0


class LuxyStrategy:
    """Luxy Momentum策略"""
    
    def __init__(self, config: LuxyConfig = None):
        self.config = config or LuxyConfig()
        self.position: Optional[Position] = None
        self.trades_history = []
        
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算ATR (Average True Range)
        
        Args:
            data: OHLC数据
            period: ATR周期
            
        Returns:
            ATR序列
        """
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # True Range = max(H-L, |H-PC|, |L-PC|)
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_supertrend(self, data: pd.DataFrame, period: int = 10, 
                            multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """
        计算SuperTrend指标
        
        Args:
            data: OHLC数据
            period: ATR周期
            multiplier: ATR倍数
            
        Returns:
            (supertrend值, 方向)
        """
        atr = self.calculate_atr(data, period)
        hl_avg = (data['High'] + data['Low']) / 2
        
        # 基础带
        upper_band = hl_avg + multiplier * atr
        lower_band = hl_avg - multiplier * atr
        
        # SuperTrend计算
        supertrend = pd.Series(index=data.index, dtype=float)
        direction = pd.Series(index=data.index, dtype=int)
        
        for i in range(1, len(data)):
            if pd.isna(atr.iloc[i]):
                continue
                
            # 初始化
            if i == 1 or pd.isna(supertrend.iloc[i-1]):
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
                continue
            
            # 更新SuperTrend
            if direction.iloc[i-1] == 1:  # 上涨趋势
                supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1])
                if data['Close'].iloc[i] <= supertrend.iloc[i]:
                    direction.iloc[i] = -1
                    supertrend.iloc[i] = upper_band.iloc[i]
                else:
                    direction.iloc[i] = 1
            else:  # 下跌趋势
                supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1])
                if data['Close'].iloc[i] >= supertrend.iloc[i]:
                    direction.iloc[i] = 1
                    supertrend.iloc[i] = lower_band.iloc[i]
                else:
                    direction.iloc[i] = -1
        
        return supertrend, direction
    
    def calculate_adx(self, data: pd.DataFrame, period: int = 14, 
                     smoothing: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算ADX (Average Directional Index)
        
        Args:
            data: OHLC数据
            period: DI计算周期
            smoothing: ADX平滑周期
            
        Returns:
            (+DI, -DI, ADX)
        """
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # 计算+DM和-DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # 当+DM和-DM都>0时，只保留较大的那个
        plus_dm[(plus_dm > 0) & (minus_dm > 0) & (plus_dm <= minus_dm)] = 0
        minus_dm[(plus_dm > 0) & (minus_dm > 0) & (minus_dm < plus_dm)] = 0
        
        # ATR
        atr = self.calculate_atr(data, period)
        
        # 平滑+DM和-DM
        plus_dm_smooth = plus_dm.rolling(window=period).mean()
        minus_dm_smooth = minus_dm.rolling(window=period).mean()
        
        # 计算+DI和-DI
        plus_di = 100 * (plus_dm_smooth / atr)
        minus_di = 100 * (minus_dm_smooth / atr)
        
        # 计算DX和ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.rolling(window=smoothing).mean()
        
        return plus_di, minus_di, adx
    
    def calculate_ut_bot(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算UT Bot动态追踪止损
        
        基于Pine Script实现：
        - adaptiveKey = utKey × (1 + |momentum| × 2) × volRatio
        - 平滑追踪止损更新
        
        Returns:
            (trailing_stop, signal, volume_ratio)
        """
        close = data['Close']
        volume = data['Volume']
        
        # 计算momentum
        momentum = close.pct_change(5)
        
        # 计算成交量比率
        volume_ma = volume.rolling(window=self.config.VOLUME_MA_PERIOD).mean()
        vol_ratio = volume / volume_ma
        vol_ratio = vol_ratio.clip(0.8, 1.2)  # 限制在0.8-1.2范围
        
        # 计算ATR
        atr = self.calculate_atr(data, self.config.UT_ATR_PERIOD)
        
        # 计算自适应key
        adaptive_key = self.config.UT_KEY_VALUE * (1 + momentum.abs() * 2) * vol_ratio
        adaptive_key = adaptive_key.fillna(self.config.UT_KEY_VALUE)
        
        # 计算追踪距离
        trail_dist = atr * adaptive_key
        
        # 初始化追踪止损
        trailing_stop = pd.Series(index=data.index, dtype=float)
        ut_signal = pd.Series(index=data.index, dtype=int)  # 1=多头, -1=空头
        
        for i in range(1, len(data)):
            if pd.isna(trail_dist.iloc[i]):
                continue
            
            # 目标追踪止损
            if i == 1 or pd.isna(trailing_stop.iloc[i-1]):
                if close.iloc[i] > close.iloc[i-1]:
                    target_trail = close.iloc[i] - trail_dist.iloc[i]
                else:
                    target_trail = close.iloc[i] + trail_dist.iloc[i]
            else:
                prev_stop = trailing_stop.iloc[i-1]
                if close.iloc[i] > prev_stop:
                    target_trail = close.iloc[i] - trail_dist.iloc[i]
                else:
                    target_trail = close.iloc[i] + trail_dist.iloc[i]
            
            # 平滑更新（指数平滑）
            if i == 1 or pd.isna(trailing_stop.iloc[i-1]):
                trailing_stop.iloc[i] = target_trail
            else:
                smoothing = self.config.UT_SMOOTHING
                trailing_stop.iloc[i] = (trailing_stop.iloc[i-1] * (1 - smoothing) + 
                                        target_trail * smoothing)
            
            # 生成信号
            if i >= 1:
                # 上穿追踪线 = 买入信号
                if (close.iloc[i] > trailing_stop.iloc[i] and 
                    close.iloc[i-1] <= trailing_stop.iloc[i-1] and 
                    vol_ratio.iloc[i] >= self.config.UT_VOLUME_THRESHOLD):
                    ut_signal.iloc[i] = 1
                # 下穿追踪线 = 卖出信号
                elif (close.iloc[i] < trailing_stop.iloc[i] and 
                      close.iloc[i-1] >= trailing_stop.iloc[i-1] and 
                      vol_ratio.iloc[i] >= self.config.UT_VOLUME_THRESHOLD):
                    ut_signal.iloc[i] = -1
                else:
                    ut_signal.iloc[i] = 0
        
        return trailing_stop, ut_signal, vol_ratio
    
    def calculate_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            data: OHLC数据
            
        Returns:
            添加了所有指标的DataFrame
        """
        df = data.copy()
        
        print("计算技术指标...")
        
        # 1. ATR
        df['ATR'] = self.calculate_atr(df, self.config.ATR_PERIOD)
        
        # 2. SuperTrend
        st_val, st_dir = self.calculate_supertrend(
            df, 
            self.config.ST_ATR_PERIOD, 
            self.config.ST_MULTIPLIER
        )
        df['SuperTrend'] = st_val
        df['ST_Direction'] = st_dir
        
        # 3. ADX
        plus_di, minus_di, adx = self.calculate_adx(
            df, 
            self.config.ADX_PERIOD, 
            self.config.ADX_SMOOTHING
        )
        df['Plus_DI'] = plus_di
        df['Minus_DI'] = minus_di
        df['ADX'] = adx
        
        # 4. UT Bot
        ut_stop, ut_sig, vol_ratio = self.calculate_ut_bot(df)
        df['UT_Stop'] = ut_stop
        df['UT_Signal'] = ut_sig
        df['Volume_Ratio'] = vol_ratio
        
        # 5. 移动平均线
        df[f'MA_{self.config.MA_FAST}'] = df['Close'].rolling(
            window=self.config.MA_FAST
        ).mean()
        df[f'MA_{self.config.MA_SLOW}'] = df['Close'].rolling(
            window=self.config.MA_SLOW
        ).mean()
        
        # 删除NaN值
        df = df.dropna()
        
        print(f"✅ 指标计算完成，有效数据: {len(df)} 条")
        
        return df
    
    def generate_signal(self, data: pd.DataFrame, index: int) -> Signal:
        """
        生成交易信号
        
        策略逻辑：
        1. UT Bot信号（核心）
        2. SuperTrend确认
        3. ADX过滤（趋势强度）
        4. 成交量过滤
        5. 均线过滤
        
        Args:
            data: 包含所有指标的数据
            index: 当前索引
            
        Returns:
            Signal对象
        """
        if index < 1:
            return Signal(SignalType.HOLD, 0.0, data['Close'].iloc[index], data.index[index])
        
        row = data.iloc[index]
        prev_row = data.iloc[index-1]
        
        # 1. UT Bot信号（必须）
        ut_signal = row['UT_Signal']
        
        if ut_signal == 0:
            return Signal(SignalType.HOLD, 0.0, row['Close'], row.name)
        
        # 2. SuperTrend确认
        st_direction = row['ST_Direction']
        
        # 3. ADX过滤（趋势强度）
        adx_ok = True
        if self.config.ENABLE_ADX_FILTER:
            adx_ok = row['ADX'] >= self.config.MIN_ADX
        
        # 4. 成交量过滤
        volume_ok = True
        if self.config.ENABLE_VOLUME_FILTER:
            volume_ok = row['Volume_Ratio'] >= self.config.MIN_VOLUME_RATIO
        
        # 5. 均线过滤
        ma_ok = True
        if self.config.ENABLE_MA_FILTER:
            ma_fast = row[f'MA_{self.config.MA_FAST}']
            ma_slow = row[f'MA_{self.config.MA_SLOW}']
            if ut_signal == 1:  # 买入信号
                ma_ok = ma_fast > ma_slow and row['Close'] > ma_fast
            else:  # 卖出信号
                ma_ok = ma_fast < ma_slow and row['Close'] < ma_fast
        
        # 计算信号置信度
        confidence = 0.0
        
        if ut_signal == 1:  # 买入信号
            # UT Bot买入 + SuperTrend多头
            if st_direction == 1:
                confidence += 0.4
            
            # ADX通过
            if adx_ok:
                confidence += 0.3
            
            # 成交量通过
            if volume_ok:
                confidence += 0.2
            
            # 均线通过
            if ma_ok:
                confidence += 0.1
            
            # 所有条件都满足
            if st_direction == 1 and adx_ok and volume_ok and ma_ok:
                signal_type = SignalType.BUY
            else:
                signal_type = SignalType.HOLD
                confidence = 0.0
                
        elif ut_signal == -1 and self.config.ENABLE_SHORT:  # 卖出信号
            # UT Bot卖出 + SuperTrend空头
            if st_direction == -1:
                confidence += 0.4
            
            # ADX通过
            if adx_ok:
                confidence += 0.3
            
            # 成交量通过
            if volume_ok:
                confidence += 0.2
            
            # 均线通过
            if ma_ok:
                confidence += 0.1
            
            # 所有条件都满足
            if st_direction == -1 and adx_ok and volume_ok and ma_ok:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
                confidence = 0.0
        else:
            signal_type = SignalType.HOLD
            confidence = 0.0
        
        return Signal(signal_type, confidence, row['Close'], row.name)
    
    def calculate_stop_loss(self, data: pd.DataFrame, index: int, 
                           entry_price: float, direction: int) -> float:
        """
        计算止损位（ATR动态止损）
        
        Args:
            data: 数据
            index: 当前索引
            entry_price: 入场价格
            direction: 方向（1=多头, -1=空头）
            
        Returns:
            止损价格
        """
        atr = data['ATR'].iloc[index]
        
        if direction == 1:  # 多头
            stop_loss = entry_price - atr * self.config.ATR_SL_MULTIPLIER
            
            # 限制止损范围
            min_sl = entry_price * (1 - self.config.MAX_STOP_LOSS_PCT)
            max_sl = entry_price * (1 - self.config.MIN_STOP_LOSS_PCT)
            stop_loss = max(min_sl, min(max_sl, stop_loss))
            
        else:  # 空头
            stop_loss = entry_price + atr * self.config.ATR_SL_MULTIPLIER
            
            # 限制止损范围
            max_sl = entry_price * (1 + self.config.MAX_STOP_LOSS_PCT)
            min_sl = entry_price * (1 + self.config.MIN_STOP_LOSS_PCT)
            stop_loss = min(max_sl, max(min_sl, stop_loss))
        
        return stop_loss
    
    def calculate_take_profit_levels(self, entry_price: float, stop_loss: float, 
                                    direction: int) -> Tuple[float, float, float]:
        """
        计算R-multiple止盈位
        
        Args:
            entry_price: 入场价格
            stop_loss: 止损价格
            direction: 方向
            
        Returns:
            (TP1, TP2, TP3)
        """
        # 计算初始风险R
        initial_risk = abs(entry_price - stop_loss)
        
        if direction == 1:  # 多头
            tp1 = entry_price + initial_risk * self.config.TP1_R_MULTIPLE
            tp2 = entry_price + initial_risk * self.config.TP2_R_MULTIPLE
            tp3 = entry_price + initial_risk * self.config.TP3_R_MULTIPLE
        else:  # 空头
            tp1 = entry_price - initial_risk * self.config.TP1_R_MULTIPLE
            tp2 = entry_price - initial_risk * self.config.TP2_R_MULTIPLE
            tp3 = entry_price - initial_risk * self.config.TP3_R_MULTIPLE
        
        return tp1, tp2, tp3
    
    def check_exit_conditions(self, data: pd.DataFrame, index: int, 
                            position: Position) -> Tuple[bool, str, float]:
        """
        检查是否应该平仓
        
        Returns:
            (should_exit, reason, exit_size)
        """
        current_price = data['Close'].iloc[index]
        
        # 1. 止损
        if position.direction == 1:  # 多头
            if current_price <= position.trailing_stop:
                return True, "止损", position.remaining_size
        else:  # 空头
            if current_price >= position.trailing_stop:
                return True, "止损", position.remaining_size
        
        # 2. R-multiple止盈
        if self.config.ENABLE_R_MULTIPLE:
            if position.direction == 1:  # 多头
                # TP3
                if position.tp3_price and current_price >= position.tp3_price:
                    return True, "TP3止盈", position.remaining_size
                # TP2
                if position.tp2_price and current_price >= position.tp2_price:
                    if position.remaining_size > position.size * (self.config.TP3_SIZE):
                        return True, "TP2止盈", position.size * self.config.TP2_SIZE
                # TP1
                if position.tp1_price and current_price >= position.tp1_price:
                    if position.remaining_size == position.size:
                        return True, "TP1止盈", position.size * self.config.TP1_SIZE
            else:  # 空头
                # TP3
                if position.tp3_price and current_price <= position.tp3_price:
                    return True, "TP3止盈", position.remaining_size
                # TP2
                if position.tp2_price and current_price <= position.tp2_price:
                    if position.remaining_size > position.size * (self.config.TP3_SIZE):
                        return True, "TP2止盈", position.size * self.config.TP2_SIZE
                # TP1
                if position.tp1_price and current_price <= position.tp1_price:
                    if position.remaining_size == position.size:
                        return True, "TP1止盈", position.size * self.config.TP1_SIZE
        
        # 3. 反向信号（仅强反向信号才平仓）
        ut_signal = data['UT_Signal'].iloc[index]
        st_direction = data['ST_Direction'].iloc[index]
        
        if position.direction == 1:  # 多头持仓
            # UT Bot卖出信号 + SuperTrend转空
            if ut_signal == -1 and st_direction == -1:
                return True, "强反向信号", position.remaining_size
        else:  # 空头持仓
            # UT Bot买入信号 + SuperTrend转多
            if ut_signal == 1 and st_direction == 1:
                return True, "强反向信号", position.remaining_size
        
        # 4. 更新追踪止损（当盈利≥1.5R时激活）
        r_multiple = position.get_r_multiple(current_price)
        if r_multiple >= self.config.TRAILING_STOP_ACTIVATION:
            if not position.trailing_activated:
                position.trailing_activated = True
                if self.config.VERBOSE:
                    print(f"  ✓ 追踪止损已激活 (R={r_multiple:.2f})")
            
            # 更新追踪止损（只能向有利方向移动）
            ut_stop = data['UT_Stop'].iloc[index]
            if position.direction == 1:  # 多头
                new_trailing = max(position.trailing_stop, ut_stop)
                if new_trailing > position.trailing_stop:
                    position.trailing_stop = new_trailing
            else:  # 空头
                new_trailing = min(position.trailing_stop, ut_stop)
                if new_trailing < position.trailing_stop:
                    position.trailing_stop = new_trailing
        
        return False, "", 0.0
    
    def __repr__(self):
        return f"LuxyStrategy(config={self.config.__class__.__name__})"


if __name__ == '__main__':
    # 测试策略初始化
    config = LuxyConfig()
    strategy = LuxyStrategy(config)
    
    print("Luxy策略初始化成功！")
    print(strategy)
    config.print_config()

"""
lucy_utils.py - 工具函数库，用于 Lucy 交易策略
包含 EMA、SMA、ATR、RSI、MACD、ZLSMA、UT Bot 相关指标和信号函数
"""

import pandas as pd
import numpy as np


def ema(series, length):
    """计算指数移动平均线 (EMA)"""
    return pd.Series(series).ewm(span=length, adjust=False).mean().values


def sma(series, length):
    """计算简单移动平均线 (SMA)"""
    return pd.Series(series).rolling(length).mean().values

def wma(series, length):
    w = np.arange(1, length+1)
    return pd.Series(series).rolling(length).apply(lambda x: np.dot(x, w) / w.sum(), raw=True).values

def vwma(price, volume, n):
    price = pd.Series(price)
    volume = pd.Series(volume)
    pv = price * volume
    return pv.rolling(n).sum() / volume.rolling(n).sum()

def rma(series, length):
    return pd.Series(series).ewm(alpha=1/length, adjust=False).mean().values 

def hma(series, length):
    """计算 Hull 移动平均线 (HMA)"""
    series = pd.Series(series)
    half = length // 2
    sqrt_len = int(np.sqrt(length))

    def wma(series, length):
        weights = np.arange(1, length + 1)
        return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    wma_half = wma(series, half)
    wma_full = wma(series, length)

    diff = 2 * wma_half - wma_full
    hma = wma(diff, sqrt_len)
    return hma.values


def atr(high, low, close, length=14):
    """
    计算平均真实波幅 (ATR)
    使用 Wilder 平滑方法（类似 RMA）
    """
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    true_range.iloc[0] = high.iloc[0] - low.iloc[0]

    # 使用 EWM 实现 RMA
    rma = true_range.ewm(alpha=1/length, adjust=False).mean()
    return rma.values


def rsi(series, length):
    """计算相对强弱指数 (RSI)"""
    series = pd.Series(series)
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(length).mean()
    avg_loss = loss.rolling(length).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.values


def macd(series, fast=12, slow=26, signal=9):
    """计算 MACD 指标"""
    series = pd.Series(series)
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)

    macd_line = ema_fast - ema_slow
    signal_line = ema(pd.Series(macd_line), signal)
    hist = pd.Series(macd_line) - pd.Series(signal_line)

    return macd_line, signal_line, hist.values


def maDistanceOk(ma_fast, ma_medium):
    return ((pd.Series(ma_fast) - pd.Series(ma_medium)).abs() / pd.Series(ma_medium) * 100 > 0.2).values


def macdSepOk(macd, macd_signal, atr):
    return ((pd.Series(macd) - pd.Series(macd_signal)).abs() > pd.Series(atr) * 0.1).values 


def zlsma(series, length):
    """计算零延迟移动平均线 (ZLSMA)"""
    ema_fast = ema(series, length // 2)
    ema_slow = ema(series, length)

    momentum_rate = (pd.Series(ema_fast) - pd.Series(ema_slow)) / length

    hull = hma(series, length)

    prediction = pd.Series(hull) + momentum_rate * (length / 4)
    zlsma_val = prediction * 0.4 + pd.Series(ema_fast) * 0.6

    return zlsma_val.values


def wma(series, length):
    """计算加权移动平均线 (WMA)"""
    series = pd.Series(series)
    weights = np.arange(1, length + 1)
    wma = series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    return wma.values


def ma_distance_check(ma_fast, ma_medium):
    """检查均线距离是否合适"""
    ma_distance = abs(ma_fast - ma_medium) / ma_medium * 100
    return ma_distance > 0.2


def macd_separation_check(macd_line, signal_line, atr):
    """检查 MACD 分离度是否足够"""
    macd_sep = abs(macd_line - signal_line)
    return macd_sep > atr * 0.1


def ut_bot_trailing_stop(close, high, low, volume, ut_atr_period, ut_key=1.2):
    """计算 UT Bot 追踪止损线"""
    atr1 = atr(high, low, close, ut_atr_period)

    momentum = pd.Series(close).pct_change(5).fillna(0)
    vol_ratio = pd.Series(volume) / pd.Series(volume).rolling(20).mean()

    adaptive_key = ut_key * (1 + np.abs(momentum) * 2) * vol_ratio.apply(lambda x: min(1.2, x)).apply(lambda x: max(0.8, x))
    trail_dist = atr1 * adaptive_key.values

    trail = np.zeros(len(close))
    trail[0] = close[0]

    for i in range(1, len(close)):
        if close[i] > trail[i - 1]:
            target = close[i] - trail_dist[i]
        else:
            target = close[i] + trail_dist[i]
        trail[i] = trail[i - 1] * 0.7 + target * 0.3
        trail[i] = close[i] if np.isnan(trail[i]) else trail[i]

    return trail


def vwap(srcVWAP, volume):
    """计算成交量加权平均价格 (VWAP)"""
    sum_pv = 0.0
    sum_v  = 0.0

    vwap = []

    vol_sma20 = pd.Series(volume).rolling(20).mean()

    for i in range(len(srcVWAP)):
        p = srcVWAP[i]
        v = volume[i]
        volume_filtered = v if v > vol_sma20.iloc[i] * 0.1 else 0.0

        sum_pv = p * volume_filtered
        sum_v  = volume_filtered

        vwap.append(sum_pv / sum_v if sum_v > 0 else np.nan)
    
    return vwap

def vwoklong(close, vwap):
    """计算 VWAP 多头确认信号"""
    close = pd.Series(close)
    vwap = pd.Series(vwap)

    vwoklong = (close > vwap)
    return vwoklong.values

def vwokshort(close, vwap):
    """计算 VWAP 空头确认信号"""
    close = pd.Series(close)
    vwap = pd.Series(vwap)

    vwokshort = (close < vwap)
    return vwokshort.values


def ut_bot_buy_signal(close, ut_trailing_stop, zlsma):
    """计算 UT Bot 买入信号"""
    close = pd.Series(close)
    ut_trailing_stop = pd.Series(ut_trailing_stop)
    zlsma = pd.Series(zlsma)

    ut_buy = (
        (close > ut_trailing_stop) &
        (close.shift() <= ut_trailing_stop.shift()) &
        (close > zlsma)
    )
    return ut_buy.values


def ut_bot_sell_signal(close, ut_trailing_stop, zlsma):
    """计算 UT Bot 卖出信号"""
    close = pd.Series(close)
    ut_trailing_stop = pd.Series(ut_trailing_stop)
    zlsma = pd.Series(zlsma)

    ut_sell = (
        (close < ut_trailing_stop) &
        (close.shift() >= ut_trailing_stop.shift()) &
        (close < zlsma)
    )
    return ut_sell.values

def _crossover(a, b):
    a = pd.Series(a)
    b = pd.Series(b)
    return (a.shift(1) <= b.shift(1)) & (a > b)

def _crossunder(a, b):
    a = pd.Series(a)
    b = pd.Series(b)
    return (a.shift(1) >= b.shift(1)) & (a < b)


def longCond_base(ma_structure_bullish, vwOkLong, macdSepOk, maDistanceOk, close, open):
    return (
            pd.Series(ma_structure_bullish) &
            pd.Series(vwOkLong) &
            pd.Series(macdSepOk) &
            pd.Series(maDistanceOk) &
            (pd.Series(close) > pd.Series(open)) 
            # (data['macd'] <= 0)
        ).values

def shortCond_base(ma_structure_bearish, vwOkShort, macdSepOk, maDistanceOk, close, open):
    return (
            pd.Series(ma_structure_bearish) &
            pd.Series(vwOkShort) &
            pd.Series(macdSepOk) &
            pd.Series(maDistanceOk) &
            (pd.Series(close) < pd.Series(open)) 
            # (data['macd'] <= 0)
        ).values

def close_gt_open(close, open):
    return (pd.Series(close) > pd.Series(open)).values

def close_lt_open(close, open):
    return (pd.Series(close) < pd.Series(open)).values

def run_lucy_strategy(data
                      # 策略参数
                        # MACD参数
                        ,macd_fast = 12
                        ,macd_slow = 26
                        ,macd_signal = 9
                        
                        # 移动平均线参数
                        ,ma_short_len = 10
                        ,ma_med_len = 20
                        ,ma_long_len = 200

                        # ATR参数
                        ,atr_period = 14
                        
                        # Supertrend参数
                        ,st_atr_period = 10
                        ,st_multiplier = 2.0
                        
                        # RSI参数
                        ,rsi_period = 14
                        ,rsi_buy_min = 40.0
                        ,rsi_buy_max = 55.0
                        ,rsi_sell_min = 45.0
                        ,rsi_sell_max = 60.0
                        
                        # ZLSMA参数
                        ,zlsma_length = 75
                        
                        # UT Bot参数
                        ,ut_atr_period = 7
                        ,ut_key = 1.2 
                        
                        # 风险管理参数
                        ,sl_percent = 0.1  # 止损百分比
                        ,tp_percent = 0.3  # 止盈百分比
                        ,min_volatility = 0.001  # 最小波动率过滤
                        ,min_hold_period = 2  # 最小持仓周期（T+1）
                        ,signal_delay = 1     # 信号延迟执行天数
                        ):
    
        """初始化策略指标"""
        # 获取价格数据
        close = data.Close.values
        high = data.High.values
        low = data.Low.values
        open = data.Open.values
        volume = data.Volume.values
        
        data = data.copy()

        # 计算移动平均线
        ma_fast = ema(close, ma_short_len)
        data['ma_fast'] = ma_fast
        
        ma_medium = ema(close, ma_med_len)
        data['ma_medium'] = ma_medium

        data['ma_long'] = sma(close, ma_long_len)

        # 计算MACD
        macd_line, macd_signal_line, macd_hist = macd(close, macd_fast, macd_slow, macd_signal)
        data['macd_line'] = macd_line
        data['macd_signal_line'] = macd_signal_line
        data['macd_hist'] = macd_hist
        
        # 计算ATR
        atr_ = atr(high, low, close, atr_period)
        data['atr'] = atr_

        # 计算RSI
        data['rsi'] = rsi(close, rsi_period)
        
        # 计算ZLSMA
        zlsma_ = zlsma(close, zlsma_length)
        data['zlsma'] = zlsma_
        
        # 计算UT Bot追踪止损线
        ut_trailing_stop = ut_bot_trailing_stop(close, high, low, volume, ut_atr_period, ut_key)
        data['ut_trailing_stop'] = ut_trailing_stop
        
        # 计算均线距离和MACD分离度条件
        data['ma_distance_ok'] = ma_distance_check(ma_fast, ma_medium)
        data['macd_sep_ok'] = macd_separation_check(macd_line, macd_signal_line, atr_)

        # 计算UT Bot买卖信号
        data['ut_buy'] = ut_bot_buy_signal(close, ut_trailing_stop, zlsma_)
        data['ut_sell'] = ut_bot_sell_signal(close, ut_trailing_stop, zlsma_)
        
        # # 用于跟踪持仓信息
        # entry_bar = None
        # pending_buy_signal = False  # 待执行的买入信号
        # pending_sell_signal = False  # 待执行的卖出信号(仅平仓)
        # signal_bar = None  # 信号产生时的K线编号

        """执行策略逻辑"""
                    
        # 波动率过滤
        volatility = data['atr'] / data['Close']
        # if volatility < min_volatility:
        data['volatility'] = volatility < min_volatility
        
        # === 趋势判断系统 ===
        data['hlc3'] = (data['High'] + data['Low'] + data['Close']) / 3

        # 均线结构趋势
        data['ma_structure_bullish'] = _crossover(data['ma_fast'], data['ma_medium'])
        data['ma_structure_bearish'] = _crossunder(data['ma_fast'], data['ma_medium'])

        # # MACD动能趋势
        # data['macd_bullish'] = data['macd_line'][-1] > data['macd_signal_line'][-1]
        # data['macd_bearish'] = data['macd_line'][-1] < data['macd_signal_line'][-1]

        # vwOk相关
        data['vwap'] = vwap(data['hlc3'], volume)
        data['vwOkLong'] = vwoklong(close, data['vwap'].values)
        data['vwOkShort'] = vwokshort(close, data['vwap'].values)

        # # 均线距离和MACD分离度检查
        # ma_distance_ok = data['ma_distance_ok'][-1]
        # macd_sep_ok = data['macd_sep_ok'][-1]
        data['maDistanceOk'] = maDistanceOk(ma_fast, ma_medium)
        data['macdSepOk'] = macdSepOk(macd_line, macd_signal_line, atr_)
        
        # # RSI过滤
        # rsi_buy_idx = data[(data['rsi'] >= rsi_buy_min) & (data['rsi'] <= rsi_buy_max)].index
        # data.loc[rsi_buy_idx, 'rsi_buy_zone'] = True
        # data['rsi_buy_zone'] = data['rsi_buy_zone'].fillna(False)

        # rsi_sell_idx = data[(data['rsi'] < rsi_sell_min) | (data['rsi'] > rsi_sell_max)].index
        # data.loc[rsi_sell_idx, 'rsi_sell_zone'] = True
        # data['rsi_sell_zone'] = data['rsi_sell_zone'].fillna(False)
        
        
        # # 综合基础信号
        # base_long = (
        #     ma_structure_bullish and 
        #     ma_distance_ok and 
        #     macd_sep_ok and 
        #     macd_bullish and 
        #     rsi_buy_zone
        # )
        
        # base_short = (
        #     ma_structure_bearish and 
        #     ma_distance_ok and 
        #     macd_sep_ok and 
        #     macd_bearish and 
        #     rsi_sell_zone
        # )
        
        # === 交易信号系统 ===
        # # UT Bot信号
        # ut_buy_signal = self.ut_buy[-1]
        # ut_sell_signal = self.ut_sell[-1]

        data['longCond_base'] = (
            data['ma_structure_bullish'] &
            data['vwOkLong'] &
            data['macdSepOk'] &
            data['maDistanceOk'] &
            (data['Close'] > data['Open']) 
        )
        
        data['longCond_base'] = longCond_base(
            data['ma_structure_bullish'].values,
            data['vwOkLong'].values,
            data['macdSepOk'].values,
            data['maDistanceOk'].values,
            data['Close'].values,
            data['Open'].values
        )

        data['shortCond_base'] = shortCond_base(
            data['ma_structure_bearish'].values,
            data['vwOkShort'].values,
            data['macdSepOk'].values,
            data['maDistanceOk'].values,
            data['Close'].values,
            data['Open'].values
        )
        
        return data 



"""
Lucy Strategy for Backtesting.py library.

This strategy implements the Lucy trading strategy compatible with the backtesting.py framework.
The strategy separates trend detection and trading signal generation.
"""

import pandas as pd
import numpy as np
from backtesting import Strategy
from backtesting.lib import crossover
import talib


class LucyStrategy(Strategy):
    # 策略参数
    # MACD参数
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    
    # 移动平均线参数
    ma_short_len = 10
    ma_med_len = 20
    ma_long_len = 200
    
    # ATR参数
    atr_period = 14
    
    # RSI参数
    rsi_period = 14
    rsi_buy_min = 40.0
    rsi_buy_max = 55.0
    rsi_sell_min = 45.0
    rsi_sell_max = 60.0
    
    # ZLSMA参数
    zlsma_length = 75
    
    # UT Bot参数
    ut_atr_period = 7
    ut_key = 1.2 
    
    # 海龟交易法参数
    turtle_atr_period = 20  # 海龟交易法ATR周期
    turtle_risk_percent = 0.01  # 每次交易风险占总资金的百分比
    turtle_volatility_factor = 2.0  # 波动性因子
    
    # 风险管理参数
    sl_percent = 0.2  # 止损百分比
    tp_percent = 0.5  # 止盈百分比
    min_volatility = 0.001  # 最小波动率过滤
    min_hold_period = 2  # 最小持仓周期（T+1）
    signal_delay = 1     # 信号延迟执行天数
    
    def init(self):
        """初始化策略指标"""
        # 获取价格数据
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        open = self.data.Open
        volume = self.data.Volume
        
        # 计算移动平均线
        self.ma_fast = self.I(ema, close, self.ma_short_len)
        self.ma_medium = self.I(ema, close, self.ma_med_len)
        self.ma_long = self.I(sma, close, self.ma_long_len)
        
        # 计算MACD
        self.macd_line, self.macd_signal_line, self.macd_hist = self.I(
            macd, close, self.macd_fast, self.macd_slow, self.macd_signal)
        
        # 计算ATR
        self.atr = self.I(atr, high, low, close, self.atr_period)
        
        # 计算RSI
        self.rsi = self.I(rsi, close, self.rsi_period)
        
        # 计算ZLSMA
        self.zlsma = self.I(zlsma, close, self.zlsma_length)
        
        # 计算UT Bot追踪止损线
        self.ut_trailing_stop = self.I(ut_bot_trailing_stop, close, high, low, volume,
                                     self.ut_atr_period, self.ut_key)
        
        # 计算均线距离和MACD分离度条件
        self.ma_distance_ok = self.I(ma_distance_check, self.ma_fast, self.ma_medium)
        self.macd_sep_ok = self.I( macd_separation_check, self.macd_line, self.macd_signal_line, self.atr)
        
        # 计算用于海龟交易法的ATR
        self.turtle_atr = self.I(atr, high, low, close, self.turtle_atr_period)
        
        # 计算UT Bot买卖信号
        self.ut_buy = self.I( ut_bot_buy_signal, close, self.ut_trailing_stop, self.zlsma)
        self.ut_sell = self.I( ut_bot_sell_signal, close, self.ut_trailing_stop, self.zlsma)

        # 趋势检测
        # data['ma_structure_bullish'].values,
        # data['vwOkLong'].values,
        # data['macdSepOk'].values,
        # data['maDistanceOk'].values,
        # data['Close'].values,
        # data['Open'].values
        
        self.ma_structure_bullish = self.I(_crossover, self.ma_fast, self.ma_medium)
        self.ma_structure_bearish = self.I(_crossunder, self.ma_fast, self.ma_medium)
        self.vwap = self.I(vwap, (high + low + close) / 3, volume)
        self.vwOkLong = self.I(vwoklong, close, self.vwap)
        self.vwOkShort = self.I(vwokshort, close, self.vwap)
        # self.macdSepOk = self.I(macdSepOk, self.macd_line, self.macd_signal_line, self.atr)
        # self.maDistanceOk = self.I(maDistanceOk, self.ma_fast, self.ma_medium)
        # self.close_gt_open = self.I(close_gt_open, close, open)
        # self.close_lt_open = self.I(close_lt_open, close, open)
        macdSepOk1 = macdSepOk(self.macd_line, self.macd_signal_line, self.atr)
        maDistanceOk1 = maDistanceOk(self.ma_fast, self.ma_medium)
        self.longCond_base = self.I(longCond_base, self.ma_structure_bullish, self.vwOkLong, macdSepOk1, maDistanceOk1, close, open)
        self.shortCond_base = self.I(shortCond_base, self.ma_structure_bearish, self.vwOkShort, macdSepOk1, maDistanceOk1, close, open)

        # 用于跟踪持仓信息
        self.entry_bar = None
        self.pending_buy_signal = False  # 待执行的买入信号
        self.pending_sell_signal = False  # 待执行的卖出信号(仅平仓)
        self.signal_bar = None  # 信号产生时的K线编号


    def next(self):
        """执行策略逻辑"""
        # 检查是否有足够的数据
        if len(self.data) < 2:
            return
            
        # 获取当前价格
        price = self.data.Close[-1]
        
        # # 检查指标数据是否有效
        # if (np.isnan(self.macd_line[-1]) or np.isnan(self.macd_signal_line[-1]) or 
        #     np.isnan(self.ma_fast[-1]) or np.isnan(self.ma_medium[-1]) or 
        #     np.isnan(self.ma_long[-1]) or np.isnan(self.atr[-1]) or 
        #     np.isnan(self.rsi[-1]) or np.isnan(self.zlsma[-1]) or
        #     np.isnan(self.ut_trailing_stop[-1])):
        #     return
            
        # 波动率过滤
        volatility = self.atr[-1] / price if price != 0 else 0
        if volatility < self.min_volatility:
            return  # 波动率太低，不交易
            
        # 检查是否满足最小持仓期（T+1）
        hold_condition = True
        if self.entry_bar is not None:
            hold_condition = (len(self.data) - self.entry_bar) >= self.min_hold_period
        
        # 检查是否到了信号执行时间
        signal_execution_time = False
        if self.signal_bar is not None:
            signal_execution_time = (len(self.data) - self.signal_bar) >= self.signal_delay
        
        # === 趋势判断系统 ===
        # 均线结构趋势
        ma_structure_bullish = (self.ma_fast[-1] > self.ma_medium[-1]) and (price > self.ma_long[-1])
        ma_structure_bearish = (self.ma_fast[-1] < self.ma_medium[-1]) and (price < self.ma_long[-1])
        
        # MACD动能趋势
        macd_bullish = self.macd_line[-1] > self.macd_signal_line[-1]
        macd_bearish = self.macd_line[-1] < self.macd_signal_line[-1]
        
        # 均线距离和MACD分离度检查
        ma_distance_ok = self.ma_distance_ok[-1]
        macd_sep_ok = self.macd_sep_ok[-1]
        
        # RSI过滤
        rsi_buy_zone = self.rsi_buy_min <= self.rsi[-1] <= self.rsi_buy_max
        rsi_sell_zone = self.rsi[-1] < self.rsi_sell_min or self.rsi[-1] > self.rsi_sell_max
        
        # === 交易信号系统 ===
        # UT Bot信号
        ut_buy_signal = self.ut_buy[-1]
        ut_sell_signal = self.ut_sell[-1]

        longCond_base = self.longCond_base[-1]
        shortCond_base = self.shortCond_base[-1]
        
        # # === 最终交易决策 ===
        # # 买入条件：基础多头信号 且 UT买入信号
        # buy_condition = base_long and ut_buy_signal
        
        # # 卖出条件：基础空头信号 且 UT卖出信号
        # sell_condition = base_short and ut_sell_signal

        # === 最终交易决策 ===
        # 买入条件：基础多头信号 且 UT买入信号
        # buy_condition = longCond_base & ut_buy_signal
        buy_condition = ut_buy_signal
        
        # 卖出条件：基础空头信号 且 UT卖出信号
        sell_condition = ut_sell_signal

        # == 信号执行逻辑 == 
        if sell_condition and hold_condition:
            self.position.close()
            self.entry_bar = None
        
        if buy_condition: 
            # 根据海龟交易法计算仓位大小
            size = self._calculate_turtle_position_size()
            size += self.position.size
            self.position.close()  # 先平掉现有仓位
            
            # 执行买入，设置止损和止盈
            sl = price * (1 - self.sl_percent)  # 止损
            tp = price * (1 + self.tp_percent)  # 止盈
            self.buy(size=size, sl=sl, tp=tp)
            self.entry_bar = len(self.data)  # 记录入场时间

    def _calculate_turtle_position_size(self):
        """
        根据海龟交易法计算仓位大小
        公式: 仓位规模 = (账户总权益 * 风险百分比) / (ATR * 波动性因子)
        """
        # 获取当前账户权益
        equity = self.equity
        
        # 获取当前ATR值
        current_atr = self.turtle_atr[-1]
        
        # 防止ATR为0或NaN
        if np.isnan(current_atr) or current_atr <= 0:
            return 0.1  # 返回默认仓位大小
        
        # 计算理论仓位大小
        position_size = (equity * self.turtle_risk_percent) / (current_atr * self.turtle_volatility_factor)
        
        # 根据波动性调整仓位大小，波动越大仓位越小
        # 限制仓位在10%到100%之间
        # position_size = max(0.1, min(1.0, position_size))

        position_size = position_size // 100 * 100 # 向下取整到最接近的100股
        
        return position_size

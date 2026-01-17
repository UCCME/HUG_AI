"""
究极策略核心模块
整合了所有策略的信号生成和交易逻辑
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from config import UltimateConfig
from indicators import TechnicalIndicators


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """交易信号数据类"""
    timestamp: datetime
    signal_type: SignalType
    confidence: float  # 信号置信度 0-1
    price: float
    reasons: List[str]  # 信号原因列表
    indicators: Dict[str, float]  # 相关指标值
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class UltimateStrategy:
    """究极交易策略类"""
    
    def __init__(self, config: UltimateConfig):
        self.config = config
        self.indicators = TechnicalIndicators()
        
        # 交易状态
        self.current_position = 0
        self.entry_price = 0.0
        self.entry_date = None
        self.highest_profit = 0.0
        self.consecutive_losses = 0
        self.last_trade_date = None
        
        # SMC结构缓存
        self.swing_highs = []
        self.swing_lows = []
        self.bos_signals = []
        self.ch_signals = []
        self.order_blocks = []
        self.fvg_zones = []
    
    def update_smc_structure(self, df: pd.DataFrame):
        """更新SMC市场结构"""
        self.swing_highs, self.swing_lows = self.indicators.find_swings(
            df['high'], df['low'], self.config.SMC_SWING_WINDOW)
        
        self.bos_signals, self.ch_signals = self.indicators.detect_bos_ch(
            df, self.swing_highs, self.swing_lows)
        
        self.order_blocks = self.indicators.detect_order_blocks(df, self.bos_signals)
        self.fvg_zones = self.indicators.detect_fvg(df)
    
    def calculate_ma_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算移动平均线交叉信号
        来自黄金策略
        """
        fast_ma_col = f'MA_{self.config.FAST_MA_PERIOD}'
        slow_ma_col = f'MA_{self.config.SLOW_MA_PERIOD}'
        
        if index < 1:
            return SignalType.HOLD, 0.0, ""
        
        current_fast_ma = data.iloc[index][fast_ma_col]
        current_slow_ma = data.iloc[index][slow_ma_col]
        prev_fast_ma = data.iloc[index - 1][fast_ma_col]
        prev_slow_ma = data.iloc[index - 1][slow_ma_col]
        
        if pd.isna(current_fast_ma) or pd.isna(current_slow_ma):
            return SignalType.HOLD, 0.0, ""
        
        # 黄金交叉
        if prev_fast_ma <= prev_slow_ma and current_fast_ma > current_slow_ma:
            confidence = min(0.8, abs(current_fast_ma - current_slow_ma) / current_slow_ma * 100)
            return SignalType.BUY, confidence, "快线向上穿越慢线(黄金交叉)"
        
        # 死亡交叉
        elif prev_fast_ma >= prev_slow_ma and current_fast_ma < current_slow_ma:
            confidence = min(0.8, abs(current_slow_ma - current_fast_ma) / current_slow_ma * 100)
            return SignalType.SELL, confidence, "快线向下穿越慢线(死亡交叉)"
        
        return SignalType.HOLD, 0.0, ""
    
    def calculate_rsi_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算RSI超买超卖信号
        来自黄金策略
        """
        rsi = data.iloc[index]['RSI']
        
        if pd.isna(rsi):
            return SignalType.HOLD, 0.0, ""
        
        # 超卖买入
        if rsi < self.config.RSI_OVERSOLD:
            confidence = (self.config.RSI_OVERSOLD - rsi) / self.config.RSI_OVERSOLD
            return SignalType.BUY, confidence, f"RSI超卖({rsi:.2f} < {self.config.RSI_OVERSOLD})"
        
        # 超买卖出
        elif rsi > self.config.RSI_OVERBOUGHT:
            confidence = (rsi - self.config.RSI_OVERBOUGHT) / (100 - self.config.RSI_OVERBOUGHT)
            return SignalType.SELL, confidence, f"RSI超买({rsi:.2f} > {self.config.RSI_OVERBOUGHT})"
        
        return SignalType.HOLD, 0.0, ""
    
    def calculate_macd_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算MACD交叉信号
        来自黄金策略
        """
        if index < 1:
            return SignalType.HOLD, 0.0, ""
        
        current_macd = data.iloc[index]['MACD']
        current_signal = data.iloc[index]['MACD_Signal']
        prev_macd = data.iloc[index - 1]['MACD']
        prev_signal = data.iloc[index - 1]['MACD_Signal']
        
        if pd.isna(current_macd) or pd.isna(current_signal):
            return SignalType.HOLD, 0.0, ""
        
        # MACD向上穿越信号线
        if prev_macd <= prev_signal and current_macd > current_signal:
            confidence = min(0.7, abs(current_macd - current_signal) / abs(current_signal) if current_signal != 0 else 0)
            return SignalType.BUY, confidence, "MACD向上穿越信号线"
        
        # MACD向下穿越信号线
        elif prev_macd >= prev_signal and current_macd < current_signal:
            confidence = min(0.7, abs(current_signal - current_macd) / abs(current_signal) if current_signal != 0 else 0)
            return SignalType.SELL, confidence, "MACD向下穿越信号线"
        
        return SignalType.HOLD, 0.0, ""
    
    def calculate_bollinger_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算布林带突破信号
        来自黄金策略
        """
        current_price = data.iloc[index]['close']
        bb_upper = data.iloc[index]['BB_Upper']
        bb_lower = data.iloc[index]['BB_Lower']
        
        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return SignalType.HOLD, 0.0, ""
        
        # 价格触及下轨
        if current_price <= bb_lower:
            confidence = min(0.6, (bb_lower - current_price) / bb_lower * 10)
            return SignalType.BUY, confidence, "价格触及布林带下轨"
        
        # 价格触及上轨
        elif current_price >= bb_upper:
            confidence = min(0.6, (current_price - bb_upper) / bb_upper * 10)
            return SignalType.SELL, confidence, "价格触及布林带上轨"
        
        return SignalType.HOLD, 0.0, ""
    
    def calculate_volume_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算成交量确认信号
        来自黄金策略
        """
        volume_ratio = data.iloc[index]['Volume_Ratio']
        price_change = data.iloc[index]['Price_Change']
        
        if pd.isna(volume_ratio) or pd.isna(price_change):
            return SignalType.HOLD, 0.0, ""
        
        # 放量上涨
        if volume_ratio > 1.5 and price_change > 0.01:
            confidence = min(0.5, volume_ratio / 3 * abs(price_change) * 10)
            return SignalType.BUY, confidence, f"放量上涨(成交量{volume_ratio:.2f}倍)"
        
        # 放量下跌
        elif volume_ratio > 1.5 and price_change < -0.01:
            confidence = min(0.5, volume_ratio / 3 * abs(price_change) * 10)
            return SignalType.SELL, confidence, f"放量下跌(成交量{volume_ratio:.2f}倍)"
        
        return SignalType.HOLD, 0.0, ""
    
    def calculate_stoch_rsi_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算StochRSI信号
        来自StochRSI策略
        """
        stoch_k = data.iloc[index]['StochRSI_K']
        stoch_d = data.iloc[index]['StochRSI_D']
        
        if pd.isna(stoch_k) or pd.isna(stoch_d):
            return SignalType.HOLD, 0.0, ""
        
        # 超卖区金叉
        if stoch_k < self.config.STOCH_OVERSOLD and stoch_k > stoch_d:
            confidence = (self.config.STOCH_OVERSOLD - stoch_k) / self.config.STOCH_OVERSOLD
            return SignalType.BUY, confidence, f"StochRSI超卖区金叉({stoch_k:.2f})"
        
        # 超买区死叉
        elif stoch_k > self.config.STOCH_OVERBOUGHT and stoch_k < stoch_d:
            confidence = (stoch_k - self.config.STOCH_OVERBOUGHT) / (100 - self.config.STOCH_OVERBOUGHT)
            return SignalType.SELL, confidence, f"StochRSI超买区死叉({stoch_k:.2f})"
        
        return SignalType.HOLD, 0.0, ""
    
    def calculate_ut_bot_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算UT Bot趋势信号
        来自Lucy策略
        """
        if index < 1:
            return SignalType.HOLD, 0.0, ""
        
        current_price = data.iloc[index]['close']
        current_stop = data.iloc[index]['UT_Bot_Stop']
        prev_price = data.iloc[index - 1]['close']
        prev_stop = data.iloc[index - 1]['UT_Bot_Stop']
        
        if pd.isna(current_stop) or pd.isna(prev_stop):
            return SignalType.HOLD, 0.0, ""
        
        # 价格突破止损线向上
        if prev_price <= prev_stop and current_price > current_stop:
            confidence = 0.6
            return SignalType.BUY, confidence, "价格突破UT Bot止损线向上"
        
        # 价格跌破止损线向下
        elif prev_price >= prev_stop and current_price < current_stop:
            confidence = 0.6
            return SignalType.SELL, confidence, "价格跌破UT Bot止损线向下"
        
        return SignalType.HOLD, 0.0, ""
    
    def calculate_smc_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算SMC结构信号
        来自SMC技术分析工具
        """
        # 检查是否有BOS信号
        if index in self.bos_signals:
            # 判断是向上还是向下突破
            if index > 0:
                if data.iloc[index]['high'] > data.iloc[index - 1]['high']:
                    return SignalType.BUY, 0.5, "BOS向上突破(结构延续)"
                else:
                    return SignalType.SELL, 0.5, "BOS向下突破(结构延续)"
        
        # 检查是否有CH信号（趋势反转）
        if index in self.ch_signals:
            if index > 0:
                if data.iloc[index]['high'] > data.iloc[index - 1]['high']:
                    return SignalType.BUY, 0.7, "CH趋势反转向上"
                else:
                    return SignalType.SELL, 0.7, "CH趋势反转向下"
        
        # 检查是否在订单块区域
        current_price = data.iloc[index]['close']
        for ob_idx, ob_low, ob_high in self.order_blocks:
            if ob_low <= current_price <= ob_high:
                # 在订单块区域，可能是支撑或阻力
                if ob_idx < index - 5:  # 订单块形成至少5根K线前
                    return SignalType.HOLD, 0.3, f"价格在订单块区域({ob_low:.2f}-{ob_high:.2f})"
        
        return SignalType.HOLD, 0.0, ""
    
    def generate_composite_signal(self, data: pd.DataFrame, index: int) -> TradingSignal:
        """
        生成综合交易信号
        整合所有策略的信号
        """
        timestamp = data.index[index]
        current_price = data.iloc[index]['close']
        
        # 计算所有信号
        signals = []
        confidences = []
        reasons = []
        
        # 基础技术指标信号
        ma_signal, ma_conf, ma_reason = self.calculate_ma_signal(data, index)
        if ma_signal != SignalType.HOLD:
            signals.append(ma_signal)
            confidences.append(ma_conf * self.config.WEIGHT_MA)
            reasons.append(ma_reason)
        
        rsi_signal, rsi_conf, rsi_reason = self.calculate_rsi_signal(data, index)
        if rsi_signal != SignalType.HOLD:
            signals.append(rsi_signal)
            confidences.append(rsi_conf * self.config.WEIGHT_RSI)
            reasons.append(rsi_reason)
        
        macd_signal, macd_conf, macd_reason = self.calculate_macd_signal(data, index)
        if macd_signal != SignalType.HOLD:
            signals.append(macd_signal)
            confidences.append(macd_conf * self.config.WEIGHT_MACD)
            reasons.append(macd_reason)
        
        bb_signal, bb_conf, bb_reason = self.calculate_bollinger_signal(data, index)
        if bb_signal != SignalType.HOLD:
            signals.append(bb_signal)
            confidences.append(bb_conf * self.config.WEIGHT_BB)
            reasons.append(bb_reason)
        
        vol_signal, vol_conf, vol_reason = self.calculate_volume_signal(data, index)
        if vol_signal != SignalType.HOLD:
            signals.append(vol_signal)
            confidences.append(vol_conf * self.config.WEIGHT_VOLUME)
            reasons.append(vol_reason)
        
        # 高级指标信号
        stoch_signal, stoch_conf, stoch_reason = self.calculate_stoch_rsi_signal(data, index)
        if stoch_signal != SignalType.HOLD:
            signals.append(stoch_signal)
            confidences.append(stoch_conf * self.config.WEIGHT_STOCH_RSI)
            reasons.append(stoch_reason)
        
        ut_signal, ut_conf, ut_reason = self.calculate_ut_bot_signal(data, index)
        if ut_signal != SignalType.HOLD:
            signals.append(ut_signal)
            confidences.append(ut_conf * self.config.WEIGHT_UT_BOT)
            reasons.append(ut_reason)
        
        smc_signal, smc_conf, smc_reason = self.calculate_smc_signal(data, index)
        if smc_signal != SignalType.HOLD:
            signals.append(smc_signal)
            confidences.append(smc_conf * self.config.WEIGHT_SMC)
            reasons.append(smc_reason)
        
        # 计算综合得分
        buy_score = sum(conf for sig, conf in zip(signals, confidences) if sig == SignalType.BUY)
        sell_score = sum(conf for sig, conf in zip(signals, confidences) if sig == SignalType.SELL)
        
        # 信号评分系统（来自加密货币策略）
        buy_signal_count = sum(1 for sig in signals if sig == SignalType.BUY)
        sell_signal_count = sum(1 for sig in signals if sig == SignalType.SELL)
        
        # 决策逻辑
        final_signal = SignalType.HOLD
        final_confidence = 0.0
        
        if buy_score > self.config.SIGNAL_THRESHOLD and buy_score > sell_score and buy_signal_count >= self.config.MIN_SIGNAL_SCORE:
            final_signal = SignalType.BUY
            final_confidence = buy_score
        elif sell_score > self.config.SIGNAL_THRESHOLD and sell_score > buy_score and sell_signal_count >= self.config.MIN_SIGNAL_SCORE:
            final_signal = SignalType.SELL
            final_confidence = sell_score
        
        # 计算止损止盈
        atr = data.iloc[index]['ATR']
        stop_loss = None
        take_profit = None
        
        if final_signal == SignalType.BUY:
            # ATR动态止损
            stop_loss = current_price - atr * self.config.ATR_STOP_MULTIPLIER
            take_profit = current_price + atr * self.config.ATR_TAKE_PROFIT_MULTIPLIER
            
            # 结合UT Bot止损线
            ut_stop = data.iloc[index]['UT_Bot_Stop']
            if not pd.isna(ut_stop) and ut_stop > stop_loss:
                stop_loss = ut_stop
        
        elif final_signal == SignalType.SELL:
            stop_loss = current_price + atr * self.config.ATR_STOP_MULTIPLIER
            take_profit = current_price - atr * self.config.ATR_TAKE_PROFIT_MULTIPLIER
            
            ut_stop = data.iloc[index]['UT_Bot_Stop']
            if not pd.isna(ut_stop) and ut_stop < stop_loss:
                stop_loss = ut_stop
        
        # 收集指标值
        indicators = {
            'price': current_price,
            'rsi': data.iloc[index]['RSI'],
            'macd': data.iloc[index]['MACD'],
            'atr': atr,
            'volume_ratio': data.iloc[index]['Volume_Ratio'],
            'stoch_rsi_k': data.iloc[index]['StochRSI_K'],
            'buy_score': buy_score,
            'sell_score': sell_score,
            'buy_signal_count': buy_signal_count,
            'sell_signal_count': sell_signal_count
        }
        
        return TradingSignal(
            timestamp=timestamp,
            signal_type=final_signal,
            confidence=final_confidence,
            price=current_price,
            reasons=reasons,
            indicators=indicators,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
    
    def check_time_stop(self, current_date: datetime) -> bool:
        """
        检查时间止损
        来自期权策略：7天未启动离场
        """
        if self.entry_date is None:
            return False
        
        days_held = (current_date - self.entry_date).days
        
        # 如果持仓超过7天且没有盈利，触发时间止损
        if days_held >= self.config.TIME_STOP_DAYS:
            if self.current_position > 0:
                current_profit = (self.entry_price - self.entry_price) / self.entry_price
                if current_profit <= 0:
                    return True
        
        return False
    
    def check_cooldown(self, current_date: datetime) -> bool:
        """
        检查冷却期
        来自加密货币策略：亏损后冷却期
        """
        if self.last_trade_date is None:
            return False
        
        days_since_last_trade = (current_date - self.last_trade_date).days
        
        # 如果有连续亏损，需要冷却
        if self.consecutive_losses > 0 and days_since_last_trade < self.config.COOLDOWN_DAYS:
            return True
        
        return False
    
    def should_roll_position(self, current_price: float) -> Tuple[bool, float, float]:
        """
        检查是否应该动态移仓
        来自期权策略：30/70法则
        """
        if self.current_position == 0 or self.entry_price == 0:
            return False, 0.0, 0.0
        
        # 计算当前盈利
        current_profit_pct = (current_price - self.entry_price) / self.entry_price
        
        # 如果盈利超过触发阈值
        if abs(current_profit_pct) >= self.config.ROLL_TRIGGER_PCT:
            # 锁定70%利润，30%继续进攻
            defense_ratio = self.config.ROLL_DEFENSE_RATIO
            attack_ratio = self.config.ROLL_ATTACK_RATIO
            
            return True, defense_ratio, attack_ratio
        
        return False, 0.0, 0.0
    
    def calculate_position_size(self, signal: TradingSignal, available_cash: float) -> int:
        """
        计算仓位大小
        整合动态仓位管理
        """
        price = signal.price
        confidence = signal.confidence
        atr = signal.indicators.get('atr', 0)
        
        # 基于信号置信度调整仓位
        adjusted_position_size = self.config.POSITION_SIZE * confidence
        
        # ATR风险调整
        if atr and atr > 0:
            risk_amount = available_cash * self.config.RISK_PER_TRADE
            stop_distance = atr * self.config.ATR_STOP_MULTIPLIER
            position_by_risk = risk_amount / (stop_distance * price)
            
            max_position_ratio = min(adjusted_position_size, position_by_risk * price / available_cash)
        else:
            max_position_ratio = adjusted_position_size
        
        # 限制最大仓位
        max_position_ratio = min(max_position_ratio, self.config.MAX_POSITION_PCT)
        
        available_for_position = available_cash * max_position_ratio
        position_count = int(available_for_position / (price * (1 + self.config.COMMISSION_RATE + self.config.SLIPPAGE)))
        
        return max(1, position_count)

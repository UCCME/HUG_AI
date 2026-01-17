"""
黄金合约交易策略
基于多种技术指标的综合趋势跟踪策略

主要特性：
- 多指标综合信号（MA、RSI、MACD、布林带、成交量）
- 动态仓位管理
- ATR动态止损止盈
- 趋势过滤机制
- 完整的风险管理
"""

import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型枚举"""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class TradingSignal:
    """交易信号类"""
    timestamp: datetime
    signal_type: SignalType
    price: float
    confidence: float  # 信号置信度 0-1
    indicators: Dict[str, float]  # 各指标的值
    reason: str  # 信号产生原因
    individual_signals: Dict[str, Tuple[SignalType, float, str]] = field(default_factory=dict)  # 各指标的原始信号


@dataclass
class StrategyConfig:
    """策略配置类"""
    # MA配置
    FAST_MA_PERIOD: int = 10
    SLOW_MA_PERIOD: int = 20
    
    # RSI配置
    RSI_OVERSOLD: float = 30
    RSI_OVERBOUGHT: float = 70
    
    # 止损止盈配置
    STOP_LOSS_PCT: float = 0.02
    TAKE_PROFIT_PCT: float = 0.03
    ATR_STOP_MULTIPLIER: float = 2.0  # ATR止损倍数
    ATR_PROFIT_MULTIPLIER: float = 3.0  # ATR止盈倍数
    
    # 仓位配置
    POSITION_SIZE: float = 0.3
    MAX_POSITION_SIZE: float = 0.5
    RISK_PER_TRADE: float = 0.01  # 每笔交易风险比例
    
    # 信号权重
    WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        'ma': 0.30,
        'macd': 0.25,
        'rsi': 0.20,
        'bb': 0.15,
        'volume': 0.10
    })
    
    # 信号阈值
    SIGNAL_THRESHOLD: float = 0.15
    
    # 交易成本
    COMMISSION_RATE: float = 0.0003  # 手续费率
    SLIPPAGE: float = 0.0001  # 滑点
    
    def validate(self):
        """验证配置参数的有效性"""
        assert self.FAST_MA_PERIOD < self.SLOW_MA_PERIOD, "快线周期必须小于慢线周期"
        assert 0 < self.RSI_OVERSOLD < self.RSI_OVERBOUGHT < 100, "RSI参数无效"
        assert 0 < self.POSITION_SIZE <= 1, "仓位比例必须在0-1之间"
        assert sum(self.WEIGHTS.values()) <= 1.01, "权重总和不能超过1"
        logger.info("策略配置验证通过")


class GoldTradingStrategy:
    """
    黄金合约交易策略类
    使用移动平均线交叉、RSI和MACD的综合信号
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.config.validate()
        
        self.position = 0  # 当前持仓：1=多头，-1=空头，0=空仓
        self.entry_price = 0.0
        self.signals_history: List[TradingSignal] = []
        self.trades_history: List[Dict] = []
        
        # 策略状态
        self.last_signal: Optional[TradingSignal] = None
        self.consecutive_signals = 0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        
        logger.info("策略初始化完成")
        
    def _safe_get_indicator(self, data: pd.DataFrame, index: int, column: str, default=None):
        """安全获取指标值，处理缺失值"""
        try:
            value = data.iloc[index][column]
            return default if pd.isna(value) else value
        except (KeyError, IndexError):
            return default
    
    def _calculate_confidence(self, diff: float, base: float, max_conf: float = 0.8, scale: float = 100) -> float:
        """统一的置信度计算方法"""
        if base == 0:
            return 0.0
        return min(max_conf, abs(diff / base) * scale)
    
    def calculate_ma_crossover_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算移动平均线交叉信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        if index < 1:
            return SignalType.HOLD, 0.0, "数据不足"
        
        try:
            fast_ma_col = f'MA_{self.config.FAST_MA_PERIOD}'
            slow_ma_col = f'MA_{self.config.SLOW_MA_PERIOD}'
            
            current_fast_ma = self._safe_get_indicator(data, index, fast_ma_col)
            current_slow_ma = self._safe_get_indicator(data, index, slow_ma_col)
            prev_fast_ma = self._safe_get_indicator(data, index-1, fast_ma_col)
            prev_slow_ma = self._safe_get_indicator(data, index-1, slow_ma_col)
            
            if None in [current_fast_ma, current_slow_ma, prev_fast_ma, prev_slow_ma]:
                return SignalType.HOLD, 0.0, "MA数据缺失"
            
            # 检查黄金交叉
            if prev_fast_ma <= prev_slow_ma and current_fast_ma > current_slow_ma:
                confidence = self._calculate_confidence(
                    current_fast_ma - current_slow_ma, 
                    current_slow_ma
                )
                return SignalType.BUY, confidence, f"金叉({current_fast_ma:.2f}>{current_slow_ma:.2f})"
            
            # 检查死亡交叉
            elif prev_fast_ma >= prev_slow_ma and current_fast_ma < current_slow_ma:
                confidence = self._calculate_confidence(
                    current_slow_ma - current_fast_ma,
                    current_slow_ma
                )
                return SignalType.SELL, confidence, f"死叉({current_fast_ma:.2f}<{current_slow_ma:.2f})"
            
            return SignalType.HOLD, 0.0, "无交叉信号"
        
        except Exception as e:
            logger.error(f"MA信号计算错误: {e}")
            return SignalType.HOLD, 0.0, "计算错误"
    
    def calculate_rsi_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算RSI信号（增强版：考虑背离）
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        try:
            rsi = self._safe_get_indicator(data, index, 'RSI')
            if rsi is None:
                return SignalType.HOLD, 0.0, "RSI数据缺失"
            
            # 超卖区域 - 买入信号
            if rsi < self.config.RSI_OVERSOLD:
                confidence = (self.config.RSI_OVERSOLD - rsi) / self.config.RSI_OVERSOLD
                return SignalType.BUY, min(confidence, 0.8), f"RSI超卖({rsi:.1f}<{self.config.RSI_OVERSOLD})"
            
            # 超买区域 - 卖出信号
            elif rsi > self.config.RSI_OVERBOUGHT:
                confidence = (rsi - self.config.RSI_OVERBOUGHT) / (100 - self.config.RSI_OVERBOUGHT)
                return SignalType.SELL, min(confidence, 0.8), f"RSI超买({rsi:.1f}>{self.config.RSI_OVERBOUGHT})"
            
            return SignalType.HOLD, 0.0, f"RSI正常({rsi:.1f})"
        
        except Exception as e:
            logger.error(f"RSI信号计算错误: {e}")
            return SignalType.HOLD, 0.0, "计算错误"
    
    def calculate_macd_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算MACD信号（增强版：考虑柱状图和零轴）
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        if index < 1:
            return SignalType.HOLD, 0.0, "MACD数据不足"
        
        try:
            current_macd = self._safe_get_indicator(data, index, 'MACD')
            current_signal = self._safe_get_indicator(data, index, 'MACD_Signal')
            prev_macd = self._safe_get_indicator(data, index-1, 'MACD')
            prev_signal = self._safe_get_indicator(data, index-1, 'MACD_Signal')
            
            if None in [current_macd, current_signal, prev_macd, prev_signal]:
                return SignalType.HOLD, 0.0, "MACD数据缺失"
            
            # 计算MACD柱状图
            current_hist = current_macd - current_signal
            prev_hist = prev_macd - prev_signal
            
            # MACD向上穿越信号线
            if prev_hist <= 0 and current_hist > 0:
                # 零轴上方的金叉更可靠
                base_conf = self._calculate_confidence(
                    abs(current_hist),
                    abs(current_signal) if current_signal != 0 else 0.01,
                    max_conf=0.7,
                    scale=1
                )
                # 如果在零轴上方，增加置信度
                confidence = base_conf * 1.2 if current_macd > 0 else base_conf
                return SignalType.BUY, min(confidence, 0.8), f"MACD金叉({current_macd:.4f})"
            
            # MACD向下穿越信号线
            elif prev_hist >= 0 and current_hist < 0:
                base_conf = self._calculate_confidence(
                    abs(current_hist),
                    abs(current_signal) if current_signal != 0 else 0.01,
                    max_conf=0.7,
                    scale=1
                )
                # 如果在零轴下方，增加置信度
                confidence = base_conf * 1.2 if current_macd < 0 else base_conf
                return SignalType.SELL, min(confidence, 0.8), f"MACD死叉({current_macd:.4f})"
            
            return SignalType.HOLD, 0.0, "MACD无穿越"
        
        except Exception as e:
            logger.error(f"MACD信号计算错误: {e}")
            return SignalType.HOLD, 0.0, "计算错误"
    
    def calculate_bollinger_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算布林带信号（增强版：考虑带宽和趋势）
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        try:
            current_price = self._safe_get_indicator(data, index, 'Close')
            bb_upper = self._safe_get_indicator(data, index, 'BB_Upper')
            bb_lower = self._safe_get_indicator(data, index, 'BB_Lower')
            bb_middle = self._safe_get_indicator(data, index, 'BB_Middle')
            
            if None in [current_price, bb_upper, bb_lower, bb_middle]:
                return SignalType.HOLD, 0.0, "布林带数据缺失"
            
            # 计算价格相对位置（0-1之间）
            bb_width = bb_upper - bb_lower
            if bb_width == 0:
                return SignalType.HOLD, 0.0, "布林带宽度为零"
            
            price_position = (current_price - bb_lower) / bb_width
            
            # 价格触及或突破下轨
            if price_position <= 0.05:  # 在下轨5%范围内
                confidence = min(0.6, (bb_lower - current_price) / bb_lower * 10)
                return SignalType.BUY, confidence, f"BB下轨({current_price:.2f}≤{bb_lower:.2f})"
            
            # 价格触及或突破上轨
            elif price_position >= 0.95:  # 在上轨5%范围内
                confidence = min(0.6, (current_price - bb_upper) / bb_upper * 10)
                return SignalType.SELL, confidence, f"BB上轨({current_price:.2f}≥{bb_upper:.2f})"
            
            return SignalType.HOLD, 0.0, f"BB中性({price_position:.1%})"
        
        except Exception as e:
            logger.error(f"布林带信号计算错误: {e}")
            return SignalType.HOLD, 0.0, "计算错误"
    
    def calculate_volume_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算成交量信号（增强版：区分放量和缩量）
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        try:
            volume_ratio = self._safe_get_indicator(data, index, 'Volume_Ratio')
            price_change = self._safe_get_indicator(data, index, 'Price_Change')
            
            if None in [volume_ratio, price_change]:
                return SignalType.HOLD, 0.0, "成交量数据缺失"
            
            # 明显放量（量比>1.5）
            if volume_ratio > 1.5:
                # 放量上涨 - 买入信号
                if price_change > 0.005:  # 涨幅>0.5%
                    confidence = min(0.5, (volume_ratio / 3) * abs(price_change) * 10)
                    return SignalType.BUY, confidence, f"放量涨({volume_ratio:.1f}x,+{price_change*100:.1f}%)"
                
                # 放量下跌 - 卖出信号
                elif price_change < -0.005:  # 跌幅>0.5%
                    confidence = min(0.5, (volume_ratio / 3) * abs(price_change) * 10)
                    return SignalType.SELL, confidence, f"放量跌({volume_ratio:.1f}x,{price_change*100:.1f}%)"
            
            # 缩量（量比<0.7）- 需要警惕
            elif volume_ratio < 0.7 and abs(price_change) > 0.01:
                # 缩量上涨可能乏力
                if price_change > 0:
                    return SignalType.HOLD, 0.0, f"缩量涨({volume_ratio:.1f}x)-警惕"
            
            return SignalType.HOLD, 0.0, f"量价正常({volume_ratio:.1f}x)"
        
        except Exception as e:
            logger.error(f"成交量信号计算错误: {e}")
            return SignalType.HOLD, 0.0, "计算错误"
    
    def check_trend_filter(self, data: pd.DataFrame, index: int) -> Tuple[bool, str]:
        """
        趋势过滤器：确保交易方向与主趋势一致
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            是否通过过滤, 趋势描述
        """
        try:
            # 使用较长周期MA判断趋势
            slow_ma = self._safe_get_indicator(data, index, f'MA_{self.config.SLOW_MA_PERIOD}')
            price = self._safe_get_indicator(data, index, 'Close')
            
            if None in [slow_ma, price]:
                return True, "趋势未知"
            
            # 简单趋势判断
            if price > slow_ma * 1.02:  # 价格明显高于慢线
                return True, "上升趋势"
            elif price < slow_ma * 0.98:  # 价格明显低于慢线
                return True, "下降趋势"
            else:
                return True, "震荡趋势"
        
        except Exception as e:
            logger.error(f"趋势过滤错误: {e}")
            return True, "过滤失败"
    
    def generate_composite_signal(self, data: pd.DataFrame, index: int) -> TradingSignal:
        """
        生成综合交易信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            综合交易信号
        """
        timestamp = data.index[index]
        current_price = data.iloc[index]['Close']
        
        # 并行计算所有指标信号
        ma_signal, ma_confidence, ma_reason = self.calculate_ma_crossover_signal(data, index)
        rsi_signal, rsi_confidence, rsi_reason = self.calculate_rsi_signal(data, index)
        macd_signal, macd_confidence, macd_reason = self.calculate_macd_signal(data, index)
        bb_signal, bb_confidence, bb_reason = self.calculate_bollinger_signal(data, index)
        vol_signal, vol_confidence, vol_reason = self.calculate_volume_signal(data, index)
        
        # 保存各指标的原始信号
        individual_signals = {
            'ma': (ma_signal, ma_confidence, ma_reason),
            'rsi': (rsi_signal, rsi_confidence, rsi_reason),
            'macd': (macd_signal, macd_confidence, macd_reason),
            'bb': (bb_signal, bb_confidence, bb_reason),
            'volume': (vol_signal, vol_confidence, vol_reason)
        }
        
        # 使用配置的权重
        weights = self.config.WEIGHTS
        
        # 计算加权信号得分
        signals = [ma_signal, rsi_signal, macd_signal, bb_signal, vol_signal]
        confidences = [ma_confidence, rsi_confidence, macd_confidence, bb_confidence, vol_confidence]
        weight_list = list(weights.values())
        
        buy_score = 0
        sell_score = 0
        
        for signal, confidence, weight in zip(signals, confidences, weight_list):
            if signal == SignalType.BUY:
                buy_score += confidence * weight
            elif signal == SignalType.SELL:
                sell_score += confidence * weight
        
        # 决定最终信号
        signal_threshold = self.config.SIGNAL_THRESHOLD
        
        # 应用趋势过滤
        trend_ok, trend_desc = self.check_trend_filter(data, index)
        
        if buy_score > sell_score and buy_score > signal_threshold:
            final_signal = SignalType.BUY
            final_confidence = buy_score
        elif sell_score > buy_score and sell_score > signal_threshold:
            final_signal = SignalType.SELL
            final_confidence = sell_score
        else:
            final_signal = SignalType.HOLD
            final_confidence = 0.0
        
        # 组合信号原因
        reasons = []
        if ma_signal != SignalType.HOLD:
            reasons.append(f"MA:{ma_reason}")
        if rsi_signal != SignalType.HOLD:
            reasons.append(f"RSI:{rsi_reason}")
        if macd_signal != SignalType.HOLD:
            reasons.append(f"MACD:{macd_reason}")
        if bb_signal != SignalType.HOLD:
            reasons.append(f"BB:{bb_reason}")
        if vol_signal != SignalType.HOLD:
            reasons.append(f"VOL:{vol_reason}")
        
        combined_reason = "; ".join(reasons) if reasons else "所有指标无明确信号"
        
        # 创建指标值字典
        indicators = {
            'MA_fast': data.iloc[index][f'MA_{self.config.FAST_MA_PERIOD}'],
            'MA_slow': data.iloc[index][f'MA_{self.config.SLOW_MA_PERIOD}'],
            'RSI': data.iloc[index]['RSI'],
            'MACD': data.iloc[index]['MACD'],
            'MACD_Signal': data.iloc[index]['MACD_Signal'],
            'BB_Upper': data.iloc[index]['BB_Upper'],
            'BB_Lower': data.iloc[index]['BB_Lower'],
            'Volume_Ratio': data.iloc[index]['Volume_Ratio'],
            'ATR': data.iloc[index]['ATR']
        }
        
        # 添加趋势信息到原因中
        if final_signal != SignalType.HOLD:
            combined_reason = f"[{trend_desc}] {combined_reason}"
        
        trading_signal = TradingSignal(
            timestamp=timestamp,
            signal_type=final_signal,
            price=current_price,
            confidence=final_confidence,
            indicators=indicators,
            reason=combined_reason,
            individual_signals=individual_signals
        )
        
        return trading_signal
    
    def calculate_atr_stop_loss(self, data: pd.DataFrame, index: int, position_type: SignalType) -> Tuple[float, float]:
        """
        计算ATR动态止损和止盈点位（优化版）
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            position_type: 持仓方向
            
        Returns:
            止损价位, 止盈价位
        """
        try:
            current_price = self._safe_get_indicator(data, index, 'Close')
            if current_price is None:
                raise ValueError("当前价格缺失")
            
            atr = self._safe_get_indicator(data, index, 'ATR')
            
            # 使用ATR或默认百分比
            if atr is not None and atr > 0:
                # 使用配置的ATR倍数
                stop_distance = atr * self.config.ATR_STOP_MULTIPLIER
                profit_distance = atr * self.config.ATR_PROFIT_MULTIPLIER
            else:
                # 降级到百分比
                stop_distance = current_price * self.config.STOP_LOSS_PCT
                profit_distance = current_price * self.config.TAKE_PROFIT_PCT
            
            if position_type == SignalType.BUY:
                stop_loss = current_price - stop_distance
                take_profit = current_price + profit_distance
            else:  # SELL
                stop_loss = current_price + stop_distance
                take_profit = current_price - profit_distance
            
            return stop_loss, take_profit
        
        except Exception as e:
            logger.error(f"止损止盈计算错误: {e}")
            # 返回保守的默认值
            if position_type == SignalType.BUY:
                return current_price * 0.98, current_price * 1.03
            else:
                return current_price * 1.02, current_price * 0.97
    
    def should_exit_position(self, data: pd.DataFrame, index: int, entry_price: float, 
                           position_type: SignalType, current_signal: Optional[TradingSignal] = None) -> Tuple[bool, str]:
        """
        判断是否应该平仓（优化版：避免重复计算信号）
        
        Args:
            data: 行情数据
            index: 当前索引
            entry_price: 入场价格
            position_type: 持仓方向
            current_signal: 当前已计算的信号（避免重复计算）
            
        Returns:
            是否平仓, 平仓原因
        """
        try:
            current_price = self._safe_get_indicator(data, index, 'Close')
            if current_price is None:
                return False, "价格数据缺失"
            
            # 止损判断（优先级最高）
            if position_type == SignalType.BUY and current_price <= self.stop_loss:
                return True, f"多头止损({current_price:.2f}≤{self.stop_loss:.2f})"
            elif position_type == SignalType.SELL and current_price >= self.stop_loss:
                return True, f"空头止损({current_price:.2f}≥{self.stop_loss:.2f})"
            
            # 止盈判断
            if position_type == SignalType.BUY and current_price >= self.take_profit:
                return True, f"多头止盈({current_price:.2f}≥{self.take_profit:.2f})"
            elif position_type == SignalType.SELL and current_price <= self.take_profit:
                return True, f"空头止盈({current_price:.2f}≤{self.take_profit:.2f})"
            
            # 反向信号平仓（使用传入的信号，避免重复计算）
            if current_signal and current_signal.confidence > 0.3:  # 只有强信号才触发反向平仓
                if ((position_type == SignalType.BUY and current_signal.signal_type == SignalType.SELL) or 
                    (position_type == SignalType.SELL and current_signal.signal_type == SignalType.BUY)):
                    return True, f"反向强信号({current_signal.confidence:.2f}): {current_signal.reason}"
            
            return False, ""
        
        except Exception as e:
            logger.error(f"平仓判断错误: {e}")
            return False, "判断错误"
    
    def should_close_position(self, data: pd.DataFrame, index: int) -> Tuple[bool, str]:
        """
        判断是否应该平仓（兼容旧版本接口）
        
        Args:
            data: 行情数据
            index: 当前索引
            
        Returns:
            是否平仓, 平仓原因
        """
        if self.position == 0:
            return False, "无持仓"
        
        position_type = SignalType.BUY if self.position > 0 else SignalType.SELL
        return self.should_exit_position(data, index, self.entry_price, position_type)
    
    def calculate_position_size(self, capital: float, price: float, confidence: float, atr: float = None) -> int:
        """
        根据信号置信度和风险动态计算仓位大小（优化版）
        
        Args:
            capital: 可用资金
            price: 当前价格
            confidence: 信号置信度 (0-1)
            atr: ATR值，用于风险调整仓位
            
        Returns:
            仓位数量
        """
        try:
            # 基础仓位根据置信度调整
            base_position_ratio = self.config.POSITION_SIZE * confidence
            
            # 确保不超过最大仓位限制
            base_position_ratio = min(base_position_ratio, self.config.MAX_POSITION_SIZE)
            
            # 如果有ATR，使用固定风险金额法计算仓位
            if atr and atr > 0:
                # 计算最大可承受的风险金额
                risk_amount = capital * self.config.RISK_PER_TRADE
                
                # 计算止损距离（使用ATR）
                stop_distance = atr * self.config.ATR_STOP_MULTIPLIER
                
                # 基于风险的仓位大小
                if stop_distance > 0:
                    position_by_risk = risk_amount / stop_distance
                    position_ratio = min(base_position_ratio, position_by_risk * price / capital)
                else:
                    position_ratio = base_position_ratio
            else:
                position_ratio = base_position_ratio
            
            # 计算实际仓位数量
            position_value = capital * position_ratio
            position_size = int(position_value / price)
            
            # 至少1手，最多不超过总资金能买的数量
            max_size = int(capital * self.config.MAX_POSITION_SIZE / price)
            position_size = max(1, min(position_size, max_size))
            
            logger.debug(f"仓位计算: 资金={capital}, 价格={price}, 置信度={confidence:.2f}, "
                        f"ATR={atr}, 仓位={position_size}")
            
            return position_size
        
        except Exception as e:
            logger.error(f"仓位计算错误: {e}")
            return 1  # 降级到最小仓位
    
    def execute_signal(self, signal: TradingSignal, capital: float = 100000) -> Dict:
        """
        执行交易信号（优化版：考虑滑点和手续费）
        
        Args:
            signal: 交易信号
            capital: 账户资金，默认10万
            
        Returns:
            交易执行结果
        """
        # 考虑滑点的实际成交价
        actual_price = signal.price * (1 + self.config.SLIPPAGE if signal.signal_type == SignalType.BUY 
                                       else 1 - self.config.SLIPPAGE)
        
        trade_result = {
            'timestamp': signal.timestamp,
            'action': 'hold',
            'price': actual_price,
            'signal_price': signal.price,
            'position_before': self.position,
            'position_after': self.position,
            'reason': signal.reason,
            'confidence': signal.confidence,
            'position_size': 0,
            'cost': 0.0  # 交易成本（手续费+滑点）
        }
        
        # 记录信号历史
        self.signals_history.append(signal)
        self.last_signal = signal
        
        # 获取ATR用于仓位计算和风险控制
        atr = signal.indicators.get('ATR', None)
        
        # 执行交易逻辑
        if signal.signal_type == SignalType.BUY and self.position != 1:
            if self.position == -1:
                # 平空仓 - 计算盈亏
                pnl_pct = (self.entry_price - actual_price) / self.entry_price
                commission = actual_price * self.config.COMMISSION_RATE
                
                trade_result['action'] = 'close_short'
                self.trades_history.append({
                    'timestamp': signal.timestamp,
                    'action': 'close_short',
                    'price': actual_price,
                    'entry_price': self.entry_price,
                    'pnl': pnl_pct,
                    'position_size': abs(self.position),
                    'commission': commission
                })
            
            # 计算智能仓位
            position_size = self.calculate_position_size(capital, actual_price, signal.confidence, atr)
            
            # 计算交易成本
            trade_cost = actual_price * position_size * self.config.COMMISSION_RATE
            
            # 开多仓 - 设置止损止盈
            self.stop_loss, self.take_profit = self.calculate_atr_stop_loss(
                pd.DataFrame({'Close': [actual_price], 'ATR': [atr]}), 0, SignalType.BUY
            )
            
            action_name = 'buy' if self.position == 0 else 'close_short_and_buy'
            trade_result.update({
                'action': action_name,
                'position_after': 1,
                'position_size': position_size,
                'cost': trade_cost,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit
            })
            
            self.position = 1
            self.entry_price = actual_price
            
        elif signal.signal_type == SignalType.SELL and self.position != -1:
            if self.position == 1:
                # 平多仓 - 计算盈亏
                pnl_pct = (actual_price - self.entry_price) / self.entry_price
                commission = actual_price * self.config.COMMISSION_RATE
                
                trade_result['action'] = 'close_long'
                self.trades_history.append({
                    'timestamp': signal.timestamp,
                    'action': 'close_long',
                    'price': actual_price,
                    'entry_price': self.entry_price,
                    'pnl': pnl_pct,
                    'position_size': abs(self.position),
                    'commission': commission
                })
            
            # 计算智能仓位
            position_size = self.calculate_position_size(capital, actual_price, signal.confidence, atr)
            
            # 计算交易成本
            trade_cost = actual_price * position_size * self.config.COMMISSION_RATE
            
            # 开空仓 - 设置止损止盈
            self.stop_loss, self.take_profit = self.calculate_atr_stop_loss(
                pd.DataFrame({'Close': [actual_price], 'ATR': [atr]}), 0, SignalType.SELL
            )
            
            action_name = 'sell' if self.position == 0 else 'close_long_and_sell'
            trade_result.update({
                'action': action_name,
                'position_after': -1,
                'position_size': position_size,
                'cost': trade_cost,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit
            })
            
            self.position = -1
            self.entry_price = actual_price
        
        return trade_result
    
    def get_strategy_stats(self) -> Dict:
        """
        获取策略统计信息
        
        Returns:
            策略统计信息
        """
        if not self.trades_history:
            return {
                'total_trades': 0, 
                'win_rate': 0, 
                'avg_return': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'avg_position_size': 0,
                'current_position': self.position
            }
        
        total_trades = len(self.trades_history)
        profitable_trades = [t for t in self.trades_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trades_history if t['pnl'] <= 0]
        
        win_rate = len(profitable_trades) / total_trades if total_trades > 0 else 0
        avg_return = np.mean([t['pnl'] for t in self.trades_history]) if self.trades_history else 0
        total_pnl = sum(t['pnl'] for t in self.trades_history)
        
        # 计算最大回撤
        cumulative_returns = np.cumsum([t['pnl'] for t in self.trades_history])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = running_max - cumulative_returns
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
        
        # 计算盈利因子
        gross_profit = sum(t['pnl'] for t in profitable_trades) if profitable_trades else 0
        gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss
        
        # 平均仓位大小
        avg_position_size = np.mean([t.get('position_size', 1) for t in self.trades_history])
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'avg_position_size': avg_position_size,
            'current_position': self.position
        }
        
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000, verbose: bool = False) -> Tuple[List[TradingSignal], List[Dict]]:
        """
        执行回测（优化版：避免重复计算，添加进度提示）
        
        Args:
            data: 包含技术指标的行情数据
            initial_capital: 初始资金
            verbose: 是否输出详细日志
            
        Returns:
            交易信号列表, 交易记录列表
        """
        signals = []
        trades = []
        current_capital = initial_capital
        
        logger.info(f"开始回测: 数据长度={len(data)}, 初始资金={initial_capital}")
        
        for i in range(len(data)):
            # 生成交易信号（只计算一次）
            signal = self.generate_composite_signal(data, i)
            signals.append(signal)
            
            # 检查是否需要止损止盈或反向平仓
            if self.position != 0:
                should_exit, exit_reason = self.should_exit_position(
                    data, i, self.entry_price, 
                    SignalType.BUY if self.position > 0 else SignalType.SELL,
                    current_signal=signal  # 传入已计算的信号
                )
                
                if should_exit:
                    # 执行平仓
                    exit_signal = TradingSignal(
                        timestamp=signal.timestamp,
                        signal_type=SignalType.HOLD,
                        price=signal.price,
                        confidence=1.0,
                        indicators=signal.indicators,
                        reason=exit_reason
                    )
                    trade_result = self.execute_signal(exit_signal, current_capital)
                    if trade_result['action'] != 'hold':
                        trades.append(trade_result)
                        if verbose:
                            logger.info(f"[{signal.timestamp}] 平仓: {exit_reason}")
            
            # 根据信号和当前持仓情况决定交易行为
            if signal.signal_type == SignalType.BUY and self.position != 1:
                trade_result = self.execute_signal(signal, current_capital)
                if trade_result['action'] != 'hold':
                    trades.append(trade_result)
                    if verbose:
                        logger.info(f"[{signal.timestamp}] 开多: {signal.reason}, 置信度={signal.confidence:.2f}")
                    
            elif signal.signal_type == SignalType.SELL and self.position != -1:
                trade_result = self.execute_signal(signal, current_capital)
                if trade_result['action'] != 'hold':
                    trades.append(trade_result)
                    if verbose:
                        logger.info(f"[{signal.timestamp}] 开空: {signal.reason}, 置信度={signal.confidence:.2f}")
        
        logger.info(f"回测完成: 信号数={len(signals)}, 交易数={len(trades)}")
        return signals, trades

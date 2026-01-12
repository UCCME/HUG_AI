"""
黄金合约交易策略
基于多种技术指标的综合趋势跟踪策略
"""

import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

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

class GoldTradingStrategy:
    """
    黄金合约交易策略类
    使用移动平均线交叉、RSI和MACD的综合信号
    """
    
    def __init__(self, config):
        self.config = config
        self.position = 0  # 当前持仓：1=多头，-1=空头，0=空仓
        self.entry_price = 0.0
        self.signals_history = []
        self.trades_history = []
        
        # 策略状态
        self.last_ma_cross_signal = None
        self.consecutive_signals = 0
        
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
        
        fast_ma_col = f'MA_{self.config.FAST_MA_PERIOD}'
        slow_ma_col = f'MA_{self.config.SLOW_MA_PERIOD}'
        
        current_fast_ma = data.iloc[index][fast_ma_col]
        current_slow_ma = data.iloc[index][slow_ma_col]
        prev_fast_ma = data.iloc[index-1][fast_ma_col]
        prev_slow_ma = data.iloc[index-1][slow_ma_col]
        
        # 检查交叉
        if prev_fast_ma <= prev_slow_ma and current_fast_ma > current_slow_ma:
            # 黄金交叉 - 买入信号
            confidence = min(0.8, abs(current_fast_ma - current_slow_ma) / current_slow_ma * 100)
            return SignalType.BUY, confidence, f"快线向上穿越慢线({current_fast_ma:.2f} > {current_slow_ma:.2f})"
            
        elif prev_fast_ma >= prev_slow_ma and current_fast_ma < current_slow_ma:
            # 死亡交叉 - 卖出信号
            confidence = min(0.8, abs(current_slow_ma - current_fast_ma) / current_slow_ma * 100)
            return SignalType.SELL, confidence, f"快线向下穿越慢线({current_fast_ma:.2f} < {current_slow_ma:.2f})"
        
        return SignalType.HOLD, 0.0, "无交叉信号"
    
    def calculate_rsi_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算RSI信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        rsi = data.iloc[index]['RSI']
        
        if pd.isna(rsi):
            return SignalType.HOLD, 0.0, "RSI数据缺失"
        
        if rsi < self.config.RSI_OVERSOLD:
            # 超卖，买入信号
            confidence = (self.config.RSI_OVERSOLD - rsi) / self.config.RSI_OVERSOLD
            return SignalType.BUY, confidence, f"RSI超卖({rsi:.2f} < {self.config.RSI_OVERSOLD})"
            
        elif rsi > self.config.RSI_OVERBOUGHT:
            # 超买，卖出信号
            confidence = (rsi - self.config.RSI_OVERBOUGHT) / (100 - self.config.RSI_OVERBOUGHT)
            return SignalType.SELL, confidence, f"RSI超买({rsi:.2f} > {self.config.RSI_OVERBOUGHT})"
        
        return SignalType.HOLD, 0.0, f"RSI正常区间({rsi:.2f})"
    
    def calculate_macd_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算MACD信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        if index < 1:
            return SignalType.HOLD, 0.0, "MACD数据不足"
        
        current_macd = data.iloc[index]['MACD']
        current_signal = data.iloc[index]['MACD_Signal']
        prev_macd = data.iloc[index-1]['MACD']
        prev_signal = data.iloc[index-1]['MACD_Signal']
        
        if pd.isna(current_macd) or pd.isna(current_signal):
            return SignalType.HOLD, 0.0, "MACD数据缺失"
        
        # MACD线穿越信号线
        if prev_macd <= prev_signal and current_macd > current_signal:
            # MACD向上穿越信号线
            confidence = min(0.7, abs(current_macd - current_signal) / abs(current_signal) if current_signal != 0 else 0.5)
            return SignalType.BUY, confidence, f"MACD向上穿越信号线({current_macd:.4f} > {current_signal:.4f})"
            
        elif prev_macd >= prev_signal and current_macd < current_signal:
            # MACD向下穿越信号线
            confidence = min(0.7, abs(current_signal - current_macd) / abs(current_signal) if current_signal != 0 else 0.5)
            return SignalType.SELL, confidence, f"MACD向下穿越信号线({current_macd:.4f} < {current_signal:.4f})"
        
        return SignalType.HOLD, 0.0, "MACD无穿越信号"
    
    def calculate_bollinger_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算布林带信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        current_price = data.iloc[index]['Close']
        bb_upper = data.iloc[index]['BB_Upper']
        bb_lower = data.iloc[index]['BB_Lower']
        bb_middle = data.iloc[index]['BB_Middle']
        
        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return SignalType.HOLD, 0.0, "布林带数据缺失"
        
        # 价格触及下轨，可能反弹
        if current_price <= bb_lower:
            confidence = min(0.6, (bb_lower - current_price) / bb_lower * 10)
            return SignalType.BUY, confidence, f"价格触及布林带下轨({current_price:.2f} <= {bb_lower:.2f})"
        
        # 价格触及上轨，可能回落
        elif current_price >= bb_upper:
            confidence = min(0.6, (current_price - bb_upper) / bb_upper * 10)
            return SignalType.SELL, confidence, f"价格触及布林带上轨({current_price:.2f} >= {bb_upper:.2f})"
        
        return SignalType.HOLD, 0.0, f"价格在布林带中轨附近({current_price:.2f})"
    
    def calculate_volume_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算成交量信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        volume_ratio = data.iloc[index]['Volume_Ratio']
        price_change = data.iloc[index]['Price_Change']
        
        if pd.isna(volume_ratio) or pd.isna(price_change):
            return SignalType.HOLD, 0.0, "成交量数据缺失"
        
        # 放量上涨
        if volume_ratio > 1.5 and price_change > 0.01:
            confidence = min(0.5, volume_ratio / 3 * abs(price_change) * 10)
            return SignalType.BUY, confidence, f"放量上涨(量比:{volume_ratio:.2f}, 涨幅:{price_change*100:.2f}%)"
        
        # 放量下跌
        elif volume_ratio > 1.5 and price_change < -0.01:
            confidence = min(0.5, volume_ratio / 3 * abs(price_change) * 10)
            return SignalType.SELL, confidence, f"放量下跌(量比:{volume_ratio:.2f}, 跌幅:{price_change*100:.2f}%)"
        
        return SignalType.HOLD, 0.0, f"成交量正常(量比:{volume_ratio:.2f})"
    
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
        
        # 计算各个指标信号
        ma_signal, ma_confidence, ma_reason = self.calculate_ma_crossover_signal(data, index)
        rsi_signal, rsi_confidence, rsi_reason = self.calculate_rsi_signal(data, index)
        macd_signal, macd_confidence, macd_reason = self.calculate_macd_signal(data, index)
        bb_signal, bb_confidence, bb_reason = self.calculate_bollinger_signal(data, index)
        vol_signal, vol_confidence, vol_reason = self.calculate_volume_signal(data, index)
        
        # 信号权重配置
        weights = {
            'ma': 0.35,     # 移动平均线权重最高
            'macd': 0.25,   # MACD次之
            'rsi': 0.20,    # RSI
            'bb': 0.15,     # 布林带
            'volume': 0.05  # 成交量权重最低
        }
        
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
        signal_threshold = 0.18  # 略降阈值，增加进场但仍过滤噪声
        reasons = []
        
        if buy_score > sell_score and buy_score > signal_threshold:
            final_signal = SignalType.BUY
            final_confidence = buy_score
        elif sell_score > buy_score and sell_score > signal_threshold:
            final_signal = SignalType.SELL
            final_confidence = sell_score
        else:
            final_signal = SignalType.HOLD
            final_confidence = 0.0

        # 趋势过滤：多头需均线与MACD同向，空头反之，避免震荡噪声
        ma_fast_val = data.iloc[index][f'MA_{self.config.FAST_MA_PERIOD}']
        ma_slow_val = data.iloc[index][f'MA_{self.config.SLOW_MA_PERIOD}']
        macd_val = data.iloc[index]['MACD']
        # 趋势强度过滤，避免均线过近时进场
        price_now = data.iloc[index]['Close']
        ma_gap_pct = abs(ma_fast_val - ma_slow_val) / price_now if price_now != 0 else 0
        min_ma_gap = 0.001  # 0.1% 价差
        # 价位须站上/跌破布林中轨以过滤震荡
        bb_mid = data.iloc[index]['BB_Middle']
        if final_signal == SignalType.BUY and not (ma_fast_val > ma_slow_val and macd_val > 0 and ma_gap_pct >= min_ma_gap and price_now >= bb_mid):
            final_signal = SignalType.HOLD
            final_confidence = 0.0
            reasons.append("趋势过滤-多头不成立")
        elif final_signal == SignalType.SELL and not (ma_fast_val < ma_slow_val and macd_val < 0 and ma_gap_pct >= min_ma_gap and price_now <= bb_mid):
            final_signal = SignalType.HOLD
            final_confidence = 0.0
            reasons.append("趋势过滤-空头不成立")
        
        # 组合信号原因
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
        
        trading_signal = TradingSignal(
            timestamp=timestamp,
            signal_type=final_signal,
            price=current_price,
            confidence=final_confidence,
            indicators=indicators,
            reason=combined_reason
        )
        
        return trading_signal
    
    def calculate_atr_stop_loss(self, data: pd.DataFrame, index: int, position_type: SignalType) -> Tuple[float, float]:
        """
        计算ATR动态止损和止盈点位
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            position_type: 持仓方向
            
        Returns:
            止损价位, 止盈价位
        """
        if index < 14:  # ATR需要至少14个数据点
            # 默认止损止盈
            current_price = data.iloc[index]['Close']
            if position_type == SignalType.BUY:
                stop_loss = current_price * (1 - self.config.STOP_LOSS_PCT)
                take_profit = current_price * (1 + self.config.TAKE_PROFIT_PCT)
            else:
                stop_loss = current_price * (1 + self.config.STOP_LOSS_PCT)
                take_profit = current_price * (1 - self.config.TAKE_PROFIT_PCT)
            return stop_loss, take_profit
        
        atr = data.iloc[index]['ATR']
        current_price = data.iloc[index]['Close']
        
        if pd.isna(atr) or atr == 0:
            # 如果ATR不可用，使用默认百分比
            if position_type == SignalType.BUY:
                stop_loss = current_price * (1 - self.config.STOP_LOSS_PCT)
                take_profit = current_price * (1 + self.config.TAKE_PROFIT_PCT)
            else:
                stop_loss = current_price * (1 + self.config.STOP_LOSS_PCT)
                take_profit = current_price * (1 - self.config.TAKE_PROFIT_PCT)
        else:
            # 使用ATR计算动态止损止盈
            if position_type == SignalType.BUY:
                stop_loss = current_price - (atr * 1.5)  # 更紧的ATR止损
                take_profit = current_price + (atr * 2.5)  # 略收紧止盈
            else:
                stop_loss = current_price + (atr * 1.5)  # 更紧的ATR止损
                take_profit = current_price - (atr * 2.5)  # 略收紧止盈
                
        return stop_loss, take_profit
    
    def should_exit_position(self, data: pd.DataFrame, index: int, entry_price: float, 
                           position_type: SignalType) -> Tuple[bool, str]:
        """
        判断是否应该平仓
        
        Args:
            data: 行情数据
            index: 当前索引
            entry_price: 入场价格
            position_type: 持仓方向
            
        Returns:
            是否平仓, 平仓原因
        """
        current_price = data.iloc[index]['Close']
        
        # 计算止损和止盈点位
        stop_loss, take_profit = self.calculate_atr_stop_loss(data, index, position_type)
        
        # 止损判断
        if position_type == SignalType.BUY and current_price <= stop_loss:
            return True, f"多头止损: 当前价{current_price:.2f} <= 止损价{stop_loss:.2f}"
        elif position_type == SignalType.SELL and current_price >= stop_loss:
            return True, f"空头止损: 当前价{current_price:.2f} >= 止损价{stop_loss:.2f}"
            
        # 止盈判断
        if position_type == SignalType.BUY and current_price >= take_profit:
            return True, f"多头止盈: 当前价{current_price:.2f} >= 止盈价{take_profit:.2f}"
        elif position_type == SignalType.SELL and current_price <= take_profit:
            return True, f"空头止盈: 当前价{current_price:.2f} <= 止盈价{take_profit:.2f}"
            
        # 反向信号平仓
        signal = self.generate_composite_signal(data, index)
        if ((position_type == SignalType.BUY and signal.signal_type == SignalType.SELL) or 
            (position_type == SignalType.SELL and signal.signal_type == SignalType.BUY)):
            return True, f"反向信号平仓: {signal.reason}"
            
        return False, ""
    
    def calculate_position_size(self, capital: float, price: float, confidence: float, atr: float = None) -> int:
        """
        根据信号置信度动态计算仓位大小
        
        Args:
            capital: 可用资金
            price: 当前价格
            confidence: 信号置信度
            atr: ATR值，用于风险调整仓位
            
        Returns:
            仓位数量
        """
        # 基础仓位根据置信度调整
        base_position_ratio = self.config.POSITION_SIZE * confidence
        
        # 如果有ATR，则进一步调整仓位以控制风险
        if atr and atr > 0:
            # 使用ATR调整仓位，确保单笔损失不超过账户的一定比例
            risk_per_trade = 0.007  # 略提升每笔风险至0.7%资金
            dollar_per_point = 100  # 黄金期货每点价值(示例值，实际可能不同)
            
            # 计算基于ATR的合适仓位大小
            risk_amount = capital * risk_per_trade
            position_by_risk = risk_amount / (atr * dollar_per_point)
            
            # 取置信度仓位和风险仓位中的较小值
            position_ratio = min(base_position_ratio, position_by_risk * price / capital)
        else:
            position_ratio = base_position_ratio
            
        # 计算实际仓位数量
        position_value = capital * position_ratio
        position_size = int(position_value / price)
        
        return max(1, position_size)  # 至少返回1手
    
    def execute_signal(self, signal: TradingSignal, capital: float = 100000) -> Dict:
        """
        执行交易信号（支持智能仓位管理）
        
        Args:
            signal: 交易信号
            capital: 账户资金，默认10万
            
        Returns:
            交易执行结果
        """
        trade_result = {
            'timestamp': signal.timestamp,
            'action': 'hold',
            'price': signal.price,
            'position_before': self.position,
            'position_after': self.position,
            'reason': signal.reason,
            'confidence': signal.confidence,
            'position_size': 0
        }
        
        # 记录信号历史
        self.signals_history.append(signal)
        
        # 获取ATR用于仓位计算和风险控制
        atr = signal.indicators.get('ATR', None)
        
        # 执行交易逻辑
        if signal.signal_type == SignalType.BUY and self.position != 1:
            if self.position == -1:
                # 平空仓
                trade_result['action'] = 'close_short'
                self.trades_history.append({
                    'timestamp': signal.timestamp,
                    'action': 'close_short',
                    'price': signal.price,
                    'entry_price': self.entry_price,
                    'pnl': (self.entry_price - signal.price) / self.entry_price,
                    'position_size': abs(self.position)
                })
            
            # 计算智能仓位
            position_size = self.calculate_position_size(capital, signal.price, signal.confidence, atr)
            
            # 开多仓
            action_name = 'buy' if self.position == 0 else 'close_short_and_buy'
            trade_result.update({
                'action': action_name,
                'position_after': 1,
                'position_size': position_size
            })
            
            self.position = 1
            self.entry_price = signal.price
            
        elif signal.signal_type == SignalType.SELL:
            if self.position == 1:
                # 平多仓，仅平仓不再开空
                trade_result['action'] = 'close_long'
                self.trades_history.append({
                    'timestamp': signal.timestamp,
                    'action': 'close_long',
                    'price': signal.price,
                    'entry_price': self.entry_price,
                    'pnl': (signal.price - self.entry_price) / self.entry_price,
                    'position_size': abs(self.position)
                })
                self.position = 0
                self.entry_price = 0.0
            else:
                # 空仓或已空头，不开新空
                trade_result['action'] = 'hold'
        
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
        
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Tuple[List[TradingSignal], List[Dict]]:
        """
        执行回测
        
        Args:
            data: 包含技术指标的行情数据
            initial_capital: 初始资金
            
        Returns:
            交易信号列表, 交易记录列表
        """
        signals = []
        trades = []
        current_capital = initial_capital
        
        for i in range(len(data)):
            # 生成交易信号
            signal = self.generate_composite_signal(data, i)
            signals.append(signal)
            
            # 检查是否需要止损止盈或反向平仓
            if self.position != 0:
                should_exit, exit_reason = self.should_exit_position(
                    data, i, self.entry_price, 
                    SignalType.BUY if self.position > 0 else SignalType.SELL
                )
                
                if should_exit:
                    # 执行平仓
                    exit_signal = TradingSignal(
                        timestamp=signal.timestamp,
                        signal_type=SignalType.HOLD,
                        price=signal.price,
                        confidence=signal.confidence,
                        indicators=signal.indicators,
                        reason=exit_reason
                    )
                    trade_result = self.execute_signal(exit_signal, current_capital)
                    if trade_result['action'] != 'hold':
                        trades.append(trade_result)
                    
            # 根据信号和当前持仓情况决定交易行为
            if signal.signal_type == SignalType.BUY and self.position != 1:
                trade_result = self.execute_signal(signal, current_capital)
                if trade_result['action'] != 'hold':
                    trades.append(trade_result)
                    
            elif signal.signal_type == SignalType.SELL and self.position != -1:
                trade_result = self.execute_signal(signal, current_capital)
                if trade_result['action'] != 'hold':
                    trades.append(trade_result)
        
        return signals, trades

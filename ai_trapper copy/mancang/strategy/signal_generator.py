"""
信号生成器
负责生成买入和卖出信号
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from mancang.utils.indicators import TechnicalIndicators


class SignalGenerator:
    """交易信号生成器"""
    
    def __init__(self, config: Dict):
        """
        初始化信号生成器
        
        Args:
            config: 策略配置字典
        """
        self.config = config
    
    def generate_entry_signal(self, data: pd.DataFrame, 
                             signal_type: str = 'pullback') -> Tuple[bool, str, float]:
        """
        生成买入信号
        
        Args:
            data: 股票数据
            signal_type: 信号类型 ('pullback', 'rotation', 'chase')
            
        Returns:
            (是否买入, 原因, 建议仓位比例)
        """
        if signal_type == 'pullback':
            return self._dragon_head_pullback_signal(data)
        elif signal_type == 'rotation':
            return self._sector_rotation_signal(data)
        elif signal_type == 'chase':
            return self._chase_signal(data)
        else:
            return False, "未知信号类型", 0.0
    
    def _dragon_head_pullback_signal(self, data: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        龙头回调低吸信号
        
        Args:
            data: 股票数据
            
        Returns:
            (是否买入, 原因, 建议仓位比例)
        """
        if len(data) < 10:
            return False, "数据不足", 0.0
        
        # 1. 检查连板数（不追高）
        consecutive_boards = TechnicalIndicators.count_consecutive_limit_up(data).iloc[-1]
        
        if consecutive_boards > self.config['chase_limit']:
            return False, f"连板数过高({consecutive_boards}板)，不追高", 0.0
        
        # 2. 检查是否处于上升趋势
        if not TechnicalIndicators.is_uptrend(data, period=self.config['pullback_min_uptrend_days']).iloc[-1]:
            return False, "未处于上升趋势", 0.0
        
        # 3. 检查是否回踩5日线
        is_pullback = TechnicalIndicators.detect_pullback_to_ma(
            data,
            ma_period=self.config['ma_stop_loss'],
            tolerance=self.config['pullback_ma5_tolerance']
        ).iloc[-1]
        
        if not is_pullback:
            return False, "未回踩5日线", 0.0
        
        # 4. 确认未跌破5日线
        ma5 = TechnicalIndicators.calculate_ma(data, period=self.config['ma_stop_loss'])
        current_close = data['close'].iloc[-1]
        
        if current_close < ma5.iloc[-1]:
            return False, "已跌破5日线", 0.0
        
        # 5. 计算建议仓位（基于信号强度）
        signal_strength = self._calculate_signal_strength(data, 'pullback')
        position_ratio = self.config['single_pos_limit'] * signal_strength
        
        return True, "龙头回调低吸信号", position_ratio
    
    def _sector_rotation_signal(self, data: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        板块轮动信号
        
        Args:
            data: 股票数据
            
        Returns:
            (是否买入, 原因, 建议仓位比例)
        """
        if len(data) < 10:
            return False, "数据不足", 0.0
        
        # 1. 检查是否处于相对低位
        recent_high = data['high'].iloc[-5:].max()
        current_price = data['close'].iloc[-1]
        
        pullback_ratio = (recent_high - current_price) / recent_high
        
        if pullback_ratio < 0.03:  # 至少回调3%
            return False, "未充分回调", 0.0
        
        # 2. 检查是否在5日线附近
        is_near_ma5 = TechnicalIndicators.detect_pullback_to_ma(
            data,
            ma_period=self.config['ma_stop_loss'],
            tolerance=self.config['pullback_ma5_tolerance']
        ).iloc[-1]
        
        if not is_near_ma5:
            return False, "未在5日线附近", 0.0
        
        # 3. 检查量能
        volume_ratio = TechnicalIndicators.calculate_volume_ratio(data, period=5).iloc[-1]
        
        if volume_ratio < 1.5:
            return False, "量能不足", 0.0
        
        # 4. 计算建议仓位
        signal_strength = self._calculate_signal_strength(data, 'rotation')
        position_ratio = self.config['single_pos_limit'] * signal_strength
        
        return True, "板块轮动低吸信号", position_ratio
    
    def _chase_signal(self, data: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        半路追涨信号
        
        Args:
            data: 股票数据
            
        Returns:
            (是否买入, 原因, 建议仓位比例)
        """
        if len(data) < 5:
            return False, "数据不足", 0.0
        
        latest = data.iloc[-1]
        prev_close = data['close'].iloc[-2]
        
        # 1. 检查涨幅范围
        pct_change = (latest['close'] - prev_close) / prev_close
        
        if not (self.config['chase_min_gain'] <= pct_change <= self.config['chase_max_gain']):
            return False, f"涨幅不在目标区间({pct_change:.2%})", 0.0
        
        # 2. 检查量比
        volume_ratio = TechnicalIndicators.calculate_volume_ratio(data, period=5).iloc[-1]
        
        if volume_ratio < self.config['chase_volume_ratio']:
            return False, f"量比不足({volume_ratio:.2f})", 0.0
        
        # 3. 检查是否在5日线上方
        ma5 = TechnicalIndicators.calculate_ma(data, period=self.config['ma_stop_loss'])
        
        if latest['close'] < ma5.iloc[-1]:
            return False, "未站上5日线", 0.0
        
        # 4. 检查连板数
        consecutive_boards = TechnicalIndicators.count_consecutive_limit_up(data).iloc[-1]
        
        if consecutive_boards > self.config['chase_limit']:
            return False, f"连板数过高({consecutive_boards}板)", 0.0
        
        # 5. 计算建议仓位（追涨仓位较小）
        signal_strength = self._calculate_signal_strength(data, 'chase')
        position_ratio = self.config['single_pos_limit'] * signal_strength * 0.8  # 追涨降低仓位
        
        return True, "半路追涨信号", position_ratio
    
    def generate_exit_signal(self, data: pd.DataFrame, 
                            entry_price: float,
                            position_ratio: float = 1.0) -> Tuple[bool, str, float]:
        """
        生成卖出信号
        
        Args:
            data: 股票数据
            entry_price: 买入价格
            position_ratio: 当前持仓比例
            
        Returns:
            (是否卖出, 原因, 卖出比例)
        """
        if len(data) < 2:
            return False, "数据不足", 0.0
        
        latest = data.iloc[-1]
        
        # 1. 强制止损：跌破5日线（最高优先级）
        ma5 = TechnicalIndicators.calculate_ma(data, period=self.config['ma_stop_loss'])
        
        if latest['close'] < ma5.iloc[-1]:
            if self.config['stop_loss_strict']:
                return True, "跌破5日线，强制止损", 1.0
            elif self.config['stop_loss_mid_term']:
                # 检查7日线
                ma7 = TechnicalIndicators.calculate_ma(data, period=self.config['ma_mid_term'])
                if latest['close'] < ma7.iloc[-1]:
                    return True, "跌破7日线，中线止损", 1.0
        
        # 2. 止盈：冲高回落
        is_surge_pullback = TechnicalIndicators.detect_surge_and_pullback(
            data,
            surge_threshold=self.config['take_profit_surge'],
            pullback_threshold=self.config['take_profit_pullback']
        ).iloc[-1]
        
        if is_surge_pullback and position_ratio > 0.5:
            return True, "冲高回落，止盈50%", self.config['take_profit_ratio']
        
        # 3. MACD顶背离
        is_divergence, div_type = TechnicalIndicators.detect_macd_divergence(data, period=5)
        
        if is_divergence and div_type == "顶背离":
            return True, "MACD顶背离，减仓", 0.5
        
        # 4. 盈利保护：大幅盈利后回撤
        current_profit = (latest['close'] - entry_price) / entry_price
        
        if current_profit > 0.15:  # 盈利超过15%
            # 检查是否回撤超过5%
            recent_high = data['high'].iloc[-5:].max()
            pullback = (recent_high - latest['close']) / recent_high
            
            if pullback > 0.05:
                return True, "大幅盈利后回撤，止盈", 0.5
        
        return False, "持有", 0.0
    
    def _calculate_signal_strength(self, data: pd.DataFrame, signal_type: str) -> float:
        """
        计算信号强度
        
        Args:
            data: 股票数据
            signal_type: 信号类型
            
        Returns:
            信号强度（0-1）
        """
        strength = 0.5  # 基础强度
        
        try:
            # 1. 量能因子
            volume_ratio = TechnicalIndicators.calculate_volume_ratio(data, period=5).iloc[-1]
            if volume_ratio > 2.0:
                strength += 0.2
            elif volume_ratio > 1.5:
                strength += 0.1
            
            # 2. 趋势因子
            if TechnicalIndicators.is_uptrend(data, period=3).iloc[-1]:
                strength += 0.15
            
            # 3. 位置因子（相对5日线）
            ma5 = TechnicalIndicators.calculate_ma(data, period=5)
            distance_to_ma5 = (data['close'].iloc[-1] - ma5.iloc[-1]) / ma5.iloc[-1]
            
            if 0 <= distance_to_ma5 <= 0.02:  # 在5日线附近
                strength += 0.15
            
        except Exception as e:
            pass
        
        return min(strength, 1.0)
    
    def check_market_sentiment(self, market_data: Dict) -> Tuple[bool, int]:
        """
        检查市场情绪
        
        Args:
            market_data: 市场数据
            
        Returns:
            (是否可以交易, 情绪分数)
        """
        if not market_data:
            return False, 0
        
        # 计算市场情绪分数
        total_stocks = market_data.get('total_stocks', 1)
        up_count = market_data.get('up_count', 0)
        limit_up_count = market_data.get('limit_up_count', 0)
        
        # 情绪分数 = 上涨家数占比 * 50 + 涨停家数占比 * 50
        sentiment_score = (up_count / total_stocks * 50) + (limit_up_count / total_stocks * 1000)
        sentiment_score = min(sentiment_score, 100)
        
        # 判断是否可以交易
        can_trade = sentiment_score >= self.config['min_market_sentiment']
        
        return can_trade, int(sentiment_score)

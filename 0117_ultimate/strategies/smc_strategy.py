"""
SMC市场结构策略
"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class SMCStrategy(BaseStrategy):
    """SMC市场结构策略"""
    
    def __init__(self, weight: float = 0.05, enabled: bool = True,
                 swing_window: int = 3, ob_lookback: int = 10, **kwargs):
        """
        初始化SMC策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            swing_window: 摆动点检测窗口
            ob_lookback: 订单块回溯周期
        """
        super().__init__(
            name="SMC_Strategy",
            weight=weight,
            enabled=enabled,
            swing_window=swing_window,
            ob_lookback=ob_lookback,
            **kwargs
        )
        
        # SMC结构缓存
        self.swing_highs = []
        self.swing_lows = []
        self.bos_signals = []
        self.ch_signals = []
        self.order_blocks = []
    
    def _validate_params(self):
        """验证参数"""
        if self.params['swing_window'] < 1:
            raise ValueError("摆动点窗口必须大于0")
        if self.params['ob_lookback'] < 1:
            raise ValueError("订单块回溯周期必须大于0")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return []  # SMC使用原始OHLC数据
    
    def update_structure(self, data: pd.DataFrame):
        """更新SMC市场结构"""
        from indicators import TechnicalIndicators
        
        # 检测摆动点
        self.swing_highs, self.swing_lows = TechnicalIndicators.find_swings(
            data['high'], data['low'], self.params['swing_window']
        )
        
        # 检测BOS和CH
        self.bos_signals, self.ch_signals = TechnicalIndicators.detect_bos_ch(
            data, self.swing_highs, self.swing_lows
        )
        
        # 检测订单块
        self.order_blocks = TechnicalIndicators.detect_order_blocks(
            data, self.bos_signals
        )
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算SMC结构信号"""
        current_price = data.iloc[index]['close']
        
        # 检查BOS信号（结构延续）
        if index in self.bos_signals:
            if index > 0:
                if data.iloc[index]['high'] > data.iloc[index - 1]['high']:
                    return StrategySignal(
                        timestamp=data.index[index],
                        signal_type=SignalType.BUY,
                        confidence=0.5,
                        price=current_price,
                        reason="BOS向上突破(结构延续)",
                        metadata={
                            'signal_type': 'BOS',
                            'direction': 'up',
                            'index': index
                        }
                    )
                else:
                    return StrategySignal(
                        timestamp=data.index[index],
                        signal_type=SignalType.SELL,
                        confidence=0.5,
                        price=current_price,
                        reason="BOS向下突破(结构延续)",
                        metadata={
                            'signal_type': 'BOS',
                            'direction': 'down',
                            'index': index
                        }
                    )
        
        # 检查CH信号（趋势反转）
        if index in self.ch_signals:
            if index > 0:
                if data.iloc[index]['high'] > data.iloc[index - 1]['high']:
                    return StrategySignal(
                        timestamp=data.index[index],
                        signal_type=SignalType.BUY,
                        confidence=0.7,
                        price=current_price,
                        reason="CH趋势反转向上",
                        metadata={
                            'signal_type': 'CH',
                            'direction': 'up',
                            'index': index
                        }
                    )
                else:
                    return StrategySignal(
                        timestamp=data.index[index],
                        signal_type=SignalType.SELL,
                        confidence=0.7,
                        price=current_price,
                        reason="CH趋势反转向下",
                        metadata={
                            'signal_type': 'CH',
                            'direction': 'down',
                            'index': index
                        }
                    )
        
        # 检查订单块区域
        for ob_idx, ob_low, ob_high in self.order_blocks:
            if ob_low <= current_price <= ob_high:
                if ob_idx < index - 5:  # 订单块形成至少5根K线前
                    return StrategySignal(
                        timestamp=data.index[index],
                        signal_type=SignalType.HOLD,
                        confidence=0.3,
                        price=current_price,
                        reason=f"价格在订单块区域({ob_low:.2f}-{ob_high:.2f})",
                        metadata={
                            'signal_type': 'OrderBlock',
                            'ob_low': ob_low,
                            'ob_high': ob_high,
                            'ob_index': ob_idx
                        }
                    )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=current_price,
            reason="无SMC结构信号",
            metadata={}
        )

"""
UT Bot追踪止损策略
"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class UTBotStrategy(BaseStrategy):
    """UT Bot追踪止损策略"""
    
    def __init__(self, weight: float = 0.10, enabled: bool = True,
                 atr_period: int = 10, key_value: float = 1.2, **kwargs):
        """
        初始化UT Bot策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            atr_period: ATR周期
            key_value: 关键值（止损距离倍数）
        """
        super().__init__(
            name="UTBot_Strategy",
            weight=weight,
            enabled=enabled,
            atr_period=atr_period,
            key_value=key_value,
            **kwargs
        )
    
    def _validate_params(self):
        """验证参数"""
        if self.params['atr_period'] < 1:
            raise ValueError("ATR周期必须大于0")
        if self.params['key_value'] <= 0:
            raise ValueError("关键值必须大于0")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return ['UT_Bot_Stop']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算UT Bot趋势信号"""
        if index < 1:
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                reason="数据不足",
                metadata={}
            )
        
        current_price = data.iloc[index]['close']
        current_stop = data.iloc[index]['UT_Bot_Stop']
        prev_price = data.iloc[index - 1]['close']
        prev_stop = data.iloc[index - 1]['UT_Bot_Stop']
        
        if pd.isna(current_stop) or pd.isna(prev_stop):
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=current_price,
                reason="UT Bot数据缺失",
                metadata={}
            )
        
        # 价格突破止损线向上（趋势转多）
        if prev_price <= prev_stop and current_price > current_stop:
            confidence = 0.6
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=current_price,
                reason=f"价格突破UT Bot止损线向上({current_price:.2f} > {current_stop:.2f})",
                metadata={
                    'price': current_price,
                    'stop_line': current_stop,
                    'breakout_strength': (current_price - current_stop) / current_stop
                }
            )
        
        # 价格跌破止损线向下（趋势转空）
        elif prev_price >= prev_stop and current_price < current_stop:
            confidence = 0.6
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=current_price,
                reason=f"价格跌破UT Bot止损线向下({current_price:.2f} < {current_stop:.2f})",
                metadata={
                    'price': current_price,
                    'stop_line': current_stop,
                    'breakdown_strength': (current_stop - current_price) / current_stop
                }
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=current_price,
            reason="价格未突破UT Bot止损线",
            metadata={'price': current_price, 'stop_line': current_stop}
        )

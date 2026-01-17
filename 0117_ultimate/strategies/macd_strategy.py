"""
MACD交叉策略
"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class MACDStrategy(BaseStrategy):
    """MACD交叉策略"""
    
    def __init__(self, weight: float = 0.20, enabled: bool = True,
                 fast: int = 12, slow: int = 26, signal: int = 9, **kwargs):
        """
        初始化MACD策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        """
        super().__init__(
            name="MACD_Strategy",
            weight=weight,
            enabled=enabled,
            fast=fast,
            slow=slow,
            signal=signal,
            **kwargs
        )
    
    def _validate_params(self):
        """验证参数"""
        if self.params['fast'] >= self.params['slow']:
            raise ValueError("MACD快线周期必须小于慢线周期")
        if any(p < 1 for p in [self.params['fast'], self.params['slow'], self.params['signal']]):
            raise ValueError("MACD周期必须大于0")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return ['MACD', 'MACD_Signal', 'MACD_Hist']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算MACD交叉信号"""
        if index < 1:
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                reason="数据不足",
                metadata={}
            )
        
        current_macd = data.iloc[index]['MACD']
        current_signal = data.iloc[index]['MACD_Signal']
        prev_macd = data.iloc[index - 1]['MACD']
        prev_signal = data.iloc[index - 1]['MACD_Signal']
        
        if pd.isna(current_macd) or pd.isna(current_signal):
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                reason="MACD数据缺失",
                metadata={}
            )
        
        # MACD向上穿越信号线
        if prev_macd <= prev_signal and current_macd > current_signal:
            confidence = min(0.7, abs(current_macd - current_signal) / abs(current_signal) if current_signal != 0 else 0)
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"MACD金叉(MACD{current_macd:.4f} > 信号{current_signal:.4f})",
                metadata={
                    'macd': current_macd,
                    'signal': current_signal,
                    'histogram': data.iloc[index]['MACD_Hist']
                }
            )
        
        # MACD向下穿越信号线
        elif prev_macd >= prev_signal and current_macd < current_signal:
            confidence = min(0.7, abs(current_signal - current_macd) / abs(current_signal) if current_signal != 0 else 0)
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"MACD死叉(MACD{current_macd:.4f} < 信号{current_signal:.4f})",
                metadata={
                    'macd': current_macd,
                    'signal': current_signal,
                    'histogram': data.iloc[index]['MACD_Hist']
                }
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=data.iloc[index]['close'],
            reason="无MACD交叉",
            metadata={'macd': current_macd, 'signal': current_signal}
        )

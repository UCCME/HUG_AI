"""
RSI超买超卖策略
"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class RSIStrategy(BaseStrategy):
    """RSI超买超卖策略"""
    
    def __init__(self, weight: float = 0.15, enabled: bool = True,
                 period: int = 14, oversold: float = 30, overbought: float = 70, **kwargs):
        """
        初始化RSI策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            period: RSI周期
            oversold: 超卖阈值
            overbought: 超买阈值
        """
        super().__init__(
            name="RSI_Strategy",
            weight=weight,
            enabled=enabled,
            period=period,
            oversold=oversold,
            overbought=overbought,
            **kwargs
        )
    
    def _validate_params(self):
        """验证参数"""
        if not 0 < self.params['oversold'] < self.params['overbought'] < 100:
            raise ValueError("RSI阈值必须满足: 0 < oversold < overbought < 100")
        if self.params['period'] < 1:
            raise ValueError("RSI周期必须大于0")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return ['RSI']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算RSI信号"""
        rsi = data.iloc[index]['RSI']
        
        if pd.isna(rsi):
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                reason="RSI数据缺失",
                metadata={}
            )
        
        # 超卖买入
        if rsi < self.params['oversold']:
            confidence = (self.params['oversold'] - rsi) / self.params['oversold']
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"RSI超卖({rsi:.2f} < {self.params['oversold']})",
                metadata={'rsi': rsi, 'threshold': self.params['oversold']}
            )
        
        # 超买卖出
        elif rsi > self.params['overbought']:
            confidence = (rsi - self.params['overbought']) / (100 - self.params['overbought'])
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"RSI超买({rsi:.2f} > {self.params['overbought']})",
                metadata={'rsi': rsi, 'threshold': self.params['overbought']}
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=data.iloc[index]['close'],
            reason=f"RSI正常({rsi:.2f})",
            metadata={'rsi': rsi}
        )

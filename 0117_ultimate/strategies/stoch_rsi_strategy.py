"""
StochRSI超买超卖策略
"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class StochRSIStrategy(BaseStrategy):
    """StochRSI超买超卖策略"""
    
    def __init__(self, weight: float = 0.10, enabled: bool = True,
                 period: int = 14, k_period: int = 3, d_period: int = 3,
                 oversold: float = 20, overbought: float = 80, **kwargs):
        """
        初始化StochRSI策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            period: RSI周期
            k_period: K线平滑周期
            d_period: D线平滑周期
            oversold: 超卖阈值
            overbought: 超买阈值
        """
        super().__init__(
            name="StochRSI_Strategy",
            weight=weight,
            enabled=enabled,
            period=period,
            k_period=k_period,
            d_period=d_period,
            oversold=oversold,
            overbought=overbought,
            **kwargs
        )
    
    def _validate_params(self):
        """验证参数"""
        if not 0 < self.params['oversold'] < self.params['overbought'] < 100:
            raise ValueError("StochRSI阈值必须满足: 0 < oversold < overbought < 100")
        if any(p < 1 for p in [self.params['period'], self.params['k_period'], self.params['d_period']]):
            raise ValueError("周期必须大于0")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return ['StochRSI_K', 'StochRSI_D']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算StochRSI信号"""
        stoch_k = data.iloc[index]['StochRSI_K']
        stoch_d = data.iloc[index]['StochRSI_D']
        
        if pd.isna(stoch_k) or pd.isna(stoch_d):
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                reason="StochRSI数据缺失",
                metadata={}
            )
        
        # 超卖区金叉
        if stoch_k < self.params['oversold'] and stoch_k > stoch_d:
            confidence = (self.params['oversold'] - stoch_k) / self.params['oversold']
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"StochRSI超卖区金叉(K:{stoch_k:.2f} > D:{stoch_d:.2f})",
                metadata={
                    'stoch_k': stoch_k,
                    'stoch_d': stoch_d,
                    'oversold_threshold': self.params['oversold']
                }
            )
        
        # 超买区死叉
        elif stoch_k > self.params['overbought'] and stoch_k < stoch_d:
            confidence = (stoch_k - self.params['overbought']) / (100 - self.params['overbought'])
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"StochRSI超买区死叉(K:{stoch_k:.2f} < D:{stoch_d:.2f})",
                metadata={
                    'stoch_k': stoch_k,
                    'stoch_d': stoch_d,
                    'overbought_threshold': self.params['overbought']
                }
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=data.iloc[index]['close'],
            reason=f"StochRSI正常(K:{stoch_k:.2f}, D:{stoch_d:.2f})",
            metadata={'stoch_k': stoch_k, 'stoch_d': stoch_d}
        )

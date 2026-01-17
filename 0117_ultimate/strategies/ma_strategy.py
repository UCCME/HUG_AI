"""
移动平均线交叉策略
"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class MAStrategy(BaseStrategy):
    """移动平均线交叉策略"""
    
    def __init__(self, weight: float = 0.25, enabled: bool = True, 
                 fast_period: int = 72, slow_period: int = 216, **kwargs):
        """
        初始化MA策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            fast_period: 快线周期
            slow_period: 慢线周期
        """
        super().__init__(
            name="MA_Strategy",
            weight=weight,
            enabled=enabled,
            fast_period=fast_period,
            slow_period=slow_period,
            **kwargs
        )
    
    def _validate_params(self):
        """验证参数"""
        if self.params['fast_period'] >= self.params['slow_period']:
            raise ValueError("快线周期必须小于慢线周期")
        if self.params['fast_period'] < 1 or self.params['slow_period'] < 1:
            raise ValueError("周期必须大于0")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return [
            f"MA_{self.params['fast_period']}",
            f"MA_{self.params['slow_period']}"
        ]
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算MA交叉信号"""
        if index < 1:
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                reason="数据不足",
                metadata={}
            )
        
        fast_col = f"MA_{self.params['fast_period']}"
        slow_col = f"MA_{self.params['slow_period']}"
        
        current_fast = data.iloc[index][fast_col]
        current_slow = data.iloc[index][slow_col]
        prev_fast = data.iloc[index - 1][fast_col]
        prev_slow = data.iloc[index - 1][slow_col]
        
        if pd.isna(current_fast) or pd.isna(current_slow):
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                reason="指标数据缺失",
                metadata={}
            )
        
        # 黄金交叉
        if prev_fast <= prev_slow and current_fast > current_slow:
            confidence = min(0.8, abs(current_fast - current_slow) / current_slow * 100)
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"MA黄金交叉(快线{current_fast:.2f} > 慢线{current_slow:.2f})",
                metadata={
                    'fast_ma': current_fast,
                    'slow_ma': current_slow,
                    'cross_strength': abs(current_fast - current_slow) / current_slow
                }
            )
        
        # 死亡交叉
        elif prev_fast >= prev_slow and current_fast < current_slow:
            confidence = min(0.8, abs(current_slow - current_fast) / current_slow * 100)
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"MA死亡交叉(快线{current_fast:.2f} < 慢线{current_slow:.2f})",
                metadata={
                    'fast_ma': current_fast,
                    'slow_ma': current_slow,
                    'cross_strength': abs(current_slow - current_fast) / current_slow
                }
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=data.iloc[index]['close'],
            reason="无交叉信号",
            metadata={'fast_ma': current_fast, 'slow_ma': current_slow}
        )

"""
布林带突破策略
"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class BollingerStrategy(BaseStrategy):
    """布林带突破策略"""
    
    def __init__(self, weight: float = 0.10, enabled: bool = True,
                 period: int = 20, std_dev: float = 2.0, **kwargs):
        """
        初始化布林带策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            period: 布林带周期
            std_dev: 标准差倍数
        """
        super().__init__(
            name="Bollinger_Strategy",
            weight=weight,
            enabled=enabled,
            period=period,
            std_dev=std_dev,
            **kwargs
        )
    
    def _validate_params(self):
        """验证参数"""
        if self.params['period'] < 1:
            raise ValueError("布林带周期必须大于0")
        if self.params['std_dev'] <= 0:
            raise ValueError("标准差倍数必须大于0")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return ['BB_Upper', 'BB_Middle', 'BB_Lower']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算布林带突破信号"""
        current_price = data.iloc[index]['close']
        bb_upper = data.iloc[index]['BB_Upper']
        bb_lower = data.iloc[index]['BB_Lower']
        bb_middle = data.iloc[index]['BB_Middle']
        
        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=current_price,
                reason="布林带数据缺失",
                metadata={}
            )
        
        # 价格触及下轨（均值回归买入）
        if current_price <= bb_lower:
            confidence = min(0.6, (bb_lower - current_price) / bb_lower * 10)
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=current_price,
                reason=f"价格触及布林带下轨({current_price:.2f} <= {bb_lower:.2f})",
                metadata={
                    'price': current_price,
                    'bb_upper': bb_upper,
                    'bb_middle': bb_middle,
                    'bb_lower': bb_lower,
                    'distance_from_lower': (bb_lower - current_price) / bb_lower
                }
            )
        
        # 价格触及上轨（均值回归卖出）
        elif current_price >= bb_upper:
            confidence = min(0.6, (current_price - bb_upper) / bb_upper * 10)
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=current_price,
                reason=f"价格触及布林带上轨({current_price:.2f} >= {bb_upper:.2f})",
                metadata={
                    'price': current_price,
                    'bb_upper': bb_upper,
                    'bb_middle': bb_middle,
                    'bb_lower': bb_lower,
                    'distance_from_upper': (current_price - bb_upper) / bb_upper
                }
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=current_price,
            reason="价格在布林带内",
            metadata={
                'price': current_price,
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower
            }
        )

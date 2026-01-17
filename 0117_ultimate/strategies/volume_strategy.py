"""
成交量确认策略
"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class VolumeStrategy(BaseStrategy):
    """成交量确认策略"""
    
    def __init__(self, weight: float = 0.05, enabled: bool = True,
                 volume_threshold: float = 1.5, price_change_threshold: float = 0.01, **kwargs):
        """
        初始化成交量策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            volume_threshold: 成交量放大阈值（倍数）
            price_change_threshold: 价格变化阈值
        """
        super().__init__(
            name="Volume_Strategy",
            weight=weight,
            enabled=enabled,
            volume_threshold=volume_threshold,
            price_change_threshold=price_change_threshold,
            **kwargs
        )
    
    def _validate_params(self):
        """验证参数"""
        if self.params['volume_threshold'] <= 1:
            raise ValueError("成交量阈值必须大于1")
        if self.params['price_change_threshold'] <= 0:
            raise ValueError("价格变化阈值必须大于0")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return ['Volume_Ratio', 'Price_Change']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算成交量确认信号"""
        volume_ratio = data.iloc[index]['Volume_Ratio']
        price_change = data.iloc[index]['Price_Change']
        
        if pd.isna(volume_ratio) or pd.isna(price_change):
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                reason="成交量数据缺失",
                metadata={}
            )
        
        # 放量上涨
        if volume_ratio > self.params['volume_threshold'] and price_change > self.params['price_change_threshold']:
            confidence = min(0.5, volume_ratio / 3 * abs(price_change) * 10)
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"放量上涨(成交量{volume_ratio:.2f}倍, 涨幅{price_change:.2%})",
                metadata={
                    'volume_ratio': volume_ratio,
                    'price_change': price_change,
                    'volume': data.iloc[index]['volume']
                }
            )
        
        # 放量下跌
        elif volume_ratio > self.params['volume_threshold'] and price_change < -self.params['price_change_threshold']:
            confidence = min(0.5, volume_ratio / 3 * abs(price_change) * 10)
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=data.iloc[index]['close'],
                reason=f"放量下跌(成交量{volume_ratio:.2f}倍, 跌幅{price_change:.2%})",
                metadata={
                    'volume_ratio': volume_ratio,
                    'price_change': price_change,
                    'volume': data.iloc[index]['volume']
                }
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=data.iloc[index]['close'],
            reason="成交量无明显异常",
            metadata={'volume_ratio': volume_ratio, 'price_change': price_change}
        )

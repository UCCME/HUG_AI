"""
板块轮动策略
用于捕捉板块趋势和轮动机会
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class SectorRotationStrategy(BaseStrategy):
    """
    板块轮动策略
    
    核心逻辑：
    1. 计算板块相对强度（相对大盘的超额收益）
    2. 识别强势板块（连续N天跑赢大盘）
    3. 确认趋势持续性（成交量放大、动量加速）
    4. 生成交易信号
    """
    
    def __init__(self, weight: float = 0.20, enabled: bool = True,
                 lookback_period: int = 20,  # 回溯周期
                 strength_threshold: float = 0.05,  # 强度阈值（5%超额收益）
                 volume_threshold: float = 1.5,  # 成交量放大阈值
                 momentum_period: int = 5,  # 动量周期
                 **kwargs):
        """
        初始化板块轮动策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            lookback_period: 计算相对强度的回溯周期
            strength_threshold: 判断强势的阈值
            volume_threshold: 成交量放大阈值
            momentum_period: 动量加速判断周期
        """
        super().__init__(
            name="SectorRotation_Strategy",
            weight=weight,
            enabled=enabled,
            lookback_period=lookback_period,
            strength_threshold=strength_threshold,
            volume_threshold=volume_threshold,
            momentum_period=momentum_period,
            **kwargs
        )
    
    def _validate_params(self):
        """验证参数"""
        if self.params['lookback_period'] < 5:
            raise ValueError("回溯周期必须至少为5天")
        if self.params['strength_threshold'] <= 0:
            raise ValueError("强度阈值必须大于0")
        if self.params['volume_threshold'] <= 1:
            raise ValueError("成交量阈值必须大于1")
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return [
            'close',
            'volume',
            'Volume_Ratio',
            'Price_Change',
            'RSI',
            'MACD'
        ]
    
    def calculate_relative_strength(self, data: pd.DataFrame, index: int, 
                                    benchmark_returns: pd.Series = None) -> float:
        """
        计算相对强度（相对于基准的超额收益）
        
        Args:
            data: 价格数据
            index: 当前索引
            benchmark_returns: 基准收益率序列（如沪深300）
            
        Returns:
            float: 相对强度值
        """
        lookback = self.params['lookback_period']
        
        if index < lookback:
            return 0.0
        
        # 计算标的收益率
        start_price = data.iloc[index - lookback]['close']
        current_price = data.iloc[index]['close']
        asset_return = (current_price - start_price) / start_price
        
        # 如果没有基准数据，使用绝对收益
        if benchmark_returns is None or len(benchmark_returns) < index:
            return asset_return
        
        # 计算基准收益率
        benchmark_return = benchmark_returns.iloc[index - lookback:index + 1].sum()
        
        # 相对强度 = 标的收益 - 基准收益
        relative_strength = asset_return - benchmark_return
        
        return relative_strength
    
    def check_momentum_acceleration(self, data: pd.DataFrame, index: int) -> bool:
        """
        检查动量是否加速
        
        通过比较近期和远期的涨幅来判断
        """
        momentum_period = self.params['momentum_period']
        
        if index < momentum_period * 2:
            return False
        
        # 近期涨幅
        recent_return = (data.iloc[index]['close'] - data.iloc[index - momentum_period]['close']) / \
                       data.iloc[index - momentum_period]['close']
        
        # 远期涨幅
        previous_return = (data.iloc[index - momentum_period]['close'] - 
                          data.iloc[index - momentum_period * 2]['close']) / \
                         data.iloc[index - momentum_period * 2]['close']
        
        # 动量加速：近期涨幅 > 远期涨幅
        return recent_return > previous_return and recent_return > 0
    
    def check_volume_confirmation(self, data: pd.DataFrame, index: int) -> bool:
        """
        检查成交量确认
        
        强势板块通常伴随成交量放大
        """
        if 'Volume_Ratio' not in data.columns:
            return False
        
        volume_ratio = data.iloc[index]['Volume_Ratio']
        
        if pd.isna(volume_ratio):
            return False
        
        return volume_ratio > self.params['volume_threshold']
    
    def check_trend_quality(self, data: pd.DataFrame, index: int) -> Dict[str, bool]:
        """
        检查趋势质量
        
        Returns:
            Dict: 包含各项趋势质量指标
        """
        quality = {
            'strong_momentum': False,
            'volume_confirmed': False,
            'rsi_healthy': False,
            'macd_positive': False
        }
        
        # 1. 动量加速
        quality['strong_momentum'] = self.check_momentum_acceleration(data, index)
        
        # 2. 成交量确认
        quality['volume_confirmed'] = self.check_volume_confirmation(data, index)
        
        # 3. RSI健康（不过热）
        if 'RSI' in data.columns and not pd.isna(data.iloc[index]['RSI']):
            rsi = data.iloc[index]['RSI']
            quality['rsi_healthy'] = 40 < rsi < 75  # 不超卖也不过度超买
        
        # 4. MACD正向
        if 'MACD' in data.columns and not pd.isna(data.iloc[index]['MACD']):
            macd = data.iloc[index]['MACD']
            quality['macd_positive'] = macd > 0
        
        return quality
    
    def calculate_signal(self, data: pd.DataFrame, index: int, 
                        benchmark_returns: pd.Series = None) -> StrategySignal:
        """
        计算板块轮动信号
        
        Args:
            data: 价格数据
            index: 当前索引
            benchmark_returns: 基准收益率（可选）
            
        Returns:
            StrategySignal: 交易信号
        """
        current_price = data.iloc[index]['close']
        
        # 计算相对强度
        relative_strength = self.calculate_relative_strength(data, index, benchmark_returns)
        
        # 检查趋势质量
        trend_quality = self.check_trend_quality(data, index)
        
        # 计算质量得分
        quality_score = sum(trend_quality.values()) / len(trend_quality)
        
        # 生成信号
        if relative_strength > self.params['strength_threshold']:
            # 强势板块
            if quality_score >= 0.75:  # 至少3/4的质量指标通过
                confidence = min(0.8, relative_strength * 10 * quality_score)
                
                reasons = []
                if trend_quality['strong_momentum']:
                    reasons.append("动量加速")
                if trend_quality['volume_confirmed']:
                    reasons.append("成交量放大")
                if trend_quality['rsi_healthy']:
                    reasons.append("RSI健康")
                if trend_quality['macd_positive']:
                    reasons.append("MACD正向")
                
                return StrategySignal(
                    timestamp=data.index[index],
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    price=current_price,
                    reason=f"强势板块(相对强度{relative_strength:.2%}, {', '.join(reasons)})",
                    metadata={
                        'relative_strength': relative_strength,
                        'quality_score': quality_score,
                        'trend_quality': trend_quality
                    }
                )
            elif quality_score >= 0.5:
                # 中等质量，持有观望
                return StrategySignal(
                    timestamp=data.index[index],
                    signal_type=SignalType.HOLD,
                    confidence=0.3,
                    price=current_price,
                    reason=f"板块强势但质量一般(相对强度{relative_strength:.2%})",
                    metadata={
                        'relative_strength': relative_strength,
                        'quality_score': quality_score
                    }
                )
        
        elif relative_strength < -self.params['strength_threshold']:
            # 弱势板块，考虑卖出
            if quality_score < 0.5:  # 质量恶化
                confidence = min(0.7, abs(relative_strength) * 10 * (1 - quality_score))
                
                return StrategySignal(
                    timestamp=data.index[index],
                    signal_type=SignalType.SELL,
                    confidence=confidence,
                    price=current_price,
                    reason=f"板块转弱(相对强度{relative_strength:.2%})",
                    metadata={
                        'relative_strength': relative_strength,
                        'quality_score': quality_score
                    }
                )
        
        # 默认持有
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=current_price,
            reason=f"板块中性(相对强度{relative_strength:.2%})",
            metadata={
                'relative_strength': relative_strength,
                'quality_score': quality_score
            }
        )


class SectorLeaderStrategy(BaseStrategy):
    """
    板块龙头策略
    
    在强势板块中选择龙头股
    """
    
    def __init__(self, weight: float = 0.15, enabled: bool = True,
                 volume_rank_threshold: int = 3,  # 成交量排名前N
                 price_strength_threshold: float = 0.03,  # 价格强度阈值
                 **kwargs):
        super().__init__(
            name="SectorLeader_Strategy",
            weight=weight,
            enabled=enabled,
            volume_rank_threshold=volume_rank_threshold,
            price_strength_threshold=price_strength_threshold,
            **kwargs
        )
    
    def get_required_indicators(self) -> List[str]:
        return ['close', 'volume', 'Volume_Ratio', 'Price_Change']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """
        计算龙头股信号
        
        龙头特征：
        1. 成交量大（板块内排名靠前）
        2. 涨幅领先
        3. 率先突破
        """
        current_price = data.iloc[index]['close']
        volume_ratio = data.iloc[index].get('Volume_Ratio', 1.0)
        price_change = data.iloc[index].get('Price_Change', 0.0)
        
        # 简化版：基于成交量和涨幅判断
        is_high_volume = volume_ratio > 2.0  # 成交量放大2倍以上
        is_strong_price = price_change > self.params['price_strength_threshold']
        
        if is_high_volume and is_strong_price:
            confidence = min(0.7, volume_ratio / 5 * abs(price_change) * 20)
            
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=current_price,
                reason=f"板块龙头(成交量{volume_ratio:.1f}倍, 涨幅{price_change:.2%})",
                metadata={
                    'volume_ratio': volume_ratio,
                    'price_change': price_change
                }
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=current_price,
            reason="非龙头特征",
            metadata={}
        )

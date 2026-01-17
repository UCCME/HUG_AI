"""
策略组合器
负责组合多个策略并生成综合信号
"""
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

from strategies.base_strategy import BaseStrategy, SignalType, StrategySignal


@dataclass
class CompositeSignal:
    """综合信号"""
    timestamp: datetime
    signal_type: SignalType
    confidence: float
    price: float
    buy_score: float
    sell_score: float
    buy_count: int
    sell_count: int
    contributing_strategies: List[str]
    all_signals: List[StrategySignal]
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class StrategyComposer:
    """
    策略组合器
    组合多个策略的信号，生成综合交易决策
    """
    
    def __init__(self, strategies: List[BaseStrategy], 
                 signal_threshold: float = 0.18,
                 min_signal_count: int = 2):
        """
        初始化策略组合器
        
        Args:
            strategies: 策略列表
            signal_threshold: 信号触发阈值
            min_signal_count: 最小信号数量
        """
        self.strategies = strategies
        self.signal_threshold = signal_threshold
        self.min_signal_count = min_signal_count
        
        # 验证策略
        self._validate_strategies()
    
    def _validate_strategies(self):
        """验证策略列表"""
        if not self.strategies:
            raise ValueError("策略列表不能为空")
        
        for strategy in self.strategies:
            if not isinstance(strategy, BaseStrategy):
                raise TypeError(f"{strategy} 必须是 BaseStrategy 的实例")
    
    def add_strategy(self, strategy: BaseStrategy):
        """添加策略"""
        if not isinstance(strategy, BaseStrategy):
            raise TypeError("策略必须是 BaseStrategy 的实例")
        self.strategies.append(strategy)
    
    def remove_strategy(self, strategy_name: str):
        """移除策略"""
        self.strategies = [s for s in self.strategies if s.name != strategy_name]
    
    def get_enabled_strategies(self) -> List[BaseStrategy]:
        """获取已启用的策略"""
        return [s for s in self.strategies if s.is_enabled()]
    
    def get_required_indicators(self) -> List[str]:
        """获取所有策略所需的指标"""
        indicators = set()
        for strategy in self.get_enabled_strategies():
            indicators.update(strategy.get_required_indicators())
        return list(indicators)
    
    def generate_composite_signal(self, data: pd.DataFrame, index: int) -> CompositeSignal:
        """
        生成综合信号
        
        Args:
            data: 包含所有指标的数据
            index: 当前索引
            
        Returns:
            CompositeSignal: 综合信号
        """
        enabled_strategies = self.get_enabled_strategies()
        
        if not enabled_strategies:
            return CompositeSignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=data.iloc[index]['close'],
                buy_score=0.0,
                sell_score=0.0,
                buy_count=0,
                sell_count=0,
                contributing_strategies=[],
                all_signals=[]
            )
        
        # 收集所有策略信号
        all_signals = []
        for strategy in enabled_strategies:
            try:
                signal = strategy.calculate_signal(data, index)
                all_signals.append(signal)
            except Exception as e:
                print(f"⚠️  策略 {strategy.name} 计算信号失败: {str(e)}")
                continue
        
        # 计算加权得分
        buy_score = 0.0
        sell_score = 0.0
        buy_count = 0
        sell_count = 0
        contributing_strategies = []
        
        for signal, strategy in zip(all_signals, enabled_strategies):
            weighted_confidence = signal.confidence * strategy.get_weight()
            
            if signal.signal_type == SignalType.BUY:
                buy_score += weighted_confidence
                buy_count += 1
                contributing_strategies.append(f"{strategy.name}(买入)")
            elif signal.signal_type == SignalType.SELL:
                sell_score += weighted_confidence
                sell_count += 1
                contributing_strategies.append(f"{strategy.name}(卖出)")
        
        # 决策逻辑
        final_signal = SignalType.HOLD
        final_confidence = 0.0
        
        if (buy_score > self.signal_threshold and 
            buy_score > sell_score and 
            buy_count >= self.min_signal_count):
            final_signal = SignalType.BUY
            final_confidence = buy_score
        elif (sell_score > self.signal_threshold and 
              sell_score > buy_score and 
              sell_count >= self.min_signal_count):
            final_signal = SignalType.SELL
            final_confidence = sell_score
        
        return CompositeSignal(
            timestamp=data.index[index],
            signal_type=final_signal,
            confidence=final_confidence,
            price=data.iloc[index]['close'],
            buy_score=buy_score,
            sell_score=sell_score,
            buy_count=buy_count,
            sell_count=sell_count,
            contributing_strategies=contributing_strategies,
            all_signals=all_signals
        )
    
    def get_strategy_weights(self) -> Dict[str, float]:
        """获取所有策略的权重"""
        return {s.name: s.get_weight() for s in self.strategies}
    
    def set_strategy_weight(self, strategy_name: str, weight: float):
        """设置策略权重"""
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                strategy.set_weight(weight)
                return
        raise ValueError(f"未找到策略: {strategy_name}")
    
    def enable_strategy(self, strategy_name: str):
        """启用策略"""
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                strategy.set_enabled(True)
                return
        raise ValueError(f"未找到策略: {strategy_name}")
    
    def disable_strategy(self, strategy_name: str):
        """禁用策略"""
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                strategy.set_enabled(False)
                return
        raise ValueError(f"未找到策略: {strategy_name}")
    
    def get_info(self) -> Dict:
        """获取组合器信息"""
        return {
            'total_strategies': len(self.strategies),
            'enabled_strategies': len(self.get_enabled_strategies()),
            'signal_threshold': self.signal_threshold,
            'min_signal_count': self.min_signal_count,
            'strategies': [s.get_info() for s in self.strategies],
            'required_indicators': self.get_required_indicators()
        }
    
    def print_info(self):
        """打印组合器信息"""
        print("\n" + "=" * 60)
        print("🎯 策略组合器信息")
        print("=" * 60)
        print(f"总策略数: {len(self.strategies)}")
        print(f"已启用策略数: {len(self.get_enabled_strategies())}")
        print(f"信号阈值: {self.signal_threshold}")
        print(f"最小信号数: {self.min_signal_count}")
        print(f"\n策略列表:")
        for i, strategy in enumerate(self.strategies, 1):
            status = "✅ 启用" if strategy.is_enabled() else "❌ 禁用"
            print(f"  {i}. {strategy.name} - 权重: {strategy.get_weight():.2f} - {status}")
        print(f"\n所需指标: {', '.join(self.get_required_indicators())}")
        print("=" * 60)

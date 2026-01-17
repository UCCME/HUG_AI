"""
策略基类
定义所有策略的统一接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategySignal:
    """策略信号数据类"""
    timestamp: datetime
    signal_type: SignalType
    confidence: float  # 信号置信度 0-1
    price: float
    reason: str  # 信号原因
    metadata: Dict[str, Any]  # 额外的元数据


class BaseStrategy(ABC):
    """
    策略基类
    所有具体策略都必须继承此类并实现抽象方法
    """
    
    def __init__(self, name: str, weight: float = 1.0, enabled: bool = True, **kwargs):
        """
        初始化策略
        
        Args:
            name: 策略名称
            weight: 策略权重（用于信号组合）
            enabled: 是否启用该策略
            **kwargs: 策略特定的参数
        """
        self.name = name
        self.weight = weight
        self.enabled = enabled
        self.params = kwargs
        self._validate_params()
    
    def _validate_params(self):
        """验证策略参数（子类可重写）"""
        pass
    
    @abstractmethod
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """
        计算交易信号
        
        Args:
            data: 包含所有技术指标的完整数据
            index: 当前数据索引
            
        Returns:
            StrategySignal: 策略信号
        """
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """
        获取策略所需的技术指标列表
        
        Returns:
            List[str]: 指标名称列表
        """
        pass
    
    def is_enabled(self) -> bool:
        """检查策略是否启用"""
        return self.enabled
    
    def set_enabled(self, enabled: bool):
        """设置策略启用状态"""
        self.enabled = enabled
    
    def get_weight(self) -> float:
        """获取策略权重"""
        return self.weight
    
    def set_weight(self, weight: float):
        """设置策略权重"""
        if not 0 <= weight <= 1:
            raise ValueError("权重必须在0-1之间")
        self.weight = weight
    
    def get_params(self) -> Dict[str, Any]:
        """获取策略参数"""
        return self.params.copy()
    
    def update_params(self, **kwargs):
        """更新策略参数"""
        self.params.update(kwargs)
        self._validate_params()
    
    def get_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'name': self.name,
            'weight': self.weight,
            'enabled': self.enabled,
            'params': self.params,
            'required_indicators': self.get_required_indicators()
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', weight={self.weight}, enabled={self.enabled})"

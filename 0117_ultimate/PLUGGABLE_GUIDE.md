# 可插拔式策略架构指南

## 📖 概述

可插拔式架构允许你灵活地组合、配置和扩展交易策略，无需修改核心代码即可实现策略的动态管理。

## 🏗️ 架构设计

### 核心组件

```
可插拔式架构
│
├── 策略基类 (BaseStrategy)
│   └── 定义统一接口
│
├── 具体策略 (Strategies)
│   ├── MAStrategy
│   ├── RSIStrategy
│   ├── MACDStrategy
│   ├── BollingerStrategy
│   ├── VolumeStrategy
│   ├── StochRSIStrategy
│   ├── UTBotStrategy
│   └── SMCStrategy
│
├── 策略工厂 (StrategyFactory)
│   ├── 策略注册
│   ├── 策略创建
│   └── 策略管理
│
├── 策略组合器 (StrategyComposer)
│   ├── 信号收集
│   ├── 信号加权
│   └── 综合决策
│
└── 配置管理 (PluggableConfig)
    ├── 策略配置
    ├── 预设方案
    └── 动态调整
```

## 🚀 快速开始

### 1. 使用预设配置

```bash
# 保守型配置
python pluggable_main.py --config conservative

# 平衡型配置（默认）
python pluggable_main.py --config balanced

# 激进型配置
python pluggable_main.py --config aggressive

# 趋势跟踪配置
python pluggable_main.py --config trend

# 均值回归配置
python pluggable_main.py --config mean_reversion
```

### 2. 列出所有可用策略

```bash
python pluggable_main.py --list-strategies
```

### 3. 运行示例

```bash
python pluggable_example.py
```

## 💡 使用示例

### 示例1：创建单个策略

```python
from strategy_factory import StrategyFactory

# 创建MA策略
ma_strategy = StrategyFactory.create(
    'ma',
    weight=0.5,
    enabled=True,
    fast_period=50,
    slow_period=200
)

print(f"策略信息: {ma_strategy}")
print(f"所需指标: {ma_strategy.get_required_indicators()}")
```

### 示例2：创建策略组合

```python
from strategy_factory import StrategyFactory
from strategy_composer import StrategyComposer

# 创建多个策略
strategies = [
    StrategyFactory.create('ma', weight=0.4),
    StrategyFactory.create('rsi', weight=0.3),
    StrategyFactory.create('macd', weight=0.3),
]

# 创建组合器
composer = StrategyComposer(
    strategies=strategies,
    signal_threshold=0.2,
    min_signal_count=2
)

composer.print_info()
```

### 示例3：使用配置文件

```python
from pluggable_config import PluggableConfig, StrategyConfig

# 创建配置
config = PluggableConfig()

# 禁用某个策略
config.disable_strategy('volume')

# 修改策略权重
config.set_strategy_weight('ma', 0.35)

# 添加新策略
config.add_strategy(StrategyConfig(
    name='rsi',
    weight=0.25,
    enabled=True,
    params={'period': 21, 'oversold': 25, 'overbought': 75}
))

config.print_config()
```

### 示例4：动态调整策略

```python
from strategy_composer import StrategyComposer

# 创建组合器
composer = StrategyComposer(strategies=strategies)

# 调整权重
composer.set_strategy_weight('MA_Strategy', 0.4)

# 禁用策略
composer.disable_strategy('Bollinger_Strategy')

# 启用策略
composer.enable_strategy('Bollinger_Strategy')

# 查看当前配置
composer.print_info()
```

## 🔧 自定义策略

### 创建新策略

1. **继承BaseStrategy类**

```python
from strategies.base_strategy import BaseStrategy, SignalType, StrategySignal
import pandas as pd
from typing import List

class MyCustomStrategy(BaseStrategy):
    """我的自定义策略"""
    
    def __init__(self, weight: float = 0.1, enabled: bool = True, 
                 my_param: int = 10, **kwargs):
        super().__init__(
            name="MyCustom_Strategy",
            weight=weight,
            enabled=enabled,
            my_param=my_param,
            **kwargs
        )
    
    def get_required_indicators(self) -> List[str]:
        """返回所需指标"""
        return ['close', 'volume']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """计算交易信号"""
        # 实现你的策略逻辑
        current_price = data.iloc[index]['close']
        
        # 示例：简单的价格突破策略
        if index < self.params['my_param']:
            signal_type = SignalType.HOLD
            confidence = 0.0
            reason = "数据不足"
        else:
            # 你的策略逻辑
            signal_type = SignalType.BUY  # 或 SELL 或 HOLD
            confidence = 0.5
            reason = "自定义信号"
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=signal_type,
            confidence=confidence,
            price=current_price,
            reason=reason,
            metadata={'my_data': 'value'}
        )
```

2. **注册策略**

```python
from strategy_factory import StrategyFactory

# 注册自定义策略
StrategyFactory.register('my_custom', MyCustomStrategy)

# 使用自定义策略
my_strategy = StrategyFactory.create('my_custom', weight=0.2, my_param=20)
```

## 📊 预设配置方案

### 1. 保守型配置
- **特点**：注重风险控制，信号要求严格
- **止损**：3%
- **止盈**：8%
- **仓位**：70%
- **策略**：仅使用MA、RSI、MACD基础策略
- **适用**：风险厌恶型投资者

### 2. 平衡型配置（默认）
- **特点**：风险收益平衡
- **止损**：5%
- **止盈**：10%
- **仓位**：95%
- **策略**：使用所有8个策略
- **适用**：大多数投资者

### 3. 激进型配置
- **特点**：追求高收益，容忍高风险
- **止损**：8%
- **止盈**：15%
- **仓位**：95%
- **策略**：使用所有策略，信号阈值较低
- **适用**：风险偏好型投资者

### 4. 趋势跟踪配置
- **特点**：专注趋势策略
- **策略**：MA、MACD、UT Bot、SMC
- **适用**：趋势明显的市场

### 5. 均值回归配置
- **特点**：专注超买超卖
- **策略**：RSI、Bollinger、StochRSI
- **适用**：震荡市场

## 🎯 策略参数说明

### MA策略
- `fast_period`: 快线周期（默认72）
- `slow_period`: 慢线周期（默认216）

### RSI策略
- `period`: RSI周期（默认14）
- `oversold`: 超卖阈值（默认30）
- `overbought`: 超买阈值（默认70）

### MACD策略
- `fast`: 快线周期（默认12）
- `slow`: 慢线周期（默认26）
- `signal`: 信号线周期（默认9）

### Bollinger策略
- `period`: 布林带周期（默认20）
- `std_dev`: 标准差倍数（默认2.0）

### Volume策略
- `volume_threshold`: 成交量放大阈值（默认1.5倍）
- `price_change_threshold`: 价格变化阈值（默认0.01）

### StochRSI策略
- `period`: RSI周期（默认14）
- `k_period`: K线平滑周期（默认3）
- `d_period`: D线平滑周期（默认3）
- `oversold`: 超卖阈值（默认20）
- `overbought`: 超买阈值（默认80）

### UT Bot策略
- `atr_period`: ATR周期（默认10）
- `key_value`: 关键值倍数（默认1.2）

### SMC策略
- `swing_window`: 摆动点检测窗口（默认3）
- `ob_lookback`: 订单块回溯周期（默认10）

## 🔍 高级用法

### 1. 参数优化

```python
from pluggable_config import PluggableConfig
from strategy_factory import StrategyFactory
from strategy_composer import StrategyComposer

# 测试不同参数组合
param_combinations = [
    {'fast_period': 50, 'slow_period': 200},
    {'fast_period': 72, 'slow_period': 216},
    {'fast_period': 100, 'slow_period': 300},
]

for params in param_combinations:
    ma_strategy = StrategyFactory.create('ma', **params)
    # 进行回测并比较结果
```

### 2. 策略权重优化

```python
# 使用网格搜索优化权重
weight_combinations = [
    {'ma': 0.3, 'rsi': 0.3, 'macd': 0.4},
    {'ma': 0.4, 'rsi': 0.2, 'macd': 0.4},
    {'ma': 0.5, 'rsi': 0.25, 'macd': 0.25},
]

for weights in weight_combinations:
    # 创建策略并测试
    pass
```

### 3. 动态策略切换

```python
# 根据市场状态切换策略
def select_strategies_by_market_condition(volatility):
    if volatility > 0.03:  # 高波动
        return get_mean_reversion_config()
    else:  # 低波动
        return get_trend_following_config()
```

## 📈 性能对比

使用可插拔架构，你可以轻松对比不同策略组合的表现：

```bash
# 对比不同配置
python pluggable_main.py --config conservative
python pluggable_main.py --config aggressive
python pluggable_main.py --config trend
```

## ⚠️ 注意事项

1. **策略数量**：不是策略越多越好，过多策略可能导致信号冲突
2. **权重分配**：确保所有启用策略的权重总和合理
3. **参数调优**：不同市场需要不同参数，避免过度拟合
4. **回测验证**：任何配置修改都应该先回测验证
5. **实盘谨慎**：回测表现不代表实盘结果

## 🎓 最佳实践

1. **从简单开始**：先使用3-5个基础策略
2. **逐步优化**：根据回测结果逐步调整
3. **分散风险**：使用不同类型的策略组合
4. **定期评估**：定期检查策略表现并调整
5. **记录变更**：记录每次配置变更和结果

## 📚 相关文档

- [README.md](README.md) - 项目总览
- [QUICKSTART.md](QUICKSTART.md) - 快速开始
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目总结

---

**版本**: v2.0.0 (可插拔式架构)  
**更新日期**: 2025-01-17

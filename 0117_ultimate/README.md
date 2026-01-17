# 究极策略 (Ultimate Strategy)

## 📖 项目简介

究极策略是一个整合了多个优秀量化交易策略的终极回测系统，融合了以下策略的核心优势：

- **黄金策略**：五大技术指标综合信号（MA、MACD、RSI、布林带、成交量）
- **加密货币策略**：情绪+技术共振、信号评分系统
- **期权策略**：30/70资金管理、时间止损、动态移仓
- **Lucy策略**：零延迟移动平均线(ZLSMA)、UT Bot自适应追踪止损
- **StochRSI策略**：超买超卖敏感信号、Fisher变换
- **SMC技术分析**：BOS/CH趋势识别、订单块和FVG关键区域

## ✨ 核心特性

### 1. 多维度信号生成
- **8大技术指标**：MA交叉、RSI、MACD、布林带、成交量、StochRSI、UT Bot、SMC结构
- **加权评分系统**：根据信号置信度和数量综合决策
- **多因子共振**：要求至少2个信号同时触发才开仓

### 2. 智能风险控制
- **多层止损机制**：
  - 固定止损：5%
  - ATR动态止损：2倍ATR
  - UT Bot追踪止损：自适应市场波动
  - 移动止损：盈利3%后启动
  - 时间止损：7天未盈利自动离场
  
- **动态仓位管理**：
  - 基于信号置信度调整仓位
  - ATR风险控制：单笔风险不超过1%
  - 30/70动态移仓：盈利8%时锁定70%利润

### 3. 完善的回测系统
- **多数据源支持**：本地CSV、yfinance、AkShare
- **精确成本模拟**：手续费0.2%、滑点0.1%
- **详细交易日志**：记录每笔交易的完整信息
- **丰富的性能指标**：夏普比率、最大回撤、胜率、盈利因子等

### 4. 专业的可视化分析
- 权益曲线和回撤图
- 收益分布和累计收益
- 月度收益热力图
- 交易盈亏分布
- 持仓时间分析

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

**注意**：TA-Lib 需要单独安装：
- macOS: `brew install ta-lib`
- Ubuntu: `sudo apt-get install ta-lib`
- Windows: 下载预编译包 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib

### 基础使用

```bash
# 使用默认配置运行（最近1年数据）
python main.py

# 指定回测日期范围
python main.py --start-date 2023-01-01 --end-date 2024-01-01

# 使用本地数据
python main.py --data-provider local

# 指定初始资金
python main.py --initial-capital 50000

# 不显示图表（仅生成报告）
python main.py --no-plot
```

### 配置文件

编辑 `config.py` 可以调整策略参数：

```python
# 技术指标参数
FAST_MA_PERIOD = 72      # 快线周期
SLOW_MA_PERIOD = 216     # 慢线周期
RSI_OVERSOLD = 30        # RSI超卖阈值
RSI_OVERBOUGHT = 70      # RSI超买阈值

# 信号权重
WEIGHT_MA = 0.25         # 移动平均线权重
WEIGHT_MACD = 0.20       # MACD权重
WEIGHT_RSI = 0.15        # RSI权重
WEIGHT_STOCH_RSI = 0.10  # StochRSI权重
WEIGHT_UT_BOT = 0.10     # UT Bot权重

# 风险控制
STOP_LOSS_PCT = 0.05     # 固定止损5%
TAKE_PROFIT_PCT = 0.10   # 固定止盈10%
TIME_STOP_DAYS = 7       # 时间止损7天
```

## 📊 策略逻辑

### 信号生成流程

1. **计算技术指标**
   - 移动平均线（MA）
   - 相对强弱指标（RSI）
   - MACD指标
   - 布林带（BB）
   - 成交量比率
   - Stochastic RSI
   - UT Bot追踪止损线
   - SMC市场结构（BOS/CH/订单块/FVG）

2. **生成子信号**
   - 每个指标独立生成买入/卖出/持有信号
   - 计算信号置信度（0-1）
   - 记录信号原因

3. **综合决策**
   - 计算加权买入得分和卖出得分
   - 统计买入/卖出信号数量
   - 要求：得分>0.18 且 信号数量>=2

4. **执行交易**
   - 根据信号置信度和ATR计算仓位
   - 设置动态止损止盈价格
   - 记录交易详情

### 风险控制机制

```
入场 → 固定止损/止盈
    ↓
    ATR动态止损/止盈
    ↓
    UT Bot追踪止损
    ↓
    移动止损（盈利3%后启动）
    ↓
    时间止损（7天未盈利）
    ↓
    动态移仓（盈利8%时锁定70%）
```

## 📈 性能指标说明

- **总收益率**：(最终资金 - 初始资金) / 初始资金
- **年化收益率**：按年化计算的收益率
- **夏普比率**：(平均收益 - 无风险利率) / 收益标准差，衡量风险调整后收益
- **最大回撤**：从峰值到谷底的最大跌幅
- **胜率**：盈利交易次数 / 总交易次数
- **盈利因子**：总盈利 / 总亏损
- **卡尔玛比率**：年化收益率 / 最大回撤，衡量收益回撤比

## 📁 项目结构

```
0117_ultimate/
├── config.py                 # 配置文件
├── indicators.py             # 技术指标计算模块
├── ultimate_strategy.py      # 核心策略类
├── data_handler.py           # 数据处理模块
├── backtest_engine.py        # 回测引擎
├── performance_analyzer.py   # 性能分析模块
├── main.py                   # 主程序入口
├── requirements.txt          # 依赖包列表
├── README.md                 # 项目文档
├── trades_log.txt           # 交易日志（运行后生成）
├── equity_curve.png         # 权益曲线图（运行后生成）
├── return_distribution.png  # 收益分布图（运行后生成）
└── trade_analysis.png       # 交易分析图（运行后生成）
```

## 🔧 高级用法

### 自定义策略参数

```python
from config import UltimateConfig

# 创建自定义配置
config = UltimateConfig()
config.INITIAL_CAPITAL = 50000
config.STOP_LOSS_PCT = 0.03  # 修改止损为3%
config.WEIGHT_MA = 0.30      # 增加MA权重

# 使用自定义配置运行回测
from data_handler import DataHandler
from backtest_engine import BacktestEngine

data_handler = DataHandler(config)
data = data_handler.prepare_data('2023-01-01', '2024-01-01')

engine = BacktestEngine(config)
result = engine.run(data)
```

### 添加新的技术指标

在 `indicators.py` 中添加新指标：

```python
@staticmethod
def calculate_your_indicator(data: pd.Series, period: int) -> pd.Series:
    """计算你的自定义指标"""
    # 实现指标计算逻辑
    return indicator_values
```

在 `ultimate_strategy.py` 中添加信号生成逻辑：

```python
def calculate_your_signal(self, data: pd.DataFrame, index: int):
    """生成你的自定义信号"""
    # 实现信号生成逻辑
    return signal_type, confidence, reason
```

## ⚠️ 注意事项

1. **数据质量**：确保数据完整无缺失，建议使用高质量的数据源
2. **参数优化**：默认参数可能不适合所有市场，建议根据具体品种调整
3. **过拟合风险**：避免过度优化参数以适应历史数据
4. **实盘差异**：回测结果不代表实盘表现，需考虑滑点、流动性等因素
5. **风险管理**：实盘交易时务必严格执行止损，控制仓位

## 📝 更新日志

### v1.0.0 (2025-01-17)
- ✅ 整合8大策略模块
- ✅ 实现多维度信号生成系统
- ✅ 完善风险控制机制
- ✅ 添加动态仓位管理
- ✅ 支持多数据源
- ✅ 完整的回测和分析系统

## 📧 联系方式

如有问题或建议，欢迎提Issue或PR。

## 📄 许可证

MIT License

---

**免责声明**：本策略仅供学习研究使用，不构成任何投资建议。量化交易存在风险，请谨慎决策。

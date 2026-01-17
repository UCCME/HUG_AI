# 顽主杯松松策略量化系统

> 基于顽主杯实盘大赛冠军选手"松松"的短线交易策略，实现的A股量化交易系统

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg)

## 📖 目录

- [项目简介](#项目简介)
- [策略背景](#策略背景)
- [核心特性](#核心特性)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [策略详解](#策略详解)
- [配置说明](#配置说明)
- [使用示例](#使用示例)
- [模块文档](#模块文档)
- [常见问题](#常见问题)
- [免责声明](#免责声明)

---

## 项目简介

本项目是基于顽主杯实盘大赛知名选手"松松"（松雅湖的松松）的交易策略，实现的一套完整的A股短线量化交易系统。松松以其从"债神"到"正股选手"的成功转型和独特的交易思想，成为业界关注的焦点。

**核心理念：**
- **敬畏市场**：承认量化资金主导地位，不与趋势对抗
- **严格风控**：单笔亏损<1%，半仓滚动，动态仓位管理
- **精选龙头**：题材热点板块的龙头股，资金流入前10
- **纪律执行**：竞价弱转强买入，炸板次日止损

---

## 策略背景

### 松松的交易历程

松松的交易策略经历了三个重要阶段的演变：

#### 1. 可转债阶段（债神时代）
- **特点**：高频交易，T+0套利
- **业绩**：45个交易日收益100%+
- **纪律**：单笔亏损<1%，亏损持债不超30秒

#### 2. 正股转型阶段
- **背景**：2022年可转债新规实施，套利空间压缩
- **策略**：转向正股打板，核心票集中
- **特点**：早盘快速板、龙头回封板

#### 3. 量化时代（当前）
- **背景**：量化资金占比25%-30%，高频交易占比21%
- **策略**：半仓滚动，每天只买一只股票
- **理念**：与量化资金协同，而非对抗

### 市场环境

- A股量化资金规模：1.8万亿+
- 顽主杯胜率：仅16%选手能战胜指数
- 生存法则：**生存先于盈利**

---

## 核心特性

### ✅ 选股系统

- **题材导向**：识别热点板块（AI应用、新能源、芯片等）
- **龙头筛选**：板块内资金流入最大的龙头股
- **市值过滤**：中小市值（20亿-500亿）
- **板块效应**：板块内>=2只涨停股
- **资金追踪**：主力资金流入前10名

### ✅ 交易信号

**买入信号：**
1. **竞价弱转强**：集合竞价从负转正
2. **早盘快速板**：9:30-10:00封死涨停
3. **龙头回封板**：炸板后强势回封
4. **半路追涨**：5%-9%涨幅 + 量能配合 + 板块效应

**卖出信号：**
1. **次日竞价不及预期**：低开超过2%
2. **炸板次日止损**：昨日涨停今日炸板
3. **技术背离**：MACD顶背离
4. **获利目标**：根据配置的获利目标

### ✅ 风控体系

- **止损铁律**：单笔亏损严格控制在1%以内
- **仓位管理**：半仓滚动（50%最大仓位）
- **频率控制**：每天最多交易1只股票
- **空仓策略**：市场情绪<40时空仓等待
- **动态调整**：根据持仓评分动态调整仓位

### ✅ 技术指标

- **OBV（能量潮）**：判断主力资金动向
- **MACD**：趋势跟踪和背离检测
- **均线系统**：5/10/20/60日均线
- **资金流向**：MFI指标
- **量比分析**：相对历史量能

---

## 安装指南

### 环境要求

- Python 3.7+
- 操作系统：Windows / macOS / Linux

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository_url>
cd ai_trapper/wanzhu
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**核心依赖：**
```
pandas>=1.3.0
numpy>=1.20.0
```

**可选依赖：**
```bash
# Tushare数据源（需要token）
pip install tushare

# AKShare数据源（免费）
pip install akshare

# YAML配置文件支持
pip install pyyaml

# 可视化工具
pip install matplotlib mplfinance
```

#### 3. 验证安装

```bash
python examples/quick_start.py
```

---

## 快速开始

### 最简单的使用方式

```python
from wanzhu.strategy.songsong_strategy import SongSongStrategy
from wanzhu.config.strategy_config import StrategyConfig

# 1. 获取配置
config = StrategyConfig.get_config(mode='backtest')

# 2. 初始化策略
strategy = SongSongStrategy(config)

# 3. 运行回测
results = strategy.run(
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 4. 查看结果
print(strategy.get_performance_report())
```

### 运行示例脚本

```bash
# 快速开始
python examples/quick_start.py

# 多配置模式对比
python examples/custom_config_example.py

# 技术指标演示
python examples/indicators_demo.py
```

---

## 策略详解

### 完整交易流程

```
开盘前
│
├─ 1. 计算市场情绪（涨跌家数、涨停数量）
│
├─ 2. 判断是否交易
│   ├─ 市场情绪 < 40 → 空仓等待
│   ├─ 已达最大持仓 → 不开新仓
│   └─ 可以交易 → 继续
│
├─ 3. 选股流程
│   ├─ 基础筛选：市值、换手率、连板数
│   ├─ 板块筛选：识别强势板块
│   ├─ 资金筛选：主力流入前10
│   └─ 题材筛选：涨停股优先
│
├─ 4. 生成买入信号
│   ├─ 竞价弱转强
│   ├─ 早盘快速板
│   ├─ 龙头回封板
│   └─ 半路追涨
│
├─ 5. 风控检查
│   ├─ 计算仓位大小（基于评分）
│   ├─ 检查止损条件
│   └─ 确认可以开仓
│
└─ 6. 执行交易
    └─ 记录交易日志
```

### 选股逻辑详解

#### 第一步：基础筛选
```python
条件1: 20亿 <= 市值 <= 500亿  # 中小市值
条件2: 非ST股票
条件3: 换手率 >= 5%
条件4: 连板数 <= 3板
```

#### 第二步：板块效应
```python
识别强势板块：
- 板块内股票数 >= 3只
- 板块内涨停数 >= 2只
- 选择板块内资金流入最大的2只龙头
```

#### 第三步：资金流向
```python
按主力资金净流入排序
选择前10名纳入观察池
```

#### 第四步：涨停优先
```python
优先级1: 早盘快速板（9:30-10:00封死）
优先级2: 封死涨停（sealed=True）
优先级3: 炸板次数少（open_count<3）
```

### 买入时机

#### 1. 竞价弱转强
```python
条件：
- 集合竞价阶段涨幅从负转正
- 竞价量能充足
- 属于强势板块

原理：
主力试探性买入，快速拉升
体现做多决心
```

#### 2. 早盘快速板
```python
条件：
- 9:30-10:00封死涨停
- 封板时间越早越好
- 炸板次数<=1次

原理：
主力全力做多，资金强势
次日高开概率大
```

#### 3. 龙头回封板
```python
条件：
- 有过炸板但最终封住
- 回封时量比 >= 1.5
- 板块龙头地位明确

原理：
主力洗盘后重新封板
更加安全和确定
```

### 卖出时机

#### 1. 止损条件（最高优先级）
```python
触发条件：
- 单笔亏损 >= 1%  → 立即止损
- 昨日涨停今日炸板 → 次日开盘止损

执行：
无条件执行，不得有侥幸心理
```

#### 2. 竞价不及预期
```python
判断标准：
- 次日集合竞价低开 > 2%
- 竞价量能萎缩
- 卖单压力大

操作：
开盘即卖出，不等待反弹
```

#### 3. 技术信号
```python
MACD顶背离：
- 价格创新高，MACD未创新高
- 5日窗口检测

均线死叉：
- 短期均线下穿长期均线
```

### 仓位管理

#### 半仓滚动策略
```python
基础仓位：50%
├─ 市场情绪 >= 60 → 可用仓位50%
├─ 市场情绪 40-60 → 可用仓位30-50%
└─ 市场情绪 < 40 → 空仓等待

单票仓位：
- 持仓评分 >= 80 → 满仓（50%）
- 持仓评分 60-80 → 半仓（25-50%）
- 持仓评分 < 60 → 清仓
```

#### 动态调整
```python
加仓条件：
- 持仓评分 >= 80
- 市场情绪 > 60
- 当前仓位 < 最大仓位

减仓条件：
- 持仓评分 < 70
- 市场情绪下降
- 出现卖出信号
```

---

## 配置说明

### 配置文件结构

```python
# config/strategy_config.py

StrategyConfig
├── INITIAL_CAPITAL        # 初始资金
├── DATA_SOURCE           # 数据源
├── STRATEGY_MODE         # 策略模式
├── SELECTOR_CONFIG       # 选股配置
├── SIGNAL_CONFIG         # 信号配置
├── RISK_CONFIG          # 风控配置
├── BACKTEST_CONFIG      # 回测配置
└── DATA_CONFIG          # 数据源配置
```

### 关键参数

#### 选股参数
```python
SELECTOR_CONFIG = {
    'min_market_cap': 20e8,          # 最小市值20亿
    'max_market_cap': 500e8,         # 最大市值500亿
    'min_turnover': 5.0,             # 最小换手率5%
    'max_continuous_limit': 3,        # 最大连板3板
    'money_flow_top_n': 10,          # 资金流入前10
    'sector_min_stocks': 3,           # 板块最少3只股票
    'sector_min_limit_up': 2,         # 板块最少2只涨停
}
```

#### 风控参数
```python
RISK_CONFIG = {
    'max_single_loss_pct': 0.01,     # 单笔最大亏损1%
    'max_position_ratio': 0.5,       # 最大仓位50%
    'max_single_position': 0.5,      # 单票最大仓位50%
    'min_position_score': 60,        # 最低持仓评分
    'max_daily_trades': 1,           # 每天最多1笔交易
    'market_sentiment_threshold': 40, # 市场情绪阈值
}
```

### 预设配置模式

#### 1. 标准模式（默认）
松松在2025年使用的核心策略
```python
config = StrategyConfig.get_config(mode='production')
```

#### 2. 激进模式
```python
from wanzhu.config.strategy_config import AGGRESSIVE_CONFIG

特点：
- 最大仓位 80%
- 止损 1.5%
- 获利目标 15%

适用场景：
- 牛市行情
- 市场情绪高涨
- 风险偏好高
```

#### 3. 保守模式
```python
from wanzhu.config.strategy_config import CONSERVATIVE_CONFIG

特点：
- 最大仓位 30%
- 止损 0.8%
- 获利目标 8%

适用场景：
- 熊市或震荡市
- 市场情绪低迷
- 风险偏好低
```

#### 4. 可转债模式
```python
from wanzhu.config.strategy_config import CONVERTIBLE_BOND_CONFIG

特点：
- 高频交易（每天最多10笔）
- 30秒止损
- 适用T+0品种

适用场景：
- 纪念债神时代
- 可转债交易
```

### 自定义配置

#### 方法1：代码配置
```python
config = StrategyConfig.get_config()

# 修改风控参数
config['risk']['max_position_ratio'] = 0.3
config['risk']['max_single_loss_pct'] = 0.008

# 修改选股参数
config['selector']['money_flow_top_n'] = 5
```

#### 方法2：配置文件（JSON）
```json
{
  "risk": {
    "max_position_ratio": 0.3,
    "max_single_loss_pct": 0.008
  },
  "selector": {
    "money_flow_top_n": 5
  }
}
```

```python
config = StrategyConfig.load_from_file('my_config.json')
```

#### 方法3：配置文件（YAML）
```yaml
risk:
  max_position_ratio: 0.3
  max_single_loss_pct: 0.008

selector:
  money_flow_top_n: 5
```

```python
config = StrategyConfig.load_from_file('my_config.yaml')
```

---

## 使用示例

### 示例1：基础回测

```python
from wanzhu import SongSongStrategy
from wanzhu.config import StrategyConfig

# 初始化
config = StrategyConfig.get_config(mode='backtest')
strategy = SongSongStrategy(config)

# 运行回测
results = strategy.run(
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 查看结果
print(f"总收益率: {results.iloc[-1]['return']*100:.2f}%")
print(strategy.get_performance_report())
```

### 示例2：实时监控

```python
from wanzhu.strategy.stock_selector import StockSelector
from wanzhu.strategy.signal_generator import SignalGenerator

# 初始化选股器
selector = StockSelector()
signal_gen = SignalGenerator()

# 获取今日市场数据
market_data = loader.load_market_data(date='2024-12-23')

# 选股
candidates = selector.select_stocks('2024-12-23', market_data)

# 生成信号
for symbol in candidates:
    stock_data = market_data[market_data['symbol'] == symbol].iloc[0]
    should_buy, reason, price = signal_gen.generate_buy_signal(
        symbol, stock_data, hist_data, market_status
    )
    
    if should_buy:
        print(f"买入信号: {symbol} @ {price:.2f}, 原因: {reason}")
```

### 示例3：技术指标分析

```python
from wanzhu.utils.indicators import TechnicalIndicators

indicators = TechnicalIndicators()

# 计算指标
obv = indicators.calculate_obv(df)
dif, dea, macd = indicators.calculate_macd(df)
divergence = indicators.detect_divergence(df['close'], dif)

# 判断信号
if obv.iloc[-1] > obv.iloc[-5] and dif.iloc[-1] > dea.iloc[-1]:
    print("买入信号: OBV上升 + MACD金叉")
```

### 示例4：风险管理

```python
from wanzhu.strategy.risk_manager import RiskManager

risk_mgr = RiskManager()

# 检查止损
should_stop, reason = risk_mgr.check_stop_loss(
    symbol='600000',
    entry_price=10.0,
    current_price=9.90
)

if should_stop:
    print(f"止损信号: {reason}")

# 计算仓位
position_size = risk_mgr.calculate_position_size(
    symbol='600000',
    current_price=10.0,
    total_capital=1000000,
    position_score=75,
    market_sentiment=60
)

print(f"建议仓位: {position_size:,.0f}元")
```

---

## 模块文档

### 核心模块

#### 1. SongSongStrategy
主策略类，整合所有模块

**主要方法：**
```python
run(start_date, end_date, symbols=None)
# 运行策略回测

get_performance_report()
# 获取策略表现报告
```

#### 2. StockSelector
选股模块

**主要方法：**
```python
select_stocks(date, market_data)
# 选择符合条件的股票

evaluate_sector_strength(sector, date)
# 评估板块强度
```

#### 3. SignalGenerator
交易信号生成器

**主要方法：**
```python
generate_buy_signal(symbol, current_data, hist_data, market_status)
# 生成买入信号

generate_sell_signal(symbol, entry_price, current_data, hist_data, market_status)
# 生成卖出信号

calculate_position_score(symbol, current_data, hist_data, market_status)
# 计算持仓评分
```

#### 4. RiskManager
风险控制模块

**主要方法：**
```python
calculate_position_size(symbol, current_price, total_capital, position_score, market_sentiment)
# 计算仓位大小

check_stop_loss(symbol, entry_price, current_price, hold_seconds=0)
# 检查止损

should_take_position(symbol, date, market_sentiment)
# 判断是否开仓

should_close_position(symbol, position_score, hold_days)
# 判断是否平仓
```

### 工具模块

#### TechnicalIndicators
技术指标计算

**支持的指标：**
- OBV（能量潮）
- MA（移动平均线）
- EMA（指数移动平均线）
- MACD
- 资金流向（MFI）
- 背离检测

#### DataLoader
数据加载器

**支持的数据源：**
- Local（本地文件）
- Tushare（需要token）
- AKShare（免费）

---

## 常见问题

### Q1：如何接入真实数据？

**A：** 本系统支持多种数据源：

**方法1：使用 Tushare**
```python
# 1. 注册获取token: https://tushare.pro/
# 2. 修改配置
config['data_source'] = 'tushare'
config['data']['tushare']['token'] = 'your_token_here'
```

**方法2：使用 AKShare（免费）**
```python
# 1. 安装: pip install akshare
# 2. 修改配置
config['data_source'] = 'akshare'
```

**方法3：自定义数据源**
```python
# 继承 DataLoader 类，实现自己的数据接口
from wanzhu.utils.data_loader import DataLoader

class MyDataLoader(DataLoader):
    def load_stock_data(self, symbol, start_date, end_date):
        # 实现你的数据加载逻辑
        pass
```

### Q2：回测结果为什么与实盘不一致？

**A：** 可能的原因：

1. **滑点和手续费**：回测默认包含0.03%手续费和0.1%滑点
2. **涨停买不到**：实盘中涨停股可能无法买入
3. **数据质量**：确保使用前复权数据
4. **信号延迟**：实盘存在网络延迟和执行延迟

**建议**：
```python
# 调整滑点率以模拟实盘
config['backtest']['slippage_rate'] = 0.002  # 0.2%
```

### Q3：如何优化策略参数？

**A：** 参数优化建议：

1. **不要过度优化**：避免过拟合历史数据
2. **关键参数**：
   - 止损比例（建议0.8%-1.5%）
   - 最大仓位（建议30%-50%）
   - 市场情绪阈值（建议35-45）

3. **样本外测试**：
```python
# 分段测试
train_results = strategy.run('2023-01-01', '2023-12-31')
test_results = strategy.run('2024-01-01', '2024-12-31')
```

### Q4：策略在什么市场环境下效果最好？

**A：** 根据松松的实战经验：

**最佳市场环境：**
- 牛市中段（市场情绪60-80）
- 题材轮动活跃
- 涨停板数量>=30只/天
- 量化资金活跃

**不利市场环境：**
- 极端行情（暴涨暴跌）
- 题材冷清，无热点
- 市场情绪<30
- 建议：空仓等待

### Q5：单笔1%止损是否太严格？

**A：** 这是松松策略的核心纪律：

**严格止损的理由：**
1. 短线交易，不能被套
2. 保护本金，落袋为安
3. 快速试错，及时纠正
4. 10次止损也只亏10%，但1次成功可赚10%+

**执行建议：**
- 绝对不能放宽到2%
- 可以考虑0.8%（保守模式）
- 止损后反思，不要连续止损

### Q6：如何处理量化资金的竞争？

**A：** 松松的策略就是与量化协同：

**核心思路：**
1. **不对抗量化**：顺势而为
2. **利用龙头溢价**：量化推高龙头
3. **空仓等待**：情绪差时不硬做
4. **半仓滚动**：控制频率和仓位

**具体做法：**
- 只做板块内最强龙头
- 早盘快速板优于尾盘板
- 次日高开卖出，不贪

### Q7：策略能否用于可转债？

**A：** 可以，本系统包含可转债配置：

```python
from wanzhu.config.strategy_config import CONVERTIBLE_BOND_CONFIG

config = StrategyConfig.get_config()
config.update({'risk': CONVERTIBLE_BOND_CONFIG['risk']})

# 可转债特点：
# - T+0交易，可高频
# - 30秒止损
# - 每天可交易多次
```

**注意**：2022年8月后可转债已有20%涨跌幅限制

---

## 性能指标

### 回测数据（基于模拟数据）

| 指标 | 标准模式 | 激进模式 | 保守模式 |
|------|---------|---------|---------|
| 年化收益率 | 45% | 65% | 25% |
| 最大回撤 | -15% | -25% | -8% |
| 夏普比率 | 1.8 | 1.5 | 2.2 |
| 胜率 | 52% | 48% | 58% |
| 日均交易 | 0.8笔 | 1.2笔 | 0.5笔 |

*注：以上数据仅供参考，实盘结果取决于市场环境和执行质量*

---

## 项目结构

```
wanzhu/
├── __init__.py                 # 包初始化
├── README.md                   # 项目文档（本文件）
├── requirements.txt            # 依赖列表
│
├── config/                     # 配置模块
│   ├── __init__.py
│   └── strategy_config.py      # 策略配置
│
├── strategy/                   # 策略模块
│   ├── __init__.py
│   ├── songsong_strategy.py    # 主策略
│   ├── stock_selector.py       # 选股器
│   ├── signal_generator.py     # 信号生成器
│   └── risk_manager.py         # 风险管理器
│
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── indicators.py           # 技术指标
│   └── data_loader.py          # 数据加载器
│
├── examples/                   # 示例脚本
│   ├── __init__.py
│   ├── quick_start.py          # 快速开始
│   ├── custom_config_example.py # 自定义配置
│   └── indicators_demo.py      # 指标演示
│
├── data/                       # 数据目录
│   └── backtest_results.csv    # 回测结果
│
├── docs/                       # 文档目录
│   └── strategy_theory.md      # 策略理论
│
└── logs/                       # 日志目录
    └── strategy.log            # 运行日志
```

---

## 技术栈

- **语言**：Python 3.7+
- **数据处理**：pandas, numpy
- **数据源**：Tushare / AKShare
- **配置**：JSON / YAML
- **可视化**：matplotlib（可选）

---

## 开发路线图

### v1.0（当前版本）
- [x] 核心策略实现
- [x] 选股系统
- [x] 信号生成
- [x] 风险管理
- [x] 配置系统
- [x] 示例脚本

### v1.1（计划中）
- [ ] 实时监控面板
- [ ] 回测可视化
- [ ] 策略参数优化工具
- [ ] 更多数据源支持

### v2.0（未来）
- [ ] 多策略组合
- [ ] 机器学习优化
- [ ] 实盘交易接口
- [ ] Web管理界面

---

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 如何贡献

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

---

## 致谢

本项目的策略思想来源于顽主杯实盘大赛选手"松松"（松雅湖的松松）的公开分享。特此感谢松松为A股短线交易者提供的宝贵经验和深刻见解。

**松松语录：**
> "这个市场没有神，只有在不确定性中保持敬畏之心的交易者。"
> 
> "打板其实是为了追求确定性，为了明天的溢价。"
> 
> "善猎者必善等待。"

---

## 免责声明

**重要提示**：

1. **本项目仅供学习研究使用**，不构成任何投资建议
2. **量化交易存在风险**，历史业绩不代表未来表现
3. **实盘交易需谨慎**，请根据自身风险承受能力决策
4. **策略可能失效**，市场环境变化可能导致策略不适用
5. **严格风控第一**，请务必执行止损纪律

**投资有风险，入市需谨慎。生存先于盈利。**

---

## 许可证

MIT License

Copyright (c) 2024 AI Trapper

---

## 联系方式

- **项目主页**：[GitHub Repository]
- **问题反馈**：[Issues]
- **讨论交流**：[Discussions]

---

**最后更新**：2024-12-23

**版本**：v1.0.0

**作者**：AI Trapper Team

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！⭐**

Made with ❤️ by AI Trapper Team

</div>

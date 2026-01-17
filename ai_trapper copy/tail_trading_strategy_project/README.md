# 尾盘选股交易策略 / Tail Trading Strategy

[中文](#中文说明) | [English](#english-version)

---

## 中文说明

### 📖 项目简介

这是一个基于Python实现的"尾盘选股法"量化交易策略。该策略通过在每个交易日的尾盘时段（14:30-15:00）筛选符合特定技术指标的股票，并在次日开盘时卖出，实现短线快进快出的交易模式。

### 🎯 策略核心

**交易逻辑**：尾盘买入 → 次日开盘卖出（T+1交易）

**8大筛选条件**：

1. **涨幅控制**：当日涨幅在 2%~5% 之间
2. **流通市值**：50亿~200亿元（聚焦中小盘股）
3. **换手率**：4%~10%（确保交易活跃度）
4. **量比**：大于1（资金介入信号）
5. **量价关系**：成交量与价格同步上升
6. **均线排列**：MA5 > MA10 > MA20（多头排列）
7. **强于大盘**：个股涨幅超过大盘指数
8. **分时均价线**：股价全天在均价线上方（数据限制未实现）

### 📊 技术指标说明

- **换手率** = 当日成交量 / 流通股本 × 100%
- **量比** = 当日成交量 / 前5日平均成交量
- **均线多头排列** = 短期均线 > 长期均线（趋势看涨）

### 🚀 快速开始

#### 1. 环境要求

- Python 3.7+
- pip

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 运行策略

```bash
python tail_trading_strategy.py
```

### 💻 使用方法

#### 基础用法

```python
from tail_trading_strategy import TailTradingStrategy

# 创建策略实例
strategy = TailTradingStrategy()

# 运行单日选股
trade_date = '20231215'  # 指定交易日期
selected_stocks = strategy.run_strategy(trade_date)

# 查看选股结果
for stock in selected_stocks:
    print(f"{stock['code']} {stock['name']}: "
          f"涨幅{stock['change_pct']:.2f}%, "
          f"换手率{stock['turnover_rate']:.2f}%")
```

#### 高级用法 - 回测

```python
# 策略回测
start_date = '20230101'
end_date = '20231231'
backtest_results = strategy.backtest(start_date, end_date)

# 回测结果会自动输出：
# - 总交易次数
# - 平均收益率
# - 胜率
# - 最大收益/亏损
# - 累计收益
```

#### 自定义股票池

```python
# 指定股票列表进行筛选
test_stocks = ['000001', '600000', '000002', '600036']
selected = strategy.screen_stocks(
    stock_list=test_stocks,
    trade_date='20231215',
    index_change_pct=1.0  # 大盘涨跌幅
)
```

### 📁 项目结构

```
tail_trading_strategy_project/
├── tail_trading_strategy.py  # 策略主文件
├── requirements.txt           # 依赖配置
└── README.md                  # 项目说明（本文件）
```

### 📦 依赖说明

- **akshare**：免费的中国股市数据接口库
- **pandas**：数据分析和处理
- **numpy**：数值计算

### ⚠️ 风险提示

1. **仅供学习研究**：本策略代码仅用于教学和研究目的
2. **历史数据回测**：过往表现不代表未来收益
3. **市场风险**：短线策略对市场情绪敏感，需警惕：
   - 流动性风险
   - 政策变化（T+1交易限制）
   - 滑点风险
4. **实盘挑战**：尾盘瞬时下单需要高速交易接口
5. **参数调整**：实际应用需根据市场环境调整参数

### 🔧 优化方向

- 加入北向资金流向数据
- 整合龙虎榜信息
- 实现分时均价线筛选
- 增加止损机制
- 优化并行处理效率

### 📝 局限性

1. **分时均价线**：因数据接口限制未实现
2. **效率优化**：全量遍历A股效率较低
3. **数据延迟**：免费数据源可能存在延迟

### 📄 许可证

本项目仅供学习交流使用。使用本代码进行实盘交易的任何盈亏，使用者需自行承担。

### 🤝 贡献

欢迎提出问题和改进建议！

---

## English Version

### 📖 Project Introduction

A Python-based quantitative trading strategy implementing the "Tail Trading Method". This strategy screens stocks based on specific technical indicators during the last trading hour (14:30-15:00) and sells at the next day's opening, achieving short-term quick in-and-out trading.

### 🎯 Core Strategy

**Trading Logic**: Buy at tail session → Sell at next day's opening (T+1)

**8 Screening Criteria**:

1. **Price Change**: Daily gain between 2%~5%
2. **Market Cap**: 50-200 billion RMB (mid-small cap focus)
3. **Turnover Rate**: 4%~10% (ensuring liquidity)
4. **Volume Ratio**: Greater than 1 (capital inflow signal)
5. **Price-Volume Sync**: Trading volume rises with price
6. **Moving Average**: MA5 > MA10 > MA20 (bullish alignment)
7. **Outperform Index**: Stock gain exceeds market index
8. **Intraday Average**: Price above average line (not implemented due to data limitation)

### 📊 Technical Indicators

- **Turnover Rate** = Daily Volume / Float Shares × 100%
- **Volume Ratio** = Daily Volume / 5-day Average Volume
- **MA Bullish Alignment** = Short-term MA > Long-term MA

### 🚀 Quick Start

#### 1. Requirements

- Python 3.7+
- pip

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Run Strategy

```bash
python tail_trading_strategy.py
```

### 💻 Usage

#### Basic Usage

```python
from tail_trading_strategy import TailTradingStrategy

# Create strategy instance
strategy = TailTradingStrategy()

# Run single day screening
trade_date = '20231215'
selected_stocks = strategy.run_strategy(trade_date)

# View results
for stock in selected_stocks:
    print(f"{stock['code']} {stock['name']}: "
          f"Gain {stock['change_pct']:.2f}%, "
          f"Turnover {stock['turnover_rate']:.2f}%")
```

#### Advanced - Backtesting

```python
# Strategy backtest
start_date = '20230101'
end_date = '20231231'
backtest_results = strategy.backtest(start_date, end_date)

# Backtest results include:
# - Total trades
# - Average return
# - Win rate
# - Max profit/loss
# - Cumulative return
```

#### Custom Stock Pool

```python
# Screen specific stocks
test_stocks = ['000001', '600000', '000002', '600036']
selected = strategy.screen_stocks(
    stock_list=test_stocks,
    trade_date='20231215',
    index_change_pct=1.0  # Index change percentage
)
```

### 📁 Project Structure

```
tail_trading_strategy_project/
├── tail_trading_strategy.py  # Main strategy file
├── requirements.txt           # Dependencies
└── README.md                  # Documentation (this file)
```

### 📦 Dependencies

- **akshare**: Free Chinese stock market data API
- **pandas**: Data analysis and manipulation
- **numpy**: Numerical computing

### ⚠️ Risk Warning

1. **Educational Purpose**: This code is for learning and research only
2. **Historical Performance**: Past results don't guarantee future returns
3. **Market Risks**: Short-term strategies are sensitive to market sentiment:
   - Liquidity risk
   - Policy changes (T+1 trading restriction)
   - Slippage risk
4. **Live Trading**: Requires high-speed trading interface for tail session orders
5. **Parameter Tuning**: Parameters need adjustment based on market conditions

### 🔧 Optimization Directions

- Add northbound capital flow data
- Integrate dragon-tiger list information
- Implement intraday average line screening
- Add stop-loss mechanism
- Optimize parallel processing efficiency

### 📝 Limitations

1. **Intraday Average**: Not implemented due to data interface limitations
2. **Efficiency**: Full market scan is relatively slow
3. **Data Latency**: Free data sources may have delays

### 📄 License

This project is for educational and communication purposes only. Users bear full responsibility for any profit or loss from live trading.

### 🤝 Contributing

Issues and improvement suggestions are welcome!

---

## 联系方式 / Contact

如有问题或建议，欢迎提出 Issue！

For questions or suggestions, feel free to open an Issue!

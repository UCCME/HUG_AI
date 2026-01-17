# 底分型网格交易策略 / Bottom Fractal Grid Trading Strategy

[中文](#中文说明) | [English](#english-version)

---

## 中文说明

### 📖 项目简介

这是一个基于Backtrader框架实现的量化交易策略，结合了**技术分析的底分型信号**与**网格交易的仓位管理**。策略通过识别日线底分型作为入场信号，并采用五档网格分批建仓的方式来控制风险，实现低买高卖的交易目标。

### 🎯 策略核心

#### 三大核心要素

1. **开仓信号：日线底分型确认**
   - 识别底分型：当前K线最低点 < 前一日 且 < 后一日
   - 确认最低点：该底分型为近20根K线的最低点
   - 目的：捕捉阶段性底部启动点，避免追高

2. **仓位管理：五档网格分批建仓**
   - 首次开仓：买入1/5仓位（总资金的20%）
   - 补仓规则：最新仓位浮亏5%时，追加1/5仓位
   - 最多补仓：5次（满仓为止）
   - 重置机制：全部仓位清空后，重新进入开仓循环

3. **风控框架：动态回撤控制**
   - 止盈规则：任一档位盈利8%时，立即止盈卖出
   - 回撤监控：实时计算和更新最大回撤
   - 资金管理：每次开仓预留5%缓冲资金

### 📊 策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| initial_position_size | 0.2 | 首次开仓比例（1/5） |
| max_positions | 5 | 最大持仓档位数 |
| take_profit_pct | 0.08 | 止盈比例（8%） |
| add_position_pct | -0.05 | 补仓触发比例（-5%） |
| lookback_period | 20 | 底分型判断周期 |

### 🚀 快速开始

#### 1. 环境要求

- Python 3.7+
- pip

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**注意**：XtQuant库需要单独安装，如果无法安装，策略会自动切换到akshare数据源。

#### 3. 运行策略

```bash
python bottom_fractal_grid_strategy.py
```

### 💻 使用方法

#### 基础用法

```python
from bottom_fractal_grid_strategy import run_backtest

# 运行回测
symbol = '000001.SZ'  # 股票代码
start_date = '20230101'  # 开始日期
end_date = '20231231'  # 结束日期
initial_cash = 100000  # 初始资金

run_backtest(symbol, start_date, end_date, initial_cash)
```

#### 自定义策略参数

```python
import backtrader as bt
from bottom_fractal_grid_strategy import BottomFractalGridStrategy

# 创建Cerebro引擎
cerebro = bt.Cerebro()

# 添加策略并自定义参数
cerebro.addstrategy(
    BottomFractalGridStrategy,
    initial_position_size=0.2,  # 首次开仓20%
    max_positions=5,             # 最多5档
    take_profit_pct=0.10,        # 止盈10%（修改）
    add_position_pct=-0.03,      # 补仓-3%（修改）
    lookback_period=30           # 30根K线（修改）
)

# ... 添加数据和运行
```

#### 使用不同数据源

策略支持两种数据源：

1. **XtQuant**（优先，推荐）
   - 数据更稳定
   - 免费使用
   - 需要安装xtquant库

2. **akshare**（备用）
   - 完全免费
   - 安装简单
   - 数据可能有延迟

### 📁 项目结构

```
bottom_fractal_grid_strategy/
├── bottom_fractal_grid_strategy.py  # 策略主文件
├── requirements.txt                  # 依赖配置
└── README.md                         # 项目说明（本文件）
```

### 📈 策略逻辑流程

```
1. 检测底分型信号
   ↓
2. 首次开仓（1/5仓位）
   ↓
3. 监控持仓状态
   ├─→ 盈利8%？→ 止盈卖出该档位
   └─→ 浮亏5%？→ 补仓（最多5档）
   ↓
4. 全部清仓后重新检测信号
```

### 📊 回测分析指标

策略提供以下分析指标：

- **收益指标**
  - 总收益率
  - 年化收益率
  - 夏普比率

- **风险指标**
  - 最大回撤
  - 最长回撤期
  - 当前回撤

- **交易统计**
  - 总交易次数
  - 盈利次数
  - 亏损次数
  - 胜率

### ⚠️ 风险提示

1. **趋势风险**
   - 底分型可能误判
   - 单边下跌时会持续补仓
   - 建议：配合趋势指标过滤

2. **流动性风险**
   - 小盘股补仓时可能无法成交
   - 建议：选择流动性好的标的

3. **参数敏感性**
   - 止盈止损点位需根据市场调整
   - 建议：定期回测优化参数

4. **资金管理**
   - 满仓风险较大
   - 建议：预留应急资金

### 🔧 优化方向

1. **加入波动率过滤**
   ```python
   # 计算ATR（平均真实波幅）
   # 在ATR > 阈值时暂停开仓
   ```

2. **动态网格间距**
   ```python
   # 根据布林带宽度调整补仓间距
   # 波动率扩大时放宽间距
   ```

3. **多品种分散**
   ```python
   # 扩展至ETF或商品期货
   # 降低单一品种风险
   ```

4. **趋势过滤**
   ```python
   # 加入均线或MACD判断大趋势
   # 仅在上升趋势中交易
   ```

### 💡 使用建议

1. **回测验证**
   - 先进行充分的历史回测
   - 在不同市场环境下测试
   - 优化参数组合

2. **小资金试验**
   - 实盘前用小资金测试
   - 验证策略的实际表现
   - 积累实战经验

3. **严格执行**
   - 机械化执行信号
   - 不要主观干预
   - 做好交易记录

4. **风险控制**
   - 设置最大回撤限制
   - 单只股票仓位控制
   - 保持资金储备

### 📄 许可证

本项目仅供学习交流使用。使用本代码进行实盘交易的任何盈亏，使用者需自行承担。

### 🤝 贡献

欢迎提出问题和改进建议！

---

## English Version

### 📖 Project Introduction

A quantitative trading strategy implemented with Backtrader framework, combining **bottom fractal technical signals** with **grid trading position management**. The strategy identifies daily bottom fractals as entry signals and uses a five-level grid for position building to control risks and achieve buy-low-sell-high objectives.

### 🎯 Core Strategy

#### Three Core Elements

1. **Entry Signal: Daily Bottom Fractal Confirmation**
   - Identify fractal: Current low < Previous day AND < Next day
   - Confirm lowest: The fractal is the lowest point in the last 20 bars
   - Purpose: Capture stage bottom initiation, avoid chasing highs

2. **Position Management: Five-Level Grid Building**
   - Initial position: Buy 1/5 position (20% of total capital)
   - Add position: When latest position floats -5%, add another 1/5
   - Maximum adds: 5 times (full position)
   - Reset: After all positions cleared, restart entry cycle

3. **Risk Control: Dynamic Drawdown Monitoring**
   - Take profit: Close position when any level profits 8%
   - Drawdown tracking: Real-time calculation and update
   - Capital management: Reserve 5% buffer for each entry

### 📊 Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| initial_position_size | 0.2 | Initial position ratio (1/5) |
| max_positions | 5 | Maximum position levels |
| take_profit_pct | 0.08 | Take profit ratio (8%) |
| add_position_pct | -0.05 | Add position trigger (-5%) |
| lookback_period | 20 | Fractal lookback period |

### 🚀 Quick Start

#### 1. Requirements

- Python 3.7+
- pip

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: XtQuant library requires separate installation. If unavailable, the strategy will automatically switch to akshare data source.

#### 3. Run Strategy

```bash
python bottom_fractal_grid_strategy.py
```

### 💻 Usage

#### Basic Usage

```python
from bottom_fractal_grid_strategy import run_backtest

# Run backtest
symbol = '000001.SZ'  # Stock code
start_date = '20230101'  # Start date
end_date = '20231231'  # End date
initial_cash = 100000  # Initial capital

run_backtest(symbol, start_date, end_date, initial_cash)
```

#### Custom Parameters

```python
import backtrader as bt
from bottom_fractal_grid_strategy import BottomFractalGridStrategy

# Create Cerebro engine
cerebro = bt.Cerebro()

# Add strategy with custom parameters
cerebro.addstrategy(
    BottomFractalGridStrategy,
    initial_position_size=0.2,  # Initial 20%
    max_positions=5,             # Max 5 levels
    take_profit_pct=0.10,        # 10% profit (modified)
    add_position_pct=-0.03,      # -3% add (modified)
    lookback_period=30           # 30 bars (modified)
)

# ... Add data and run
```

### 📁 Project Structure

```
bottom_fractal_grid_strategy/
├── bottom_fractal_grid_strategy.py  # Main strategy file
├── requirements.txt                  # Dependencies
└── README.md                         # Documentation (this file)
```

### 📈 Strategy Logic Flow

```
1. Detect bottom fractal signal
   ↓
2. Initial entry (1/5 position)
   ↓
3. Monitor position status
   ├─→ 8% profit? → Take profit
   └─→ -5% loss? → Add position (max 5)
   ↓
4. After full exit, re-detect signals
```

### 📊 Backtest Metrics

The strategy provides these analysis metrics:

- **Return Metrics**
  - Total return
  - Annualized return
  - Sharpe ratio

- **Risk Metrics**
  - Maximum drawdown
  - Longest drawdown period
  - Current drawdown

- **Trading Statistics**
  - Total trades
  - Winning trades
  - Losing trades
  - Win rate

### ⚠️ Risk Warning

1. **Trend Risk**
   - Bottom fractals may give false signals
   - Continuous adding in downtrends
   - Suggestion: Filter with trend indicators

2. **Liquidity Risk**
   - Small-cap stocks may have execution issues
   - Suggestion: Choose liquid instruments

3. **Parameter Sensitivity**
   - Profit/loss levels need market-based adjustment
   - Suggestion: Regular backtesting and optimization

4. **Capital Management**
   - Full position carries high risk
   - Suggestion: Maintain emergency reserves

### 🔧 Optimization Directions

1. **Add Volatility Filter**
   - Calculate ATR (Average True Range)
   - Pause entries when ATR > threshold

2. **Dynamic Grid Spacing**
   - Adjust spacing based on Bollinger Band width
   - Widen spacing during high volatility

3. **Multi-Instrument Diversification**
   - Extend to ETFs or futures
   - Reduce single-instrument risk

4. **Trend Filter**
   - Add MA or MACD for trend judgment
   - Trade only in uptrends

### 💡 Usage Recommendations

1. **Backtest Validation**
   - Conduct thorough historical backtests
   - Test in different market conditions
   - Optimize parameter combinations

2. **Small Capital Testing**
   - Test with small capital before live trading
   - Verify actual performance
   - Accumulate practical experience

3. **Strict Execution**
   - Mechanically execute signals
   - Avoid subjective intervention
   - Maintain trading records

4. **Risk Control**
   - Set maximum drawdown limits
   - Control per-stock position size
   - Maintain capital reserves

### 📄 License

This project is for educational and research purposes only. Users bear full responsibility for any profit or loss from live trading.

### 🤝 Contributing

Issues and improvement suggestions are welcome!

---

## 联系方式 / Contact

如有问题或建议，欢迎提出 Issue！

For questions or suggestions, feel free to open an Issue!

# 快速开始指南

## 🚀 5分钟上手究极策略

### 步骤1：安装依赖

```bash
cd 0117_ultimate
pip install -r requirements.txt
```

**注意**：TA-Lib 需要单独安装：
- macOS: `brew install ta-lib`
- Ubuntu: `sudo apt-get install ta-lib`
- Windows: 从 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib 下载预编译包

### 步骤2：运行基础回测

```bash
python main.py
```

这将使用默认配置运行最近1年的回测。

### 步骤3：查看结果

回测完成后，你将看到：
- 📊 控制台输出的性能报告
- 📈 自动生成的图表（权益曲线、收益分布、交易分析）
- 📝 详细的交易日志文件 `trades_log.txt`

## 📝 常用命令

### 指定回测日期范围
```bash
python main.py --start-date 2023-01-01 --end-date 2024-01-01
```

### 使用本地数据
```bash
python main.py --data-provider local
```

### 修改初始资金
```bash
python main.py --initial-capital 50000
```

### 不显示图表（仅生成报告）
```bash
python main.py --no-plot
```

## 🎯 运行示例代码

```bash
python example.py
```

选择要运行的示例：
1. 基础回测
2. 自定义参数回测
3. 使用本地数据回测
4. 策略参数对比

## ⚙️ 自定义配置

编辑 `config.py` 文件来调整策略参数：

```python
# 修改止损止盈
STOP_LOSS_PCT = 0.03      # 3%止损
TAKE_PROFIT_PCT = 0.15    # 15%止盈

# 修改信号权重
WEIGHT_MA = 0.30          # 增加MA权重
WEIGHT_RSI = 0.20         # 增加RSI权重

# 修改技术指标参数
FAST_MA_PERIOD = 50       # 快线周期
SLOW_MA_PERIOD = 200      # 慢线周期
```

## 📊 理解输出结果

### 性能指标说明

- **总收益率**：整个回测期间的收益率
- **年化收益率**：按年化计算的收益率
- **夏普比率**：风险调整后的收益，>1为良好，>2为优秀
- **最大回撤**：从峰值到谷底的最大跌幅
- **胜率**：盈利交易占总交易的比例
- **盈利因子**：总盈利/总亏损，>1表示盈利

### 图表说明

1. **权益曲线图** (`equity_curve.png`)
   - 上图：投资组合价值变化
   - 中图：回撤曲线
   - 下图：持仓变化

2. **收益分布图** (`return_distribution.png`)
   - 左图：日收益率分布直方图
   - 右图：累计收益率曲线

3. **交易分析图** (`trade_analysis.png`)
   - 左上：月度收益热力图
   - 右上：关键绩效指标
   - 左下：交易盈亏分布
   - 右下：持仓时间分布

## 🔧 常见问题

### Q: 如何使用自己的数据？
A: 将数据保存为CSV格式，包含 `date, open, high, low, close, volume` 列，然后在配置中设置：
```python
config.DATA_PROVIDER = "local"
config.LOCAL_DATA_PATH = "your_data.csv"
```

### Q: 如何调整策略参数？
A: 编辑 `config.py` 文件，或在代码中创建自定义配置：
```python
config = UltimateConfig()
config.STOP_LOSS_PCT = 0.03
config.WEIGHT_MA = 0.30
```

### Q: 回测结果不理想怎么办？
A: 
1. 检查数据质量是否完整
2. 尝试调整技术指标参数
3. 修改信号权重配置
4. 调整止损止盈比例
5. 使用 `example.py` 中的策略对比功能

### Q: 如何添加新的技术指标？
A: 参考 README.md 中的"高级用法"章节

## 📚 下一步

- 阅读完整的 [README.md](README.md) 了解详细功能
- 查看 [example.py](example.py) 学习更多用法
- 修改 [config.py](config.py) 优化策略参数
- 研究源代码了解实现细节

## 💡 提示

- 回测结果不代表实盘表现
- 建议先在模拟盘测试
- 实盘交易需严格风控
- 定期检查和优化参数

---

祝你交易顺利！🎉

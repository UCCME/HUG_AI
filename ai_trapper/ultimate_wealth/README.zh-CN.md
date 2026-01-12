# Ultimate Strategy（ai_trapper 集成版）

本目录包含一个单文件策略，已将 `ai_trapper` 的各模块合并到一个可运行脚本中。策略是通用的，可应用于任意标的。

## 快速开始

运行单文件策略：

```bash
python ultimate_strategy.py
```

运行模块化「终极」策略（通过适配器整合各子项目）：

```bash
python main.py
```

不绘图运行：

```bash
python ultimate_strategy.py --no-plots
```

打开交互式菜单：

```bash
python ultimate_strategy.py --menu
```

## 配置

编辑 `ultimate_strategy.py` 顶部的 `Config` 类：

- `DATA_PROVIDER`：`local`、`yfinance` 或 `akshare`
- `SYMBOL`：任意市场标的（例如 `SPY`、`ES=F`）
- `LOCAL_DATA_PATH`：本地数据 CSV 路径
- `START_DATE` / `END_DATE`：回测时间窗口
- 风险控制与指标参数

可选的 ETF 备用数据源默认关闭：

```
ENABLE_WGC_FALLBACK = False
```

仅在需要额外 ETF 备用数据时开启。

## 模块化终极策略

模块化策略位于 `ultimate_wealth/ultimate_modular/`，负责拼接仓库内多个子项目的信号。
使用 `ultimate_wealth/main.py` 运行。

关键配置开关在 `ultimate_wealth/ultimate_modular/config.py`：

- `ENABLE_COIN_STRATEGY`, `ENABLE_SPREAD_STRATEGY`, `ENABLE_QIQUAN_STRATEGY`
- `ENABLE_SMC_STRATEGY`, `ENABLE_TRENDRADAR`
- `ENABLE_XUEQIU`, `ENABLE_X_SCRAPER`, `ENABLE_AI_HEDGE_FUND`, `ENABLE_AI_HEADHUNTER`

当适配器所需数据文件缺失或为空时，会自动跳过。

指标汇总会写入交易信号的 `indicators`，并以 `来源_指标名` 的方式命名，例如：
`coin_strategy_score`、`trendradar_score`、`ai_headhunter_candidate_count`。

可选 JSON 信号输入格式：

```json
{
  "signal": "buy",
  "confidence": 0.7
}
```

## 备注

- 脚本使用动态仓位、ATR 止损与多指标信号。
- 绘图需要 `matplotlib` 与 `seaborn`。
- 依赖缺失时脚本可自动安装（除非使用 `--no-deps`）。

## 交易知识库：双针探顶（Tweezers Top）

双针探顶本质是反转信号，表示价格两次冲高失败。但形态是否有效取决于语境。

判断有效性的 4 个维度：

1. 位置（Location）
   - 有效：出现在关键阻力位（前高、重要均线、整数关口、布林带上轨）。
   - 无效：出现在无明显阻力的半山腰位置。

2. 趋势强度（Trend Strength）
   - 无效：极强单边上升趋势中，多为“假动作”。
   - 有效：震荡末期或上行动能衰竭、缩量上涨、MACD 顶背离时。

3. 微观结构
   - 有效：放量滞涨，价格上不去。
   - 无效：缩量试探，容易被突破。

4. 确认信号（Confirmation）
   - 真正确认：第三根 K 线跌破双针实体底部。
   - 若出现小阳线或十字星，形态可能失败。

建议将该形态做标签化记录并回测，结合位置、趋势、结构与确认来提升胜率。

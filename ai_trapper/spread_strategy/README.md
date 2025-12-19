Brent-WTI Spread Strategy (布伦特/WTI 价差策略)
===============================================

本目录提供布伦特 vs WTI 价差策略的轻量实现，包含两种玩法：
- 均值回归：价差 <3 做多价差（多 Brent、空 WTI），>7 做空价差；回到 4-5 区间止盈；极值外止损。
- 网格交易：每 0.5 美元价差为一档分批加仓，价差回到基准值时整体平仓。

快速上手
--------
1) 准备数据：CSV 需含 `date,brent,wti`（示例见 `sample_data.csv`）。
2) 均值回归示例（在仓库根目录执行）：
   ```bash
   python spread_strategy/brent_wti_strategy.py --data spread_strategy/sample_data.csv --mode mean_reversion --lower 3 --upper 7 --take-profit-low 4 --take-profit-high 5 --stop-high 12
   ```
3) 网格示例（做多价差）：
   ```bash
   python spread_strategy/brent_wti_strategy.py --data spread_strategy/sample_data.csv --mode grid --grid-mode long --spacing 0.5 --base-size 0.02 --step-size 0.02
   ```
输出写入 `spread_strategy/output/` 下的 JSONL。

主要参数
--------
- `--lower/--upper`：开仓阈值（均值回归）。
- `--take-profit-low/--take-profit-high`：止盈区间。
- `--stop-low/--stop-high`：极值止损保护。
- `--spacing`：网格间距（美元/桶）。
- `--base-size/--step-size`：首单手数与每档递增手数。
- `--grid-mode`：`long` 价差缩小时逐档做多价差；`short` 价差扩大时逐档做空价差。

假设
----
- 价差 = Brent 价格 - WTI 价格（美元/桶）。
- 做多价差 = 多 Brent、空 WTI，名义 1:1。
- PnL 以每桶计，可按合约乘数放大。

已知限制
--------
- 仅离线信号/回测；不含实盘下单。
- 不含实时行情抓取，需自行提供数据。

可优化点（待选）
---------------
- 补充合约乘数与滑点/手续费参数，使 PnL 贴近实盘。
- 网格 PnL 可按加仓均价精算（当前按基准近似），便于规模较大时评估。
- 支持 Brent/WTI 不同比例的合约对冲（按美元名义匹配，而非简单 1:1）。

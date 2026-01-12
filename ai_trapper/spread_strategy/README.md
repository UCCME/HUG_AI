# Brent-WTI 价差策略

本目录提供 Brent 与 WTI 价差策略的轻量实现，包含两种模式：
- 均值回归：价差低于下阈值做多价差，高于上阈值做空价差，回到止盈带退出。
- 网格交易：以固定间距分批加仓，回到基准价差时整体平仓。

## 快速开始

1) 准备数据  
CSV 需包含 `date,brent,wti` 字段，示例见 `spread_strategy/sample_data.csv`。

2) 均值回归示例（仓库根目录执行）

```bash
python spread_strategy/brent_wti_strategy.py --data spread_strategy/sample_data.csv --mode mean_reversion --lower 3 --upper 7 --take-profit-low 4 --take-profit-high 5 --stop-high 12
```

3) 网格示例（做多价差）

```bash
python spread_strategy/brent_wti_strategy.py --data spread_strategy/sample_data.csv --mode grid --grid-mode long --spacing 0.5 --base-size 0.02 --step-size 0.02
```

输出默认写入 `spread_strategy/output/` 下的 JSONL 文件。

## 关键参数

- `--lower/--upper`：开仓阈值（均值回归）
- `--take-profit-low/--take-profit-high`：止盈带
- `--stop-low/--stop-high`：极值止损带
- `--grid-mode`：`long` 做多价差，`short` 做空价差
- `--spacing`：网格间距（美元/桶）
- `--base-size/--step-size`：首单手数与每档递增手数

## 假设与说明

- 价差 = Brent 价格 - WTI 价格（美元/桶）
- 做多价差 = 多 Brent、空 WTI（名义 1:1）
- PnL 以每桶计，可按合约乘数放大

## 已知限制

- 仅离线回测，不含实盘下单
- 不含实时行情抓取，需要自行提供数据

## 可优化点

- 补充合约乘数与滑点手续费参数，使 PnL 更贴近实盘
- 网格 PnL 可按加仓均价精算
- 支持 Brent/WTI 不同名义的对冲比例

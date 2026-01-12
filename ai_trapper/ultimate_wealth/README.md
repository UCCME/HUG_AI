# Ultimate Strategy (ai_trapper integrated)

This folder contains a single-file strategy that merges all modules from `ai_trapper`
into one runnable script. The strategy is generic and can be applied to any symbol.

## Quick Start

Run the strategy:

```bash
python ultimate_strategy.py
```

Run the modular "ultimate" strategy (all subprojects via adapters):

```bash
python main.py
```

Run without plots:

```bash
python ultimate_strategy.py --no-plots
```

Open the interactive menu:

```bash
python ultimate_strategy.py --menu
```

## Configuration

Edit the `Config` class at the top of `ultimate_strategy.py`:

- `DATA_PROVIDER`: `local`, `yfinance`, or `akshare`
- `SYMBOL`: any market symbol (e.g., `SPY`, `ES=F`)
- `LOCAL_DATA_PATH`: CSV path for local data
- `START_DATE` / `END_DATE`: backtest window
- Risk and indicator parameters

Optional ETF fallback data source is disabled by default:

```
ENABLE_WGC_FALLBACK = False
```

Enable it only if you want the extra ETF fallback fetch.

## Modular Ultimate Strategy

The modular strategy lives under `ultimate_wealth/ultimate_modular/` and stitches
signals from multiple subprojects in the repo. Use `ultimate_wealth/main.py` to run it.

Key config toggles live in `ultimate_wealth/ultimate_modular/config.py`:
- `ENABLE_COIN_STRATEGY`, `ENABLE_SPREAD_STRATEGY`, `ENABLE_QIQUAN_STRATEGY`
- `ENABLE_SMC_STRATEGY`, `ENABLE_TRENDRADAR`
- `ENABLE_XUEQIU`, `ENABLE_X_SCRAPER`, `ENABLE_AI_HEDGE_FUND`
- `ENABLE_AI_HEADHUNTER`

Adapters skip gracefully if their data files are missing or empty.

Aggregated indicators are stored on each signal under `indicators`, with keys
prefixed by the adapter name (e.g., `coin_strategy_score`, `trendradar_score`).

JSON signal inputs (optional) use this format:

```json
{
  "signal": "buy",
  "confidence": 0.7
}
```

## Notes

- The script uses dynamic position sizing, ATR stops, and multi-indicator signals.
- Plotting requires `matplotlib` and `seaborn`.
- If dependencies are missing, the script can install them (unless you run with `--no-deps`).

## Documentation

Chinese documentation: `ultimate_wealth/README.zh-CN.md`

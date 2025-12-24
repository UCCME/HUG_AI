"""
Quick SMC-style visualizer for gold 5m CSV data.

Inputs:
  - CSV columns: Date;Open;High;Low;Close;Volume
  - Use --data to point to the file (default: ../XAU_5m_data.csv from repo root)
  - Use --bars to limit the last N bars for clarity (default: 400)

Outputs:
  - PNG saved to jinshJ_index/output/smc_signals.png

Signals (lightweight approximations):
  - BOS: break of prior swing high/low (using swing window=3)
  - CH : first break in opposite direction -> potential reversal
  - OB : last opposite-colored candle before BOS, drawn as a short zone
  - FVG: 3-candle fair value gaps, highlighted as short zones
  - EQH/EQL: equal highs/lows within tolerance
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd


@dataclass
class Candle:
    idx: int
    open: float
    high: float
    low: float
    close: float


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.rename(columns=str.lower)
    return df


def find_swings(df: pd.DataFrame, window: int = 3) -> Tuple[List[int], List[int]]:
    highs, lows = [], []
    for i in range(window, len(df) - window):
        local_high = df["high"].iloc[i - window : i + window + 1].max()
        local_low = df["low"].iloc[i - window : i + window + 1].min()
        if df["high"].iloc[i] == local_high:
            highs.append(i)
        if df["low"].iloc[i] == local_low:
            lows.append(i)
    return highs, lows


def detect_bos_ch(
    df: pd.DataFrame, swing_highs: List[int], swing_lows: List[int]
) -> Tuple[List[int], List[int]]:
    bos_list, ch_list = [], []
    last_high, last_low = None, None
    last_dir = None

    for i in range(len(df)):
        if i in swing_highs:
            if last_high is not None and df["high"].iloc[i] > df["high"].iloc[last_high]:
                bos_list.append(i)  # bull BOS
                if last_dir == "down":
                    ch_list.append(i)  # change of character
                last_dir = "up"
            last_high = i
        if i in swing_lows:
            if last_low is not None and df["low"].iloc[i] < df["low"].iloc[last_low]:
                bos_list.append(i)  # bear BOS
                if last_dir == "up":
                    ch_list.append(i)
                last_dir = "down"
            last_low = i
    return bos_list, ch_list


def detect_order_blocks(df: pd.DataFrame, bos_idx: List[int]) -> List[Tuple[int, float, float]]:
    ob_zones = []
    for i in bos_idx:
        # bull BOS -> look back last red candle; bear BOS -> last green candle
        direction_up = df["close"].iloc[i] > df["open"].iloc[i]
        lookback = range(max(0, i - 10), i)[::-1]
        ob_candle = None
        for j in lookback:
            up_candle = df["close"].iloc[j] > df["open"].iloc[j]
            if direction_up and not up_candle:
                ob_candle = j
                break
            if not direction_up and up_candle:
                ob_candle = j
                break
        if ob_candle is not None:
            body_high = max(df["open"].iloc[ob_candle], df["close"].iloc[ob_candle])
            body_low = min(df["open"].iloc[ob_candle], df["close"].iloc[ob_candle])
            ob_zones.append((ob_candle, body_low, body_high))
    return ob_zones


def detect_fvg(df: pd.DataFrame) -> List[Tuple[int, float, float]]:
    zones = []
    for i in range(2, len(df)):
        # bullish gap: low[i-1] > high[i-2] and low[i] > high[i-2]
        if df["low"].iloc[i - 1] > df["high"].iloc[i - 2] and df["low"].iloc[i] > df["high"].iloc[i - 2]:
            zones.append((i, df["high"].iloc[i - 2], df["low"].iloc[i]))
        # bearish gap: high[i-1] < low[i-2] and high[i] < low[i-2]
        if df["high"].iloc[i - 1] < df["low"].iloc[i - 2] and df["high"].iloc[i] < df["low"].iloc[i - 2]:
            zones.append((i, df["high"].iloc[i], df["low"].iloc[i - 2]))
    return zones


def detect_equal_levels(
    df: pd.DataFrame, swing_highs: List[int], swing_lows: List[int], tol: float = 0.05
) -> Tuple[List[int], List[int]]:
    eqh, eql = [], []
    for i in swing_highs:
        for j in swing_highs:
            if i >= j:
                continue
            if abs(df["high"].iloc[i] - df["high"].iloc[j]) <= tol:
                eqh.extend([i, j])
    for i in swing_lows:
        for j in swing_lows:
            if i >= j:
                continue
            if abs(df["low"].iloc[i] - df["low"].iloc[j]) <= tol:
                eql.extend([i, j])
    return list(sorted(set(eqh))), list(sorted(set(eql)))


def plot_smc(df: pd.DataFrame, out_path: Path, bars: int = 400) -> None:
    df = df.tail(bars).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    swing_highs, swing_lows = find_swings(df)
    bos, ch = detect_bos_ch(df, swing_highs, swing_lows)
    ob_zones = detect_order_blocks(df, bos)
    fvg_zones = detect_fvg(df)
    eqh, eql = detect_equal_levels(df, swing_highs, swing_lows)

    fig, ax = plt.subplots(figsize=(14, 7))

    x = mdates.date2num(df["date"])
    colors = ["#2ca02c" if c >= o else "#d62728" for o, c in zip(df["open"], df["close"])]

    # width for 5m bars in matplotlib date units (~5/1440 days)
    bar_width = 5 / 1440 * 0.8

    # wicks
    ax.vlines(x, df["low"], df["high"], color=colors, linewidth=0.6, alpha=0.8)
    # bodies
    body_height = df["close"] - df["open"]
    ax.bar(x, body_height, bottom=df["open"], color=colors, width=bar_width, alpha=0.8, align="center")

    # OB zones
    for idx, low, high in ob_zones:
        ax.add_patch(
            plt.Rectangle(
                (x[idx] - bar_width, low),
                bar_width * 12,
                high - low,
                color="#ff7f0e",
                alpha=0.15,
                linewidth=0,
            )
        )

    # FVG zones
    for idx, low, high in fvg_zones:
        ax.add_patch(
            plt.Rectangle(
                (x[idx] - bar_width, low),
                bar_width * 8,
                high - low,
                color="#1f77b4",
                alpha=0.15,
                linewidth=0,
            )
        )

    # Markers
    ax.scatter(x[bos], df["high"].iloc[bos] + 0.5, marker="^", color="gold", label="BOS", zorder=5)
    ax.scatter(x[ch], df["low"].iloc[ch] - 0.5, marker="v", color="black", label="CH", zorder=5)
    ax.scatter(x[eqh], df["high"].iloc[eqh] + 0.3, marker="o", color="purple", label="EQH", s=20, zorder=5)
    ax.scatter(x[eql], df["low"].iloc[eql] - 0.3, marker="o", color="brown", label="EQL", s=20, zorder=5)

    ax.set_title(f"Gold 5m with SMC-style signals (last {len(df)} bars)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.2)
    ax.legend(loc="upper left")

    # Date formatter
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d\n%H:%M"))
    fig.autofmt_xdate()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"Saved plot to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot SMC-style signals on gold 5m CSV data.")
    parser.add_argument("--data", default="../XAU_5m_data.csv", help="Path to CSV (Date;Open;High;Low;Close;Volume)")
    parser.add_argument("--bars", type=int, default=400, help="Number of latest bars to plot")
    parser.add_argument("--output", default="jinshJ_index/output/smc_signals.png", help="Output PNG path")
    args = parser.parse_args()

    df = load_data(Path(args.data))
    plot_smc(df, Path(args.output), bars=args.bars)


if __name__ == "__main__":
    main()

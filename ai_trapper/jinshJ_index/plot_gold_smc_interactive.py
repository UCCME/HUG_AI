"""
Interactive SMC-style visualizer for gold 5m CSV data (Plotly).

Inputs:
  - CSV columns: Date;Open;High;Low;Close;Volume
  - Use --data to point to the file (default: ../XAU_5m_data.csv)
  - Use --bars to limit the last N bars (default: 800)

Output:
  - HTML with zoom/drag/range slider: jinshJ_index/output/smc_signals.html
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import plotly.graph_objects as go


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


def detect_bos_ch(df: pd.DataFrame, swing_highs: List[int], swing_lows: List[int]):
    bos_list, ch_list = [], []
    last_high, last_low = None, None
    last_dir = None
    for i in range(len(df)):
        if i in swing_highs:
            if last_high is not None and df["high"].iloc[i] > df["high"].iloc[last_high]:
                bos_list.append(i)
                if last_dir == "down":
                    ch_list.append(i)
                last_dir = "up"
            last_high = i
        if i in swing_lows:
            if last_low is not None and df["low"].iloc[i] < df["low"].iloc[last_low]:
                bos_list.append(i)
                if last_dir == "up":
                    ch_list.append(i)
                last_dir = "down"
            last_low = i
    return bos_list, ch_list


def detect_order_blocks(df: pd.DataFrame, bos_idx: List[int]) -> List[Tuple[int, float, float]]:
    ob_zones = []
    for i in bos_idx:
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
        if df["low"].iloc[i - 1] > df["high"].iloc[i - 2] and df["low"].iloc[i] > df["high"].iloc[i - 2]:
            zones.append((i, df["high"].iloc[i - 2], df["low"].iloc[i]))
        if df["high"].iloc[i - 1] < df["low"].iloc[i - 2] and df["high"].iloc[i] < df["low"].iloc[i - 2]:
            zones.append((i, df["high"].iloc[i], df["low"].iloc[i - 2]))
    return zones


def detect_equal_levels(df: pd.DataFrame, swing_highs: List[int], swing_lows: List[int], tol: float = 0.05):
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


def plot_interactive(df: pd.DataFrame, out_path: Path, bars: int = 800) -> None:
    df = df.tail(bars).reset_index(drop=True)
    swing_highs, swing_lows = find_swings(df)
    bos, ch = detect_bos_ch(df, swing_highs, swing_lows)
    ob_zones = detect_order_blocks(df, bos)
    fvg_zones = detect_fvg(df)
    eqh, eql = detect_equal_levels(df, swing_highs, swing_lows)

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing_line_color="#2ca02c",
            decreasing_line_color="#d62728",
        )
    )

    # Order blocks
    for idx, low, high in ob_zones:
        x0 = df["date"].iloc[idx]
        x1 = x0 + pd.Timedelta(minutes=60)
        fig.add_shape(
            type="rect",
            x0=x0,
            x1=x1,
            y0=low,
            y1=high,
            fillcolor="orange",
            opacity=0.15,
            line_width=0,
        )

    # FVG zones
    for idx, low, high in fvg_zones:
        x0 = df["date"].iloc[idx]
        x1 = x0 + pd.Timedelta(minutes=40)
        fig.add_shape(
            type="rect",
            x0=x0,
            x1=x1,
            y0=low,
            y1=high,
            fillcolor="blue",
            opacity=0.12,
            line_width=0,
        )

    fig.add_trace(
        go.Scatter(
            x=df["date"].iloc[bos],
            y=df["high"].iloc[bos],
            mode="markers",
            marker=dict(color="gold", symbol="triangle-up", size=10),
            name="BOS",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"].iloc[ch],
            y=df["low"].iloc[ch],
            mode="markers",
            marker=dict(color="black", symbol="triangle-down", size=10),
            name="CH",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"].iloc[eqh],
            y=df["high"].iloc[eqh],
            mode="markers",
            marker=dict(color="purple", symbol="circle", size=6),
            name="EQH",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"].iloc[eql],
            y=df["low"].iloc[eql],
            mode="markers",
            marker=dict(color="brown", symbol="circle", size=6),
            name="EQL",
        )
    )

    fig.update_layout(
        title=f"Gold 5m SMC signals (last {len(df)} bars)",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis=dict(rangeslider=dict(visible=True)),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(out_path)
    print(f"Saved interactive plot to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot interactive SMC signals (Plotly) on gold 5m CSV.")
    parser.add_argument("--data", default="../XAU_5m_data.csv", help="Path to CSV (Date;Open;High;Low;Close;Volume)")
    parser.add_argument("--bars", type=int, default=800, help="Number of latest bars to plot")
    parser.add_argument("--output", default="jinshJ_index/output/smc_signals.html", help="Output HTML path")
    args = parser.parse_args()

    df = load_data(Path(args.data))
    plot_interactive(df, Path(args.output), bars=args.bars)


if __name__ == "__main__":
    main()

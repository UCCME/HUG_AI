"""
Brent-WTI spread strategy simulator.

Two modes:
- mean_reversion: enter when spread < lower or > upper; exit in take-profit band; stop if out of range.
- grid: scale in every spacing step, flatten when price returns to the base.

Usage examples:
  python brent_wti_strategy.py --data spread_strategy/sample_data.csv --mode mean_reversion
  python brent_wti_strategy.py --data spread_strategy/sample_data.csv --mode grid --grid-mode long
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PricePoint:
    date: str
    brent: float
    wti: float

    @property
    def spread(self) -> float:
        return self.brent - self.wti


@dataclass
class TradeEvent:
    date: str
    spread: float
    action: str  # open/close/stop/grid_fill/grid_flatten
    direction: str  # long_spread/short_spread/flat
    size: float
    reason: str
    pnl_per_barrel: Optional[float] = None
    entry_date: Optional[str] = None
    entry_spread: Optional[float] = None


def load_prices(path: Path) -> List[PricePoint]:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = {h.lower(): h for h in (reader.fieldnames or [])}
        brent_key = next((headers[k] for k in headers if k in {"brent", "brent_price", "brentusd", "brent_usd"}), None)
        wti_key = next((headers[k] for k in headers if k in {"wti", "wti_price", "wtiusd", "wti_usd"}), None)
        date_key = next((headers[k] for k in headers if k in {"date", "time", "timestamp"}), None)

        if not brent_key or not wti_key:
            raise ValueError("CSV must contain headers for Brent and WTI prices (e.g., brent, wti).")

        data: List[PricePoint] = []
        for idx, row in enumerate(reader, start=1):
            try:
                brent = float(row[brent_key])
                wti = float(row[wti_key])
            except Exception as exc:
                raise ValueError(f"Failed to parse prices on row {idx}: {row}") from exc
            date_val = row.get(date_key) if date_key else None
            data.append(PricePoint(date=date_val or f"row_{idx}", brent=brent, wti=wti))
    if not data:
        raise ValueError("No data rows found in CSV.")
    return data


def mean_reversion_signals(
    prices: List[PricePoint],
    lower: float,
    upper: float,
    take_profit_low: float,
    take_profit_high: float,
    stop_low: float,
    stop_high: float,
) -> List[TradeEvent]:
    events: List[TradeEvent] = []
    position: Optional[TradeEvent] = None

    for p in prices:
        spread = p.spread
        if position is None:
            if spread < lower:
                position = TradeEvent(
                    date=p.date,
                    spread=spread,
                    action="open",
                    direction="long_spread",
                    size=1.0,
                    reason="spread_below_lower",
                )
                events.append(position)
            elif spread > upper:
                position = TradeEvent(
                    date=p.date,
                    spread=spread,
                    action="open",
                    direction="short_spread",
                    size=1.0,
                    reason="spread_above_upper",
                )
                events.append(position)
            continue

        # Manage open position
        stop_hit = spread >= stop_high or spread <= stop_low
        in_take_band = take_profit_low <= spread <= take_profit_high

        if stop_hit:
            pnl = compute_pnl(position.direction, position.spread, spread)
            events.append(
                TradeEvent(
                    date=p.date,
                    spread=spread,
                    action="stop",
                    direction="flat",
                    size=0.0,
                    reason="stop_out",
                    pnl_per_barrel=pnl,
                    entry_date=position.date,
                    entry_spread=position.spread,
                )
            )
            position = None
        elif in_take_band:
            pnl = compute_pnl(position.direction, position.spread, spread)
            events.append(
                TradeEvent(
                    date=p.date,
                    spread=spread,
                    action="close",
                    direction="flat",
                    size=0.0,
                    reason="take_profit_band",
                    pnl_per_barrel=pnl,
                    entry_date=position.date,
                    entry_spread=position.spread,
                )
            )
            position = None

    if position is not None:
        # Mark remaining open position
        events.append(
            TradeEvent(
                date=prices[-1].date,
                spread=prices[-1].spread,
                action="open_unclosed",
                direction=position.direction,
                size=position.size,
                reason="still_open_at_end",
                entry_date=position.date,
                entry_spread=position.spread,
            )
        )
    return events


def grid_signals(
    prices: List[PricePoint],
    grid_mode: str,
    spacing: float,
    base_size: float,
    step_size: float,
    max_steps: int,
) -> List[TradeEvent]:
    if grid_mode not in {"long", "short"}:
        raise ValueError("grid_mode must be 'long' or 'short'.")

    base_spread = prices[0].spread
    filled_steps = 0
    size_accum = 0.0
    events: List[TradeEvent] = []

    for p in prices:
        spread = p.spread
        if grid_mode == "long":
            steps_now = math.floor((base_spread - spread) / spacing)
            direction = "long_spread"
            should_close = size_accum > 0 and spread >= base_spread
        else:
            steps_now = math.floor((spread - base_spread) / spacing)
            direction = "short_spread"
            should_close = size_accum < 0 and spread <= base_spread

        # New fills when moving deeper into grid
        while steps_now > filled_steps and filled_steps < max_steps:
            order_size = base_size + filled_steps * step_size
            size_accum += order_size if grid_mode == "long" else -order_size
            events.append(
                TradeEvent(
                    date=p.date,
                    spread=spread,
                    action="grid_fill",
                    direction=direction,
                    size=order_size,
                    reason=f"grid_step_{filled_steps+1}",
                )
            )
            filled_steps += 1

        # Flatten when reverting to base
        if should_close and size_accum != 0:
            pnl = compute_grid_pnl(direction, base_spread, spread, size_accum)
            events.append(
                TradeEvent(
                    date=p.date,
                    spread=spread,
                    action="grid_flatten",
                    direction="flat",
                    size=-size_accum,
                    reason="revert_to_base",
                    pnl_per_barrel=pnl,
                )
            )
            size_accum = 0.0
            filled_steps = 0

    # Mark residual position if any
    if size_accum != 0:
        events.append(
            TradeEvent(
                date=prices[-1].date,
                spread=prices[-1].spread,
                action="grid_unclosed",
                direction=direction,
                size=size_accum,
                reason="still_open_at_end",
            )
        )
    return events


def compute_pnl(direction: str, entry_spread: float, exit_spread: float) -> float:
    if direction == "long_spread":
        return exit_spread - entry_spread
    if direction == "short_spread":
        return entry_spread - exit_spread
    return 0.0


def compute_grid_pnl(direction: str, base_spread: float, exit_spread: float, size_accum: float) -> float:
    # Approximate pnl using average entry near base; grid size_accum reflects signed exposure.
    if direction == "long_spread":
        return (exit_spread - base_spread) * (size_accum / abs(size_accum))
    return (base_spread - exit_spread) * (size_accum / abs(size_accum))


def write_events(events: List[TradeEvent], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Brent-WTI spread strategy simulator")
    parser.add_argument("--data", required=True, help="CSV path with columns: date, brent, wti")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["mean_reversion", "grid"],
        help="Strategy mode to run",
    )
    parser.add_argument("--lower", type=float, default=3.0, help="Lower threshold to go long spread")
    parser.add_argument("--upper", type=float, default=7.0, help="Upper threshold to go short spread")
    parser.add_argument("--take-profit-low", type=float, default=4.0, help="Take profit band low")
    parser.add_argument("--take-profit-high", type=float, default=5.0, help="Take profit band high")
    parser.add_argument("--stop-low", type=float, default=-20.0, help="Stop if spread falls below this value")
    parser.add_argument("--stop-high", type=float, default=12.0, help="Stop if spread rises above this value")
    parser.add_argument("--grid-mode", choices=["long", "short"], default="long", help="Grid direction")
    parser.add_argument("--spacing", type=float, default=0.5, help="Grid spacing in USD")
    parser.add_argument("--base-size", type=float, default=0.02, help="First grid order size")
    parser.add_argument("--step-size", type=float, default=0.02, help="Incremental size per grid step")
    parser.add_argument("--max-steps", type=int, default=30, help="Max grid steps to scale")
    parser.add_argument(
        "--output",
        default="spread_strategy/output/signals.jsonl",
        help="Output JSONL path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prices = load_prices(Path(args.data))
    out_path = Path(args.output)

    if args.mode == "mean_reversion":
        events = mean_reversion_signals(
            prices=prices,
            lower=args.lower,
            upper=args.upper,
            take_profit_low=args.take_profit_low,
            take_profit_high=args.take_profit_high,
            stop_low=args.stop_low,
            stop_high=args.stop_high,
        )
    else:
        events = grid_signals(
            prices=prices,
            grid_mode=args.grid_mode,
            spacing=args.spacing,
            base_size=args.base_size,
            step_size=args.step_size,
            max_steps=args.max_steps,
        )

    write_events(events, out_path)
    print(f"Generated {len(events)} events -> {out_path}")


if __name__ == "__main__":
    main()

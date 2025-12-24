import argparse
import csv
import datetime as dt
import math
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Config:
    initial_cash: float = 29000.0
    risk_per_trade: float = 0.25
    max_loss_tolerance: float = 0.5
    expiry_days: int = 45
    time_stop_days: int = 7
    roll_attack_ratio: float = 0.30
    roll_trigger_pct: float = 0.08
    roll_cooldown_days: int = 3
    otm_offset_pct: float = 0.03
    time_value_scale: float = 0.08
    iv_default: float = 0.35
    iv_exit: float = 0.90
    take_profit_pct: float = 0.80
    stop_move_pct: float = 0.12
    withdraw_step: float = 1.6
    withdraw_ratio: float = 0.40
    strike_step: float = 50.0


@dataclass
class Position:
    direction: str
    strike: float
    expiry: dt.datetime
    premium: float
    qty: float
    entry_date: dt.datetime
    entry_price: float

    def value(self, underlying: float, iv: float, now: dt.datetime, time_value_scale: float) -> float:
        days_to_expiry = max((self.expiry - now).days, 0)
        price = option_price(self.direction, underlying, self.strike, iv, days_to_expiry, time_value_scale)
        return price * self.qty


@dataclass
class TradeLog:
    rows: List[List[str]] = field(default_factory=list)

    def add(self, now: dt.datetime, action: str, detail: str, cash: float, equity: float) -> None:
        self.rows.append([
            now.strftime("%Y-%m-%d"),
            action,
            detail,
            f"{cash:.2f}",
            f"{equity:.2f}",
        ])


def parse_date(value: str) -> dt.datetime:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return dt.datetime.fromisoformat(value)


def round_strike(price: float, step: float) -> float:
    return round(price / step) * step


def option_price(direction: str, underlying: float, strike: float, iv: float, days_to_expiry: int, time_value_scale: float) -> float:
    if direction == "call":
        intrinsic = max(underlying - strike, 0.0)
    else:
        intrinsic = max(strike - underlying, 0.0)
    t = max(days_to_expiry, 1) / 365.0
    time_value = max(0.0, underlying * iv * math.sqrt(t) * time_value_scale)
    return max(intrinsic + time_value, 0.01)


def read_price_series(path: Optional[str]) -> List[Tuple[dt.datetime, float]]:
    if not path or not os.path.exists(path):
        return generate_synthetic_series()

    series = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_key = row.get("date") or row.get("datetime") or row.get("time")
            if not date_key:
                continue
            price = float(row.get("close") or row.get("price") or row.get("last") or 0.0)
            series.append((parse_date(date_key), price))
    return series


def read_events(path: Optional[str]) -> Dict[dt.datetime, Dict[str, str]]:
    if not path or not os.path.exists(path):
        return {}

    events: Dict[dt.datetime, Dict[str, str]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_key = row.get("date") or row.get("datetime")
            if not date_key:
                continue
            when = parse_date(date_key)
            events[when.date()] = {
                "direction": (row.get("direction") or "call").strip().lower(),
                "note": (row.get("note") or "").strip(),
                "iv": (row.get("iv") or "").strip(),
            }
    return events


def generate_synthetic_series(days: int = 260, seed: int = 7) -> List[Tuple[dt.datetime, float]]:
    random.seed(seed)
    start = dt.datetime(2024, 1, 2)
    price = 100.0
    series = []
    for i in range(days):
        drift = 0.03 / 252
        shock = random.gauss(0, 0.02)
        price *= (1 + drift + shock)
        series.append((start + dt.timedelta(days=i), price))
    return series


def simple_trend_signal(series: List[Tuple[dt.datetime, float]], idx: int, short: int = 10, long: int = 30) -> Optional[str]:
    if idx < long:
        return None
    short_avg = sum(p for _, p in series[idx - short:idx]) / short
    long_avg = sum(p for _, p in series[idx - long:idx]) / long
    if short_avg > long_avg * 1.002:
        return "call"
    if short_avg < long_avg * 0.998:
        return "put"
    return None


def equity_value(positions: List[Position], underlying: float, iv: float, now: dt.datetime, cfg: Config) -> float:
    return sum(pos.value(underlying, iv, now, cfg.time_value_scale) for pos in positions)


def open_position(
    positions: List[Position],
    cash: float,
    now: dt.datetime,
    underlying: float,
    direction: str,
    iv: float,
    cfg: Config,
) -> Tuple[float, Optional[Position]]:
    risk_budget = cash * cfg.risk_per_trade
    if risk_budget <= 0:
        return cash, None

    strike = round_strike(underlying, cfg.strike_step)
    if direction == "call":
        strike = strike
    else:
        strike = strike

    expiry = now + dt.timedelta(days=cfg.expiry_days)
    premium = option_price(direction, underlying, strike, iv, cfg.expiry_days, cfg.time_value_scale)
    qty = risk_budget / premium
    cost = qty * premium
    if cost > cash or cost <= 0:
        return cash, None

    cash -= cost
    pos = Position(direction, strike, expiry, premium, qty, now, underlying)
    positions.append(pos)
    return cash, pos


def reduce_positions_by_ratio(positions: List[Position], ratio: float) -> float:
    released = 0.0
    if not positions or ratio <= 0:
        return released

    for pos in positions:
        pos.qty *= (1 - ratio)
    return released


def roll_positions(
    positions: List[Position],
    cash: float,
    now: dt.datetime,
    underlying: float,
    iv: float,
    cfg: Config,
) -> float:
    if not positions:
        return cash

    total_value = equity_value(positions, underlying, iv, now, cfg)
    if total_value <= 0:
        return cash

    roll_budget = total_value * cfg.roll_attack_ratio
    cash += roll_budget
    for pos in positions:
        pos.qty *= (1 - cfg.roll_attack_ratio)

    direction = positions[0].direction
    if direction == "call":
        strike = round_strike(underlying * (1 + cfg.otm_offset_pct), cfg.strike_step)
    else:
        strike = round_strike(underlying * (1 - cfg.otm_offset_pct), cfg.strike_step)

    expiry = now + dt.timedelta(days=cfg.expiry_days)
    premium = option_price(direction, underlying, strike, iv, cfg.expiry_days, cfg.time_value_scale)
    qty = roll_budget / premium
    cost = qty * premium
    cash -= cost
    positions.append(Position(direction, strike, expiry, premium, qty, now, underlying))
    return cash


def write_csv(path: str, header: List[str], rows: List[List[str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def run_simulation(prices: List[Tuple[dt.datetime, float]], events: Dict[dt.datetime, Dict[str, str]], cfg: Config) -> None:
    cash = cfg.initial_cash
    withdrawn = 0.0
    positions: List[Position] = []
    last_roll: Optional[dt.datetime] = None
    last_entry: Optional[dt.datetime] = None
    last_withdraw_mark = cfg.initial_cash

    equity_rows: List[List[str]] = []
    trades = TradeLog()

    for idx, (now, price) in enumerate(prices):
        iv = cfg.iv_default
        event = events.get(now.date())
        if event and event.get("iv"):
            try:
                iv = float(event["iv"])
            except ValueError:
                iv = cfg.iv_default

        pos_value = equity_value(positions, price, iv, now, cfg)
        equity = cash + pos_value

        equity_rows.append([now.strftime("%Y-%m-%d"), f"{price:.2f}", f"{cash:.2f}", f"{pos_value:.2f}", f"{equity:.2f}"])

        if positions:
            age_days = (now - positions[0].entry_date).days
            move = (price - positions[0].entry_price) / positions[0].entry_price
            if positions[0].direction == "put":
                move = -move

            if age_days >= cfg.time_stop_days and pos_value <= sum(p.premium * p.qty for p in positions):
                cash += pos_value
                positions.clear()
                trades.add(now, "exit_time", "time_stop", cash, cash)
                continue

            if move <= -cfg.stop_move_pct:
                cash += pos_value
                positions.clear()
                trades.add(now, "exit_stop", "logic_invalid", cash, cash)
                continue

            if move >= cfg.take_profit_pct or iv >= cfg.iv_exit:
                cash += pos_value
                positions.clear()
                trades.add(now, "exit_profit", "profit_or_iv", cash, cash)
                continue

            if move >= cfg.roll_trigger_pct:
                if not last_roll or (now - last_roll).days >= cfg.roll_cooldown_days:
                    cash = roll_positions(positions, cash, now, price, iv, cfg)
                    last_roll = now
                    trades.add(now, "roll", f"attack_{cfg.roll_attack_ratio:.0%}", cash, cash + equity_value(positions, price, iv, now, cfg))

        if not positions:
            direction = None
            if event:
                direction = event.get("direction", "call")
            else:
                direction = simple_trend_signal(prices, idx)

            if direction:
                if last_entry is None or (now - last_entry).days >= 5:
                    cash, pos = open_position(positions, cash, now, price, direction, iv, cfg)
                    if pos:
                        last_entry = now
                        trades.add(now, "entry", direction, cash, cash + equity_value(positions, price, iv, now, cfg))

        if equity >= last_withdraw_mark * cfg.withdraw_step:
            withdraw_amount = equity * cfg.withdraw_ratio
            if withdraw_amount <= cash:
                cash -= withdraw_amount
                withdrawn += withdraw_amount
                last_withdraw_mark = equity
                trades.add(now, "withdraw", f"{withdraw_amount:.2f}", cash, cash + pos_value)

    summary = [
        ["initial_cash", f"{cfg.initial_cash:.2f}"],
        ["ending_cash", f"{cash:.2f}"],
        ["withdrawn", f"{withdrawn:.2f}"],
        ["ending_equity", f"{cash + equity_value(positions, prices[-1][1], cfg.iv_default, prices[-1][0], cfg):.2f}"],
    ]

    write_csv("qiquan_bisai/equity_curve.csv", ["date", "price", "cash", "position_value", "equity"], equity_rows)
    write_csv("qiquan_bisai/trade_log.csv", ["date", "action", "detail", "cash", "equity"], trades.rows)
    write_csv("qiquan_bisai/summary.csv", ["metric", "value"], summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggressive options strategy simulator")
    parser.add_argument("--price", help="CSV with date, close columns")
    parser.add_argument("--events", help="CSV with date, direction, iv, note columns")
    args = parser.parse_args()

    cfg = Config()
    prices = read_price_series(args.price)
    events = read_events(args.events)
    run_simulation(prices, events, cfg)


if __name__ == "__main__":
    main()

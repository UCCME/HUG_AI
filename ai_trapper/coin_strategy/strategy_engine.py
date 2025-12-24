import argparse
import csv
import datetime as dt
import math
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Config:
    initial_cash: float = 10000.0
    max_position_pct: float = 0.10
    stop_loss_pct: float = 0.03
    take_profit_rr: float = 2.0
    cooldown_days: int = 1
    min_signal_score: int = 2


@dataclass
class Bar:
    date: dt.datetime
    close: float


@dataclass
class Sentiment:
    date: dt.datetime
    funding: float
    liquidation: float


@dataclass
class Trade:
    entry_date: dt.datetime
    entry_price: float
    side: str
    size: float
    stop: float
    take: float


def parse_date(value: str) -> dt.datetime:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return dt.datetime.fromisoformat(value)


def read_price_series(path: Optional[str]) -> List[Bar]:
    if not path or not os.path.exists(path):
        return generate_synthetic_prices()

    rows: List[Bar] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_key = row.get("date") or row.get("datetime") or row.get("time")
            if not date_key:
                continue
            price = float(row.get("close") or row.get("price") or row.get("last") or 0.0)
            rows.append(Bar(parse_date(date_key), price))
    return rows


def read_sentiment(path: Optional[str]) -> Dict[dt.date, Sentiment]:
    if not path or not os.path.exists(path):
        return generate_synthetic_sentiment()

    rows: Dict[dt.date, Sentiment] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_key = row.get("date") or row.get("datetime")
            if not date_key:
                continue
            when = parse_date(date_key)
            funding = float(row.get("funding") or 0.0)
            liquidation = float(row.get("liquidation") or 0.0)
            rows[when.date()] = Sentiment(when, funding, liquidation)
    return rows


def generate_synthetic_prices(days: int = 200, seed: int = 7) -> List[Bar]:
    random.seed(seed)
    start = dt.datetime(2024, 1, 2)
    price = 100.0
    series: List[Bar] = []
    for i in range(days):
        drift = 0.05 / 252
        shock = random.gauss(0, 0.02)
        price *= (1 + drift + shock)
        series.append(Bar(start + dt.timedelta(days=i), price))
    return series


def generate_synthetic_sentiment(days: int = 200, seed: int = 8) -> Dict[dt.date, Sentiment]:
    random.seed(seed)
    start = dt.datetime(2024, 1, 2)
    data: Dict[dt.date, Sentiment] = {}
    for i in range(days):
        funding = random.uniform(-0.03, 0.03)
        liquidation = abs(random.gauss(0, 1))
        when = start + dt.timedelta(days=i)
        data[when.date()] = Sentiment(when, funding, liquidation)
    return data


def sma(values: List[float], length: int) -> Optional[float]:
    if len(values) < length:
        return None
    return sum(values[-length:]) / length


def compute_signal(price_series: List[Bar], idx: int, sentiment: Optional[Sentiment]) -> Tuple[int, Optional[str]]:
    if idx < 30:
        return 0, None

    closes = [b.close for b in price_series[: idx + 1]]
    fast = sma(closes, 10)
    slow = sma(closes, 30)

    score = 0
    side = None

    if fast is not None and slow is not None:
        if fast > slow * 1.002:
            score += 1
            side = "long"
        elif fast < slow * 0.998:
            score += 1
            side = "short"

    if sentiment:
        if sentiment.funding > 0.02:
            score += 1
            side = "short"
        elif sentiment.funding < -0.02:
            score += 1
            side = "long"

        if sentiment.liquidation > 2.0:
            score += 1

    if score >= 2:
        return score, side
    return score, None


def run_backtest(prices: List[Bar], sentiment_map: Dict[dt.date, Sentiment], cfg: Config) -> None:
    cash = cfg.initial_cash
    trade: Optional[Trade] = None
    last_entry: Optional[dt.datetime] = None

    rows: List[List[str]] = []

    for i, bar in enumerate(prices):
        sentiment = sentiment_map.get(bar.date.date())

        if trade:
            pnl = (bar.close - trade.entry_price) / trade.entry_price
            if trade.side == "short":
                pnl = -pnl

            stop_hit = bar.close <= trade.stop if trade.side == "long" else bar.close >= trade.stop
            take_hit = bar.close >= trade.take if trade.side == "long" else bar.close <= trade.take

            if stop_hit or take_hit:
                cash += trade.size * (1 + pnl)
                rows.append([
                    bar.date.strftime("%Y-%m-%d"),
                    "exit",
                    trade.side,
                    f"{bar.close:.2f}",
                    f"{pnl:.4f}",
                    f"{cash:.2f}",
                ])
                trade = None

        if not trade:
            if last_entry and (bar.date - last_entry).days < cfg.cooldown_days:
                continue

            score, side = compute_signal(prices, i, sentiment)
            if side:
                risk_cash = cash * cfg.max_position_pct
                entry = bar.close
                stop = entry * (1 - cfg.stop_loss_pct) if side == "long" else entry * (1 + cfg.stop_loss_pct)
                take = entry * (1 + cfg.stop_loss_pct * cfg.take_profit_rr) if side == "long" else entry * (1 - cfg.stop_loss_pct * cfg.take_profit_rr)

                trade = Trade(bar.date, entry, side, risk_cash, stop, take)
                cash -= risk_cash
                last_entry = bar.date
                rows.append([
                    bar.date.strftime("%Y-%m-%d"),
                    "entry",
                    side,
                    f"{entry:.2f}",
                    f"score={score}",
                    f"{cash:.2f}",
                ])

        rows.append([
            bar.date.strftime("%Y-%m-%d"),
            "mark",
            trade.side if trade else "none",
            f"{bar.close:.2f}",
            "",
            f"{cash:.2f}",
        ])

    output_path = "coin_strategy/trade_log.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "action", "side", "price", "detail", "cash"])
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto tool-light strategy engine")
    parser.add_argument("--price", help="CSV with date, close columns")
    parser.add_argument("--sentiment", help="CSV with date, funding, liquidation columns")
    args = parser.parse_args()

    cfg = Config()
    prices = read_price_series(args.price)
    sentiment = read_sentiment(args.sentiment)
    run_backtest(prices, sentiment, cfg)


if __name__ == "__main__":
    main()

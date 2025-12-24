import csv
import datetime as dt
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Report:
    initial_cash: float
    ending_cash: float
    total_trades: int
    win_rate: float
    avg_pnl: float


def parse_trade_log(path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def compute_report(rows: List[Dict[str, str]]) -> Report:
    entries = [r for r in rows if r["action"] == "entry"]
    exits = [r for r in rows if r["action"] == "exit"]

    pnls: List[float] = []
    cash_values = [float(r["cash"]) for r in rows if r["action"] in ("entry", "exit", "mark")]

    for exit_row in exits:
        detail = exit_row.get("detail", "")
        if detail:
            try:
                pnls.append(float(detail))
            except ValueError:
                continue

    win_rate = 0.0
    if pnls:
        win_rate = sum(1 for p in pnls if p > 0) / len(pnls)

    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

    return Report(
        initial_cash=cash_values[0] if cash_values else 0.0,
        ending_cash=cash_values[-1] if cash_values else 0.0,
        total_trades=len(entries),
        win_rate=win_rate,
        avg_pnl=avg_pnl,
    )


def write_summary(report: Report, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["initial_cash", f"{report.initial_cash:.2f}"])
        writer.writerow(["ending_cash", f"{report.ending_cash:.2f}"])
        writer.writerow(["total_trades", report.total_trades])
        writer.writerow(["win_rate", f"{report.win_rate:.2%}"])
        writer.writerow(["avg_pnl", f"{report.avg_pnl:.4f}"])


def main() -> None:
    trade_log_path = "coin_strategy/trade_log.csv"
    rows = parse_trade_log(trade_log_path)
    report = compute_report(rows)
    write_summary(report, "coin_strategy/summary.csv")


if __name__ == "__main__":
    main()

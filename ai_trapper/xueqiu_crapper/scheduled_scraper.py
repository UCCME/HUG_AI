import subprocess
import sys
import time
import datetime
from pathlib import Path

# Try to load config; fall back to defaults if missing.
try:
    from scheduler_config import SchedulerConfig, ScraperConfig
except ImportError:
    class SchedulerConfig:
        INTERVAL_MINUTES = 30
        INCREMENTAL = True
        ONCE = False
        LOG_DIR = "logs"
        LOG_MAX_FILES = 50

    class ScraperConfig:
        USER_IDS = [
            1247347556,
            2347043226,
        ]
        PAGES = 2
        COUNT = 20
        DELAY = 3.0
        FORMAT = "jsonl"
        OUTDIR = "output"
        DOWNLOAD_IMAGES = True


def _get_log_dir() -> Path:
    log_dir_name = getattr(SchedulerConfig, "LOG_DIR", "logs")
    return Path(__file__).resolve().parent / log_dir_name


def _prune_logs(log_dir: Path, max_files: int) -> None:
    if max_files <= 0:
        return
    files = sorted(log_dir.glob("scrape_*.log"), key=lambda p: p.stat().st_mtime)
    while len(files) > max_files:
        files.pop(0).unlink(missing_ok=True)


def scrape_with_logging(incremental: bool = False) -> bool:
    """
    Run the scraper and persist stdout to a timestamped log file.
    """
    log_dir = _get_log_dir()
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"scrape_{timestamp}.log"

    base_dir = Path(__file__).resolve().parent
    cmd = [sys.executable, "scrape_presets.py"]

    if incremental or SchedulerConfig.INCREMENTAL:
        cmd.append("--incremental")

    print(f"Starting scheduled scrape: {datetime.datetime.now()}")
    print(f"Log file: {log_file}")
    print("Running scraper...")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(base_dir),
        )

        output = result.stdout or ""
        log_file.write_text(output, encoding="utf-8")
        print(output)
        print(f"Scrape completed: {datetime.datetime.now()}")
        print(f"Log written to: {log_file}")
        _prune_logs(log_dir, int(getattr(SchedulerConfig, "LOG_MAX_FILES", 50)))
        return True
    except subprocess.CalledProcessError as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        error_msg = f"Scrape failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}"
        print(error_msg)
        log_file.write_text(error_msg, encoding="utf-8")
        _prune_logs(log_dir, int(getattr(SchedulerConfig, "LOG_MAX_FILES", 50)))
        return False
    except FileNotFoundError:
        error_msg = "scrape_presets.py not found. Run from the xueqiu_crapper directory."
        print(error_msg)
        log_file.write_text(error_msg, encoding="utf-8")
        sys.exit(1)


def run_scheduler(interval_minutes: int | None = None, incremental: bool | None = None) -> None:
    """
    Run scheduled scraping on a fixed interval.
    """
    interval = interval_minutes or SchedulerConfig.INTERVAL_MINUTES
    incr_mode = incremental if incremental is not None else SchedulerConfig.INCREMENTAL

    print(f"Scheduler started. Interval: {interval} minutes")
    print(f"Incremental mode: {'on' if incr_mode else 'off'}")
    print("Press Ctrl+C to stop.")

    while True:
        try:
            success = scrape_with_logging(incremental=incr_mode)

            if success:
                print(f"Scrape success. Next run in {interval} minutes...")
            else:
                print(f"Scrape failed. Next run in {interval} minutes...")

            time.sleep(interval * 60)
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as exc:
            print(f"Unexpected error: {exc}")
            print(f"Retrying in {interval} minutes...")
            time.sleep(interval * 60)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Scheduled Xueqiu scraper runner")
    parser.add_argument(
        "--interval",
        type=int,
        default=SchedulerConfig.INTERVAL_MINUTES,
        help="Interval in minutes between runs",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=SchedulerConfig.ONCE,
        help="Run only once and exit",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=SchedulerConfig.INCREMENTAL,
        help="Enable incremental mode (append new items only)",
    )
    args = parser.parse_args()

    if args.once:
        scrape_with_logging(incremental=args.incremental)
    else:
        run_scheduler(args.interval, args.incremental)


if __name__ == "__main__":
    main()

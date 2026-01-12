"""
Modular ultimate strategy configuration.
"""
from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent


class Config:
    # Core data source (ai_trapper)
    DATA_PROVIDER = "local"  # "local", "akshare", "yfinance"
    SYMBOL = "GC=F"
    AK_SYMBOL = "AU0"
    FALLBACK_SYMBOL = "GLD"
    LOCAL_DATA_PATH = REPO_ROOT / "XAU_5m_data.csv"
    USE_LOCAL_ON_FAIL = True
    MAX_FETCH_RETRIES = 6
    RETRY_BACKOFF_BASE = 2

    START_DATE = "2016-01-01"
    END_DATE = "2024-12-12"

    # Strategy parameters (ai_trapper)
    FAST_MA_PERIOD = 72
    SLOW_MA_PERIOD = 216
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    SR_LOOKBACK = 50
    SR_PROXIMITY_PCT = 0.003
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9

    INITIAL_CAPITAL = 100000.0
    COMMISSION_RATE = 0.002
    SLIPPAGE = 0.001
    POSITION_SIZE = 0.95
    MAX_DRAWDOWN = 0.20
    STOP_LOSS_PCT = 0.05
    TAKE_PROFIT_PCT = 0.10

    # Modular toggles
    ENABLE_AI_TRAPPER_BASE = True
    ENABLE_COIN_STRATEGY = True
    ENABLE_SPREAD_STRATEGY = True
    ENABLE_QIQUAN_STRATEGY = True
    ENABLE_SMC_STRATEGY = True
    ENABLE_TRENDRADAR = True
    ENABLE_XUEQIU = True
    ENABLE_X_SCRAPER = True
    ENABLE_AI_HEDGE_FUND = True
    ENABLE_AI_HEADHUNTER = True

    # Coin strategy inputs
    COIN_PRICE_PATH = REPO_ROOT / "coin_strategy" / "sample_price.csv"
    COIN_SENTIMENT_PATH = REPO_ROOT / "coin_strategy" / "sample_sentiment.csv"

    # Spread strategy inputs
    SPREAD_DATA_PATH = REPO_ROOT / "spread_strategy" / "sample_data.csv"
    SPREAD_UPPER = 5.0
    SPREAD_LOWER = -5.0

    # Options strategy inputs
    QIQUAN_PRICE_PATH = REPO_ROOT / "qiquan_bisai" / "sample_price.csv"
    QIQUAN_EVENTS_PATH = REPO_ROOT / "qiquan_bisai" / "sample_events.csv"
    QIQUAN_IV_RISK_OFF = 0.70

    # SMC (jinshJ_index) parameters
    SMC_LOOKBACK_BARS = 400
    SMC_SWING_WINDOW = 3

    # TrendRadar inputs
    TRENDRADAR_OUTPUT_DIR = REPO_ROOT / "TrendRadar" / "output"
    TRENDRADAR_BULL_WORDS = ("up", "breakout", "bullish", "beats", "upgrade")
    TRENDRADAR_BEAR_WORDS = ("down", "bearish", "miss", "downgrade", "selloff")
    TRENDRADAR_MIN_SCORE = 2

    # External signal placeholders
    XUEQIU_SIGNAL_PATH = REPO_ROOT / "xueqiu_crapper" / "latest_signal.json"
    X_SCRAPER_SIGNAL_PATH = REPO_ROOT / "x_crapper" / "latest_signal.json"
    HEDGE_FUND_SIGNAL_PATH = REPO_ROOT / "ai-hedge-fund" / "signals.json"
    AI_HEADHUNTER_DATA_PATH = REPO_ROOT / "ai_headhunter" / "sample_candidates.json"

    # Combination weights
    WEIGHT_BASE = 1.0
    WEIGHT_COIN = 0.3
    WEIGHT_SPREAD = 0.2
    WEIGHT_QIQUAN = 0.2
    WEIGHT_SMC = 0.3
    WEIGHT_TRENDRADAR = 0.2
    WEIGHT_XUEQIU = 0.1
    WEIGHT_X_SCRAPER = 0.1
    WEIGHT_AI_HEDGE_FUND = 0.2
    WEIGHT_AI_HEADHUNTER = 0.0

    COMBINE_THRESHOLD = 0.25

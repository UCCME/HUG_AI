"""
Runner for the modular ultimate strategy.
"""
from __future__ import annotations

from datetime import datetime

from ultimate_wealth.ultimate_modular.combined_strategy import CombinedStrategy
from ultimate_wealth.ultimate_modular.utils import ensure_repo_on_path


def validate_config(config) -> bool:
    try:
        start_date = datetime.strptime(config.START_DATE, "%Y-%m-%d")
        end_date = datetime.strptime(config.END_DATE, "%Y-%m-%d")
        if start_date >= end_date:
            print("Invalid date range: START_DATE must be earlier than END_DATE")
            return False
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD")
        return False

    if config.INITIAL_CAPITAL <= 0:
        print("INITIAL_CAPITAL must be positive")
        return False
    if config.POSITION_SIZE <= 0 or config.POSITION_SIZE > 1:
        print("POSITION_SIZE must be in (0, 1]")
        return False
    if config.FAST_MA_PERIOD >= config.SLOW_MA_PERIOD:
        print("FAST_MA_PERIOD must be smaller than SLOW_MA_PERIOD")
        return False
    if config.RSI_OVERSOLD >= config.RSI_OVERBOUGHT:
        print("RSI_OVERSOLD must be smaller than RSI_OVERBOUGHT")
        return False
    return True


def run_modular_strategy(config) -> bool:
    ensure_repo_on_path()
    from ai_trapper.data_handler import DataHandler
    from ai_trapper.backtest_engine import BacktestEngine
    from ai_trapper.performance_analyzer import PerformanceAnalyzer

    if not validate_config(config):
        return False

    enabled = []
    if config.ENABLE_AI_TRAPPER_BASE:
        enabled.append("ai_trapper")
    if config.ENABLE_COIN_STRATEGY:
        enabled.append("coin_strategy")
    if config.ENABLE_SPREAD_STRATEGY:
        enabled.append("spread_strategy")
    if config.ENABLE_QIQUAN_STRATEGY:
        enabled.append("qiquan_bisai")
    if config.ENABLE_SMC_STRATEGY:
        enabled.append("jinshJ_index")
    if config.ENABLE_TRENDRADAR:
        enabled.append("TrendRadar")
    if config.ENABLE_XUEQIU:
        enabled.append("xueqiu_crapper")
    if config.ENABLE_X_SCRAPER:
        enabled.append("x_crapper")
    if config.ENABLE_AI_HEDGE_FUND:
        enabled.append("ai-hedge-fund")
    if getattr(config, "ENABLE_AI_HEADHUNTER", False):
        enabled.append("ai_headhunter")

    if enabled:
        print("Enabled modules: " + ", ".join(enabled))

    data_handler = DataHandler(
        symbol=config.SYMBOL,
        fallback_symbol=config.FALLBACK_SYMBOL,
        local_data_path=str(config.LOCAL_DATA_PATH),
        use_local_on_fail=config.USE_LOCAL_ON_FAIL,
        retry_backoff_base=config.RETRY_BACKOFF_BASE,
        data_provider=config.DATA_PROVIDER,
        ak_symbol=config.AK_SYMBOL,
    )

    data = data_handler.prepare_data(
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        max_retries=config.MAX_FETCH_RETRIES,
    )

    if data.empty:
        print("No data returned for the selected range.")
        return False

    strategy = CombinedStrategy(config)
    backtest_engine = BacktestEngine(config)
    result = backtest_engine.run_backtest(data, strategy)
    analyzer = PerformanceAnalyzer(result)
    analyzer.print_performance_summary()
    return True

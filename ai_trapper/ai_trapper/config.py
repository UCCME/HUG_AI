"""
黄金合约策略配置文件
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    # 数据源配置
    DATA_PROVIDER = "local"            # 可选: "local", "akshare", "yfinance"
    SYMBOL = "GC=F"                    # 策略标的标识（逻辑用）
    AK_SYMBOL = "AU0"                  # AkShare 使用的合约代码（示例：AU0 主力连续）
    FALLBACK_SYMBOL = "GLD"            # yfinance 备用代码，主代码被限速时使用
    LOCAL_DATA_PATH = os.path.join(BASE_DIR, "..", "XAU_5m_data.csv")   # 本地5分钟CSV路径
    USE_LOCAL_ON_FAIL = True           # 下载失败时是否尝试本地文件
    MAX_FETCH_RETRIES = 6              # 主数据下载最大重试次数（增加重试次数）
    RETRY_BACKOFF_BASE = 2             # 指数退避基数（秒）
    
    # 数据区间
    START_DATE = "2016-01-01"
    END_DATE = "2024-12-12"
    
    # 策略参数
    FAST_MA_PERIOD = 72   # 约6小时窗口（5m数据）
    SLOW_MA_PERIOD = 216  # 约18小时窗口（5m数据）
    RSI_PERIOD = 14       # RSI周期
    RSI_OVERSOLD = 30     # RSI超卖阈值
    RSI_OVERBOUGHT = 70   # RSI超买阈值
    
    # MACD参数
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # 回测参数
    INITIAL_CAPITAL = 100000.0  # 初始资金
    COMMISSION_RATE = 0.002     # 手续费率 0.2%
    SLIPPAGE = 0.001            # 滑点 0.1%
    POSITION_SIZE = 0.95        # 仓位大小 (95%的资金参与交易)
    
    # 风控参数
    MAX_DRAWDOWN = 0.20         # 最大回撤限制 20%
    STOP_LOSS_PCT = 0.05        # 止损百分比 5%
    TAKE_PROFIT_PCT = 0.10      # 止盈百分比 10%

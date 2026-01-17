"""
究极策略配置文件
整合了所有策略模块的最佳参数
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class UltimateConfig:
    """究极策略配置类"""
    
    # ==================== 基础配置 ====================
    INITIAL_CAPITAL: float = 100000.0
    COMMISSION_RATE: float = 0.002  # 手续费率 0.2%
    SLIPPAGE: float = 0.001  # 滑点 0.1%
    
    # ==================== 数据源配置 ====================
    DATA_PROVIDER: str = "local"  # local / akshare / yfinance
    SYMBOL: str = "GC=F"  # 黄金期货代码
    LOCAL_DATA_PATH: str = "../XAU_5m_data.csv"
    
    # ==================== 技术指标参数 ====================
    # 移动平均线（来自黄金策略）
    FAST_MA_PERIOD: int = 72  # 快线周期
    SLOW_MA_PERIOD: int = 216  # 慢线周期
    
    # RSI
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 30
    RSI_OVERBOUGHT: float = 70
    
    # MACD
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    
    # 布林带
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    
    # ATR
    ATR_PERIOD: int = 14
    
    # StochRSI（来自StochRSI策略）
    STOCH_RSI_PERIOD: int = 14
    STOCH_K_PERIOD: int = 3
    STOCH_D_PERIOD: int = 3
    STOCH_OVERSOLD: float = 20
    STOCH_OVERBOUGHT: float = 80
    
    # UT Bot（来自Lucy策略）
    UT_ATR_PERIOD: int = 10
    UT_KEY_VALUE: float = 1.2
    
    # SMC参数（来自SMC工具）
    SMC_SWING_WINDOW: int = 3  # 摆动点检测窗口
    SMC_OB_LOOKBACK: int = 10  # 订单块回溯周期
    
    # ==================== 信号权重配置 ====================
    # 基础技术指标权重（来自黄金策略）
    WEIGHT_MA: float = 0.25
    WEIGHT_MACD: float = 0.20
    WEIGHT_RSI: float = 0.15
    WEIGHT_BB: float = 0.10
    WEIGHT_VOLUME: float = 0.05
    
    # 高级指标权重
    WEIGHT_STOCH_RSI: float = 0.10  # StochRSI权重
    WEIGHT_UT_BOT: float = 0.10  # UT Bot趋势权重
    WEIGHT_SMC: float = 0.05  # SMC结构权重
    
    # 信号阈值
    SIGNAL_THRESHOLD: float = 0.18  # 综合信号触发阈值
    MIN_SIGNAL_SCORE: int = 2  # 最小信号得分（来自加密货币策略）
    
    # ==================== 仓位管理配置 ====================
    # 基础仓位（来自黄金策略）
    POSITION_SIZE: float = 0.95  # 默认仓位 95%
    MAX_POSITION_PCT: float = 0.10  # 单笔最大仓位 10%（来自加密货币策略）
    
    # 动态仓位调整（来自期权策略的30/70法则）
    ROLL_ATTACK_RATIO: float = 0.30  # 移仓时30%进攻
    ROLL_DEFENSE_RATIO: float = 0.70  # 70%防守
    ROLL_TRIGGER_PCT: float = 0.08  # 移仓触发阈值8%
    
    # 风险控制
    RISK_PER_TRADE: float = 0.01  # 单笔风险1%
    
    # ==================== 止损止盈配置 ====================
    # 固定止损止盈
    STOP_LOSS_PCT: float = 0.05  # 止损 5%
    TAKE_PROFIT_PCT: float = 0.10  # 止盈 10%
    
    # ATR动态止损
    ATR_STOP_MULTIPLIER: float = 2.0  # ATR止损倍数
    ATR_TAKE_PROFIT_MULTIPLIER: float = 3.0  # ATR止盈倍数
    
    # 移动止损（来自Lucy策略）
    TRAILING_STOP_ENABLED: bool = True
    TRAILING_STOP_ACTIVATION: float = 0.03  # 3%盈利后启动移动止损
    TRAILING_STOP_DISTANCE: float = 0.02  # 移动止损距离2%
    
    # 时间止损（来自期权策略）
    TIME_STOP_DAYS: int = 7  # 7天未启动离场
    
    # ==================== 风险控制配置 ====================
    MAX_DRAWDOWN: float = 0.20  # 最大回撤限制 20%
    MAX_DAILY_LOSS: float = 0.05  # 单日最大亏损 5%
    MAX_CONSECUTIVE_LOSSES: int = 3  # 最大连续亏损次数
    
    # 冷却期（来自加密货币策略）
    COOLDOWN_DAYS: int = 1  # 亏损后冷却期
    
    # ==================== 市场状态识别 ====================
    # 波动率阈值（用于动态调整策略）
    HIGH_VOLATILITY_THRESHOLD: float = 0.03  # 高波动率阈值
    LOW_VOLATILITY_THRESHOLD: float = 0.01  # 低波动率阈值
    
    # 趋势强度阈值
    STRONG_TREND_THRESHOLD: float = 0.02  # 强趋势阈值
    
    # ==================== 回测配置 ====================
    START_DATE: Optional[str] = None
    END_DATE: Optional[str] = None
    
    # ==================== 输出配置 ====================
    LOG_TRADES: bool = True
    TRADES_LOG_PATH: str = "0117_ultimate/trades_log.txt"
    PLOT_RESULTS: bool = True
    SAVE_RESULTS: bool = True
    RESULTS_PATH: str = "0117_ultimate/backtest_results.json"


# 创建全局配置实例
config = UltimateConfig()

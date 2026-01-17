"""
Luxy Momentum策略配置文件
基于Pine Script的Luxy Momentum V7策略核心思想
- UT Bot动态追踪止损
- R-multiple固定盈亏比止盈
- ATR自适应风险管理
- 精简高效过滤器
"""

class LuxyConfig:
    """Luxy策略配置"""
    
    # ==================== 数据配置 ====================
    DATA_FILE = 'XAU_5m_data.csv'  # 5分钟黄金数据
    START_DATE = '2016-01-01'
    END_DATE = '2025-12-31'
    
    # ==================== 资金管理 ====================
    INITIAL_CAPITAL = 100000  # 初始资金
    POSITION_SIZE = 0.15  # 单次交易使用15%资金
    COMMISSION_RATE = 0.0002  # 手续费率0.02%
    
    # ==================== UT Bot追踪止损 ====================
    UT_KEY_VALUE = 2.0  # UT Bot基础倍数（类似ATR倍数）
    UT_ATR_PERIOD = 10  # UT Bot的ATR周期
    UT_SMOOTHING = 0.3  # 追踪止损平滑系数
    UT_VOLUME_THRESHOLD = 0.8  # 成交量过滤阈值（volRatio需要≥0.8）
    
    # ==================== R-multiple止盈系统 ====================
    # 固定盈亏比止盈（基于初始风险R）
    ENABLE_R_MULTIPLE = True  # 启用R-multiple止盈
    TP1_R_MULTIPLE = 1.5  # 第一止盈：1.5R（1:1.5盈亏比）
    TP2_R_MULTIPLE = 2.0  # 第二止盈：2R（1:2盈亏比）
    TP3_R_MULTIPLE = 3.0  # 第三止盈：3R（1:3盈亏比）
    
    # 分批止盈比例
    TP1_SIZE = 0.33  # 第一止盈平仓33%
    TP2_SIZE = 0.33  # 第二止盈平仓33%
    TP3_SIZE = 0.34  # 第三止盈平仓剩余34%
    
    # ==================== ATR动态止损 ====================
    ATR_PERIOD = 14  # ATR计算周期
    ATR_SL_MULTIPLIER = 2.0  # 止损=entry±2×ATR
    MIN_STOP_LOSS_PCT = 0.005  # 最小止损0.5%（防止止损过小）
    MAX_STOP_LOSS_PCT = 0.05  # 最大止损5%（防止止损过大）
    
    # ==================== SuperTrend ====================
    ST_ATR_PERIOD = 10  # SuperTrend ATR周期
    ST_MULTIPLIER = 3.0  # SuperTrend倍数
    
    # SuperTrend自适应参数（类似Luxy的adaptiveMult）
    ST_ADAPTIVE_MIN = 0.8  # 最小倍数系数
    ST_ADAPTIVE_MAX = 0.4  # 最大倍数系数（基于趋势强度调整）
    
    # ==================== ADX趋势过滤 ====================
    ADX_PERIOD = 14  # ADX计算周期
    ADX_SMOOTHING = 14  # ADX平滑周期
    MIN_ADX = 20  # 最小ADX值（过滤震荡市，Luxy使用≥20）
    
    # ==================== 成交量过滤 ====================
    VOLUME_MA_PERIOD = 20  # 成交量均线周期
    MIN_VOLUME_RATIO = 1.2  # 最小成交量比率（必须≥1.2才接受信号）
    
    # ==================== 移动平均线 ====================
    # ZLSMA参数（Zero-Lag SMA，Luxy使用）
    ZLSMA_PERIOD = 32
    
    # 传统MA（用于趋势确认）
    MA_FAST = 50
    MA_SLOW = 200
    
    # ==================== 信号过滤 ====================
    SIGNAL_THRESHOLD = 0.25  # 最小信号强度阈值
    
    # 是否启用各个过滤器
    ENABLE_VOLUME_FILTER = True  # 成交量过滤
    ENABLE_ADX_FILTER = True  # ADX趋势强度过滤
    ENABLE_MA_FILTER = True  # 均线过滤
    
    # ==================== 回测配置 ====================
    ENABLE_SHORT = False  # 是否允许做空（黄金长期上涨，建议只做多）
    TRAILING_STOP_ACTIVATION = 1.5  # 当盈利≥1.5R时激活追踪止损
    
    # ==================== 打印配置 ====================
    VERBOSE = False  # 是否打印详细信息（改为False，只保存到文件）
    PLOT_SIGNALS = True  # 是否绘制信号图
    SAVE_TRADES = True  # 是否保存交易详情
    
    @classmethod
    def get_config_summary(cls):
        """获取配置摘要"""
        summary = f"""
{'='*80}
Luxy Momentum Strategy Configuration
{'='*80}

Data Config:
  - Data File: {cls.DATA_FILE}
  - Period: {cls.START_DATE} to {cls.END_DATE}
  - Initial Capital: ${cls.INITIAL_CAPITAL:,}

Risk Management:
  - Position Size: {cls.POSITION_SIZE*100}% per trade
  - Commission: {cls.COMMISSION_RATE*100}%
  - ATR Stop Loss: {cls.ATR_SL_MULTIPLIER}×ATR
  - Min/Max SL: {cls.MIN_STOP_LOSS_PCT*100}% / {cls.MAX_STOP_LOSS_PCT*100}%

R-Multiple Take Profit:
  - TP1: {cls.TP1_R_MULTIPLE}R ({cls.TP1_SIZE*100:.0f}% position)
  - TP2: {cls.TP2_R_MULTIPLE}R ({cls.TP2_SIZE*100:.0f}% position)
  - TP3: {cls.TP3_R_MULTIPLE}R ({cls.TP3_SIZE*100:.0f}% position)

UT Bot Tracking:
  - Key Value: {cls.UT_KEY_VALUE}
  - ATR Period: {cls.UT_ATR_PERIOD}
  - Volume Threshold: {cls.UT_VOLUME_THRESHOLD}

Filters:
  - ADX: {'Enabled' if cls.ENABLE_ADX_FILTER else 'Disabled'} (min: {cls.MIN_ADX})
  - Volume: {'Enabled' if cls.ENABLE_VOLUME_FILTER else 'Disabled'} (min ratio: {cls.MIN_VOLUME_RATIO})
  - MA: {'Enabled' if cls.ENABLE_MA_FILTER else 'Disabled'} ({cls.MA_FAST}/{cls.MA_SLOW})

Trading:
  - Short Selling: {'Enabled' if cls.ENABLE_SHORT else 'Disabled'}
  - Signal Threshold: {cls.SIGNAL_THRESHOLD}

{'='*80}
"""
        return summary
    
    @classmethod
    def print_config(cls):
        """打印配置"""
        print(cls.get_config_summary())


if __name__ == '__main__':
    # 打印配置
    LuxyConfig.print_config()

"""
满仓大佬策略配置文件
包含所有核心参数和风控设置
"""

from typing import Dict, Any


class StrategyConfig:
    """策略配置类"""
    
    # ==================== 核心均线参数 ====================
    MA_STOP_LOSS = 5  # 核心止损线，5日均线
    MA_MID_TERM = 7   # 中线止损/趋势辅助线，7日均线
    
    # ==================== 仓位管理参数 ====================
    MAX_TOTAL_POS = 0.50        # 最大总仓位上限 50%
    MAX_TOTAL_POS_HIGH_RISK = 0.30  # 高风险期降至 30%
    SINGLE_POS_LIMIT = 0.10     # 单只股票最大仓位 10%（分仓5只）
    MAX_POSITIONS = 5           # 最大持仓数量
    
    # ==================== 交易限制参数 ====================
    CHASE_LIMIT = 3             # 连板高度限制，超过3板不追高
    MIN_MARKET_CAP = 20         # 最小市值（亿元）
    MAX_MARKET_CAP = 500        # 最大市值（亿元）
    MIN_TURNOVER_RATE = 5.0     # 最小换手率 %
    
    # ==================== IPO 新股参数 ====================
    IPO_ENTRY_DAY = 6           # 新股上市第6天反包时介入
    IPO_MIN_DECLINE_DAYS = 3    # IPO 至少下跌天数
    
    # ==================== 买入信号参数 ====================
    # 龙头回调低吸
    PULLBACK_MA5_TOLERANCE = 0.02   # 5日线附近容忍度 2%
    PULLBACK_MIN_UPTREND_DAYS = 3   # 最少上升趋势天数
    
    # 题材轮动
    SECTOR_MIN_LIMIT_UP = 2     # 板块内最少涨停股数量
    SECTOR_MIN_STOCKS = 3       # 板块内最少股票数量
    
    # 半路追涨
    CHASE_MIN_GAIN = 0.05       # 最小涨幅 5%
    CHASE_MAX_GAIN = 0.09       # 最大涨幅 9%
    CHASE_VOLUME_RATIO = 2.0    # 量比要求
    
    # ==================== 卖出信号参数 ====================
    # 止盈参数
    TAKE_PROFIT_SURGE = 0.08    # 冲高涨幅阈值 8%
    TAKE_PROFIT_PULLBACK = 0.02 # 回落幅度阈值 2%
    TAKE_PROFIT_RATIO = 0.50    # 止盈卖出比例 50%
    
    # 止损参数
    STOP_LOSS_STRICT = True     # 是否严格执行5日线止损
    STOP_LOSS_MID_TERM = False  # 是否使用7日线作为中线止损
    
    # ==================== 市场情绪参数 ====================
    MIN_MARKET_SENTIMENT = 40   # 最低市场情绪分数（0-100）
    LIMIT_UP_THRESHOLD = 30     # 涨停家数阈值
    
    # ==================== 定时任务时间 ====================
    SCHEDULE_US_MARKET_CHECK = "06:00"      # 美股数据检查
    SCHEDULE_MARKET_OPEN = "09:30"          # 开盘时间
    SCHEDULE_MARKET_CLOSE = "15:00"         # 收盘时间
    SCHEDULE_AFTER_MARKET = "15:30"         # 盘后复盘
    SCHEDULE_MONITOR_INTERVAL = 3600        # 监控间隔（秒）
    
    # ==================== 数据源配置 ====================
    DATA_SOURCE = 'akshare'     # 数据源：'akshare', 'tushare', 'custom'
    TUSHARE_TOKEN = None        # Tushare token（如使用）
    
    # ==================== 回测参数 ====================
    INITIAL_CAPITAL = 1000000   # 初始资金 100万
    COMMISSION = 0.0003         # 手续费率 0.03%
    SLIPPAGE = 0.001            # 滑点 0.1%
    
    # ==================== 风险控制参数 ====================
    MAX_DAILY_LOSS = 0.02       # 单日最大亏损 2%
    MAX_SINGLE_LOSS = 0.01      # 单笔最大亏损 1%
    STOP_TRADING_LOSS = 0.10    # 累计亏损停止交易阈值 10%
    
    # ==================== 龙头识别参数 ====================
    DRAGON_MIN_LIMIT_UP_DAYS = 2    # 龙头最少涨停天数
    DRAGON_VOLUME_RANK = 10         # 成交量排名前N
    DRAGON_MONEY_FLOW_RANK = 10     # 资金流入排名前N
    
    @classmethod
    def get_config(cls, mode: str = 'backtest') -> Dict[str, Any]:
        """
        获取配置字典
        
        Args:
            mode: 运行模式 'backtest' 或 'live'
            
        Returns:
            配置字典
        """
        config = {
            # 均线参数
            'ma_stop_loss': cls.MA_STOP_LOSS,
            'ma_mid_term': cls.MA_MID_TERM,
            
            # 仓位管理
            'max_total_pos': cls.MAX_TOTAL_POS,
            'max_total_pos_high_risk': cls.MAX_TOTAL_POS_HIGH_RISK,
            'single_pos_limit': cls.SINGLE_POS_LIMIT,
            'max_positions': cls.MAX_POSITIONS,
            
            # 交易限制
            'chase_limit': cls.CHASE_LIMIT,
            'min_market_cap': cls.MIN_MARKET_CAP,
            'max_market_cap': cls.MAX_MARKET_CAP,
            'min_turnover_rate': cls.MIN_TURNOVER_RATE,
            
            # IPO参数
            'ipo_entry_day': cls.IPO_ENTRY_DAY,
            'ipo_min_decline_days': cls.IPO_MIN_DECLINE_DAYS,
            
            # 买入信号
            'pullback_ma5_tolerance': cls.PULLBACK_MA5_TOLERANCE,
            'pullback_min_uptrend_days': cls.PULLBACK_MIN_UPTREND_DAYS,
            'sector_min_limit_up': cls.SECTOR_MIN_LIMIT_UP,
            'sector_min_stocks': cls.SECTOR_MIN_STOCKS,
            'chase_min_gain': cls.CHASE_MIN_GAIN,
            'chase_max_gain': cls.CHASE_MAX_GAIN,
            'chase_volume_ratio': cls.CHASE_VOLUME_RATIO,
            
            # 卖出信号
            'take_profit_surge': cls.TAKE_PROFIT_SURGE,
            'take_profit_pullback': cls.TAKE_PROFIT_PULLBACK,
            'take_profit_ratio': cls.TAKE_PROFIT_RATIO,
            'stop_loss_strict': cls.STOP_LOSS_STRICT,
            'stop_loss_mid_term': cls.STOP_LOSS_MID_TERM,
            
            # 市场情绪
            'min_market_sentiment': cls.MIN_MARKET_SENTIMENT,
            'limit_up_threshold': cls.LIMIT_UP_THRESHOLD,
            
            # 数据源
            'data_source': cls.DATA_SOURCE,
            'tushare_token': cls.TUSHARE_TOKEN,
            
            # 回测参数
            'initial_capital': cls.INITIAL_CAPITAL,
            'commission': cls.COMMISSION,
            'slippage': cls.SLIPPAGE,
            
            # 风险控制
            'max_daily_loss': cls.MAX_DAILY_LOSS,
            'max_single_loss': cls.MAX_SINGLE_LOSS,
            'stop_trading_loss': cls.STOP_TRADING_LOSS,
            
            # 龙头识别
            'dragon_min_limit_up_days': cls.DRAGON_MIN_LIMIT_UP_DAYS,
            'dragon_volume_rank': cls.DRAGON_VOLUME_RANK,
            'dragon_money_flow_rank': cls.DRAGON_MONEY_FLOW_RANK,
            
            # 运行模式
            'mode': mode,
        }
        
        return config
    
    @classmethod
    def update_config(cls, **kwargs):
        """
        更新配置参数
        
        Args:
            **kwargs: 要更新的参数
        """
        for key, value in kwargs.items():
            if hasattr(cls, key.upper()):
                setattr(cls, key.upper(), value)
    
    @classmethod
    def get_high_risk_config(cls) -> Dict[str, Any]:
        """
        获取高风险期配置（降低仓位）
        
        Returns:
            高风险配置字典
        """
        config = cls.get_config()
        config['max_total_pos'] = cls.MAX_TOTAL_POS_HIGH_RISK
        return config

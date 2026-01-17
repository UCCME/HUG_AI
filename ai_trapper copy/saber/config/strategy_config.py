"""
Saber 策略配置文件
包含市场状态过滤器、子策略选择、风控参数等
"""

from typing import Dict, Any


class StrategyConfig:
    """策略配置类"""
    
    # ==================== 市场状态过滤器参数 ====================
    # 技术趋势
    MA_PERIODS = [10, 20, 30, 60]  # 均线周期
    BOLLINGER_PERIOD = 20          # 布林带周期
    BOLLINGER_STD = 2              # 布林带标准差
    
    # 情绪指标
    FEAR_GREED_MIN = 40            # 恐慌贪婪指数最小值
    FEAR_GREED_MAX = 75            # 恐慌贪婪指数最大值
    
    # 波动率状态
    IV_LOW_PERCENTILE = 30         # IV低位分位数（触发模式A）
    IV_HIGH_PERCENTILE = 60        # IV高位分位数（触发模式B）
    IV_LOOKBACK_DAYS = 90          # IV历史回溯天数
    
    # 流动性
    VOLUME_MA_PERIOD = 20          # 成交量均线周期
    VOLUME_SURGE_THRESHOLD = 2.0   # 放量阈值（倍数）
    
    # ==================== 期权选择参数 ====================
    # 模式A：牛市认购价差 (Bull Call Spread)
    CALL_SPREAD_LONG_MONEYNESS = 0.00   # 买入Call的价值度（0=ATM）
    CALL_SPREAD_SHORT_MONEYNESS = 0.05  # 卖出Call的价值度（5%虚值）
    CALL_SPREAD_DTE_MIN = 14            # 最小到期天数
    CALL_SPREAD_DTE_MAX = 45            # 最大到期天数
    
    # 模式B：牛市认沽价差 (Bull Put Spread)
    PUT_SPREAD_SHORT_MONEYNESS = -0.03  # 卖出Put的价值度（3%虚值）
    PUT_SPREAD_LONG_MONEYNESS = -0.08   # 买入Put的价值度（8%虚值）
    PUT_SPREAD_DTE_MIN = 14             # 最小到期天数
    PUT_SPREAD_DTE_MAX = 45             # 最大到期天数
    
    # ==================== 仓位管理参数 ====================
    SINGLE_POSITION_LIMIT = 0.05        # 单策略最大仓位 5%
    TOTAL_POSITION_LIMIT = 0.10         # 总仓位限制 10%
    MAX_POSITIONS = 5                   # 最大持仓数量
    
    # ==================== 止盈止损参数 ====================
    # 止盈
    TAKE_PROFIT_RATIO = 0.75            # 达到最大利润的75%时止盈
    RESISTANCE_TAKE_PROFIT = True       # 触及阻力位时止盈
    
    # 止损
    STOP_LOSS_SUPPORT_BREAK = True      # 跌破支撑位止损
    STOP_LOSS_MAX_LOSS = 0.50           # 最大亏损50%权利金
    STOP_LOSS_DTE_THRESHOLD = 7         # 到期前N天强制平仓
    
    # IV逻辑背离止损
    CALL_SPREAD_IV_DROP_THRESHOLD = -0.10   # Call Spread时IV下跌10%止损
    PUT_SPREAD_IV_RISE_THRESHOLD = 0.10     # Put Spread时IV上涨10%止损
    
    # ==================== 尾部风险对冲 ====================
    TAIL_HEDGE_RATIO = 0.10             # 用利润的10%买入保护性Put
    TAIL_HEDGE_MONEYNESS = -0.20        # 保护性Put的价值度（20%虚值）
    TAIL_HEDGE_DTE = 90                 # 保护性Put的到期天数
    
    # ==================== 数据源配置 ====================
    PRICE_DATA_SOURCE = 'binance'       # 价格数据源
    OPTIONS_DATA_SOURCE = 'deribit'     # 期权数据源
    FEAR_GREED_API = 'alternative.me'   # 恐慌贪婪指数API
    
    # ==================== 回测参数 ====================
    INITIAL_CAPITAL = 100000            # 初始资金（USDT）
    COMMISSION_RATE = 0.0003            # 手续费率 0.03%
    SLIPPAGE = 0.001                    # 滑点 0.1%
    
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
            # 市场过滤器
            'ma_periods': cls.MA_PERIODS,
            'bollinger_period': cls.BOLLINGER_PERIOD,
            'bollinger_std': cls.BOLLINGER_STD,
            'fear_greed_min': cls.FEAR_GREED_MIN,
            'fear_greed_max': cls.FEAR_GREED_MAX,
            'iv_low_percentile': cls.IV_LOW_PERCENTILE,
            'iv_high_percentile': cls.IV_HIGH_PERCENTILE,
            'iv_lookback_days': cls.IV_LOOKBACK_DAYS,
            'volume_ma_period': cls.VOLUME_MA_PERIOD,
            'volume_surge_threshold': cls.VOLUME_SURGE_THRESHOLD,
            
            # 期权选择
            'call_spread_long_moneyness': cls.CALL_SPREAD_LONG_MONEYNESS,
            'call_spread_short_moneyness': cls.CALL_SPREAD_SHORT_MONEYNESS,
            'call_spread_dte_min': cls.CALL_SPREAD_DTE_MIN,
            'call_spread_dte_max': cls.CALL_SPREAD_DTE_MAX,
            'put_spread_short_moneyness': cls.PUT_SPREAD_SHORT_MONEYNESS,
            'put_spread_long_moneyness': cls.PUT_SPREAD_LONG_MONEYNESS,
            'put_spread_dte_min': cls.PUT_SPREAD_DTE_MIN,
            'put_spread_dte_max': cls.PUT_SPREAD_DTE_MAX,
            
            # 仓位管理
            'single_position_limit': cls.SINGLE_POSITION_LIMIT,
            'total_position_limit': cls.TOTAL_POSITION_LIMIT,
            'max_positions': cls.MAX_POSITIONS,
            
            # 止盈止损
            'take_profit_ratio': cls.TAKE_PROFIT_RATIO,
            'resistance_take_profit': cls.RESISTANCE_TAKE_PROFIT,
            'stop_loss_support_break': cls.STOP_LOSS_SUPPORT_BREAK,
            'stop_loss_max_loss': cls.STOP_LOSS_MAX_LOSS,
            'stop_loss_dte_threshold': cls.STOP_LOSS_DTE_THRESHOLD,
            'call_spread_iv_drop_threshold': cls.CALL_SPREAD_IV_DROP_THRESHOLD,
            'put_spread_iv_rise_threshold': cls.PUT_SPREAD_IV_RISE_THRESHOLD,
            
            # 尾部对冲
            'tail_hedge_ratio': cls.TAIL_HEDGE_RATIO,
            'tail_hedge_moneyness': cls.TAIL_HEDGE_MONEYNESS,
            'tail_hedge_dte': cls.TAIL_HEDGE_DTE,
            
            # 数据源
            'price_data_source': cls.PRICE_DATA_SOURCE,
            'options_data_source': cls.OPTIONS_DATA_SOURCE,
            'fear_greed_api': cls.FEAR_GREED_API,
            
            # 回测
            'initial_capital': cls.INITIAL_CAPITAL,
            'commission_rate': cls.COMMISSION_RATE,
            'slippage': cls.SLIPPAGE,
            
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

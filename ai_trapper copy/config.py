"""
黄金合约策略配置文件
"""

import logging

logger = logging.getLogger(__name__)


class Config:
    # 数据配置
    SYMBOL = "GC=F"  # 黄金期货合约符号
    START_DATE = "2016-01-01"  # 从2016年开始
    END_DATE = "2024-12-31"
    
    # 策略参数（平衡优化 - 质量与频率平衡）
    FAST_MA_PERIOD = 25  # 快速移动平均线周期（平衡：减少噪音但不过长）
    SLOW_MA_PERIOD = 80  # 慢速移动平均线周期（平衡：捕捉趋势但不过长）
    RSI_PERIOD = 14      # RSI周期
    RSI_OVERSOLD = 35    # RSI超卖阈值（平衡：较极端但可交易）
    RSI_OVERBOUGHT = 65  # RSI超买阈值（平衡：较极端但可交易）
    
    # MACD参数
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # 回测参数（平衡优化 - 保守但可交易）
    INITIAL_CAPITAL = 100000.0  # 初始资金
    COMMISSION_RATE = 0.002     # 手续费率 0.2%
    SLIPPAGE = 0.001           # 滑点 0.1%
    POSITION_SIZE = 0.15       # 仓位大小 (15%的资金，平衡风险与收益)
    
    # 风控参数（平衡优化 - 严格但可交易）
    MAX_DRAWDOWN = 0.15        # 最大回撤限制 15%（更严格）
    STOP_LOSS_PCT = 0.02       # 止损百分比 2%（更快止损）
    TAKE_PROFIT_PCT = 0.08     # 止盈百分比 8%（提高盈亏比到4:1）
    
    # 新增：ATR相关参数（与优化后的策略兼容）
    ATR_STOP_MULTIPLIER = 2.0   # ATR止损倍数（收紧止损）
    ATR_PROFIT_MULTIPLIER = 6.0  # ATR止盈倍数（扩大止盈）
    MAX_POSITION_SIZE = 0.15     # 最大仓位限制（大幅降低）
    RISK_PER_TRADE = 0.005       # 每笔交易风险比例（降低到0.5%）
    SIGNAL_THRESHOLD = 0.25      # 信号阈值（平衡：既保证质量又能产生交易）
    
    # 信号权重（深度优化 - 强调趋势跟踪）
    WEIGHTS = {
        'ma': 0.45,      # MA权重大幅提高（趋势是核心）
        'macd': 0.35,    # MACD权重提高（确认趋势）
        'rsi': 0.10,     # RSI权重降低（仅作辅助）
        'bb': 0.10,      # 布林带降低
        'volume': 0.00   # 成交量去掉（黄金市场成交量参考价值有限）
    }
    
    def validate(self):
        """验证配置参数的有效性"""
        try:
            assert self.FAST_MA_PERIOD < self.SLOW_MA_PERIOD, "快线周期必须小于慢线周期"
            assert 0 < self.RSI_OVERSOLD < self.RSI_OVERBOUGHT < 100, "RSI参数无效"
            assert 0 < self.POSITION_SIZE <= 1, "仓位比例必须在0-1之间"
            assert sum(self.WEIGHTS.values()) <= 1.01, "权重总和不能超过1"
            logger.info("策略配置验证通过")
        except AssertionError as e:
            logger.error(f"配置验证失败: {e}")
            raise

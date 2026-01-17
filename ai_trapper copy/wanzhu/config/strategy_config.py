"""
策略配置文件
提供策略的各项参数配置
"""

from typing import Dict, Any


class StrategyConfig:
    """策略配置类"""
    
    # ==================== 基础配置 ====================
    INITIAL_CAPITAL = 1000000  # 初始资金100万
    DATA_SOURCE = 'local'       # 数据源：local/tushare/akshare
    STRATEGY_MODE = 'half_position'  # 策略模式：half_position（半仓滚动）
    MAX_POSITIONS = 1           # 最大持仓数：每天只买一只股票
    ENABLE_MARGIN = False       # 是否启用融资
    
    # ==================== 选股配置 ====================
    SELECTOR_CONFIG = {
        # 市值筛选
        'min_market_cap': 20e8,          # 最小市值20亿
        'max_market_cap': 500e8,         # 最大市值500亿（中小市值）
        
        # 换手率筛选
        'min_turnover': 5.0,             # 最小换手率5%
        
        # 连板限制
        'max_continuous_limit': 3,        # 最大连板数3板（不做高连板）
        
        # 资金流向
        'money_flow_top_n': 10,          # 主力资金流入前10名
        
        # 板块效应
        'sector_min_stocks': 3,           # 板块最少股票数
        'sector_min_limit_up': 2,         # 板块最少涨停数
    }
    
    # ==================== 信号配置 ====================
    SIGNAL_CONFIG = {
        # 涨停板相关
        'limit_up_threshold': 9.9,             # 涨停阈值9.9%
        'early_limit_time': '10:00:00',        # 早盘快速板时间界限
        
        # 竞价相关
        'weak_to_strong_threshold': 0.0,       # 竞价弱转强阈值
        
        # 回封板相关
        'reseal_min_volume': 1.5,              # 回封板最小量比
        
        # 止损相关
        'stop_loss_pct': 0.01,                 # 止损比例1%（松松的核心纪律）
        
        # 技术指标
        'macd_divergence_window': 5,           # MACD背离检测窗口
        'macd_fast_period': 12,                # MACD快线周期
        'macd_slow_period': 26,                # MACD慢线周期
        'macd_signal_period': 9,               # MACD信号线周期
        
        # 均线周期
        'ma_periods': [5, 10, 20, 60],         # 均线周期
        
        # 获利目标（可选）
        # 'target_profit_pct': 0.10,           # 获利目标10%
    }
    
    # ==================== 风控配置 ====================
    RISK_CONFIG = {
        # 止损相关
        'max_single_loss_pct': 0.01,          # 单笔最大亏损1%（严格纪律）
        'stop_loss_time_limit': 30,           # 止损时间限制30秒（可转债时代）
        
        # 仓位管理
        'max_position_ratio': 0.5,            # 最大仓位50%（半仓滚动）
        'max_single_position': 0.5,           # 单个股票最大仓位50%
        'min_position_score': 60,             # 最低持仓评分
        
        # 交易频率控制
        'max_daily_trades': 1,                # 每天最多交易1只股票
        
        # 空仓策略
        'empty_position_days_limit': 5,       # 允许空仓天数
        'market_sentiment_threshold': 40,     # 市场情绪阈值（低于此值考虑空仓）
        'min_market_sentiment': 40,           # 最低市场情绪要求
    }
    
    # ==================== 回测配置 ====================
    BACKTEST_CONFIG = {
        'start_date': '2024-01-01',           # 回测开始日期
        'end_date': '2024-12-31',             # 回测结束日期
        'commission_rate': 0.0003,            # 手续费率0.03%
        'slippage_rate': 0.001,               # 滑点率0.1%
        'min_trade_amount': 10000,            # 最小交易金额
    }
    
    # ==================== 数据源配置 ====================
    DATA_CONFIG = {
        # Tushare配置
        'tushare': {
            'token': '',  # 需要用户自行填写Tushare token
            'timeout': 30,
        },
        
        # AKShare配置
        'akshare': {
            'timeout': 30,
        },
        
        # 本地数据配置
        'local': {
            'data_dir': 'wanzhu/data',
            'cache_enabled': True,
        }
    }
    
    # ==================== 日志配置 ====================
    LOG_CONFIG = {
        'level': 'INFO',                      # 日志级别
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': 'wanzhu/logs/strategy.log',   # 日志文件路径
        'console_output': True,               # 是否输出到控制台
    }
    
    @classmethod
    def get_config(cls, mode: str = 'production') -> Dict[str, Any]:
        """
        获取完整配置
        
        Args:
            mode: 配置模式 ('production', 'backtest', 'debug')
            
        Returns:
            配置字典
        """
        config = {
            'initial_capital': cls.INITIAL_CAPITAL,
            'data_source': cls.DATA_SOURCE,
            'strategy_mode': cls.STRATEGY_MODE,
            'max_positions': cls.MAX_POSITIONS,
            'enable_margin': cls.ENABLE_MARGIN,
            'selector': cls.SELECTOR_CONFIG,
            'signal': cls.SIGNAL_CONFIG,
            'risk': cls.RISK_CONFIG,
            'backtest': cls.BACKTEST_CONFIG,
            'data': cls.DATA_CONFIG,
            'log': cls.LOG_CONFIG,
        }
        
        # 根据模式调整配置
        if mode == 'debug':
            config['log']['level'] = 'DEBUG'
            config['log']['console_output'] = True
        elif mode == 'backtest':
            config['log']['level'] = 'INFO'
        
        return config
    
    @classmethod
    def load_from_file(cls, config_file: str) -> Dict[str, Any]:
        """
        从配置文件加载配置
        
        Args:
            config_file: 配置文件路径（支持JSON/YAML）
            
        Returns:
            配置字典
        """
        import json
        import os
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            if config_file.endswith('.json'):
                custom_config = json.load(f)
            elif config_file.endswith(('.yml', '.yaml')):
                try:
                    import yaml
                    custom_config = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("请安装PyYAML: pip install pyyaml")
            else:
                raise ValueError("不支持的配置文件格式，仅支持JSON和YAML")
        
        # 合并默认配置和自定义配置
        base_config = cls.get_config()
        base_config.update(custom_config)
        
        return base_config


# ==================== 预设配置模板 ====================

# 激进模式配置
AGGRESSIVE_CONFIG = {
    'risk': {
        'max_position_ratio': 0.8,        # 更高仓位
        'max_single_position': 0.8,
        'max_single_loss_pct': 0.015,     # 稍宽松的止损
        'min_position_score': 50,
    },
    'signal': {
        'target_profit_pct': 0.15,        # 更高获利目标
    }
}

# 保守模式配置
CONSERVATIVE_CONFIG = {
    'risk': {
        'max_position_ratio': 0.3,        # 更低仓位
        'max_single_position': 0.3,
        'max_single_loss_pct': 0.008,     # 更严格止损
        'min_position_score': 70,
        'market_sentiment_threshold': 50,  # 更高市场情绪要求
    },
    'signal': {
        'target_profit_pct': 0.08,        # 较低获利目标，快速止盈
    }
}

# 可转债高频模式配置（纪念松松的债神时代）
CONVERTIBLE_BOND_CONFIG = {
    'risk': {
        'max_position_ratio': 0.6,
        'max_daily_trades': 10,            # 高频交易
        'stop_loss_time_limit': 30,        # 30秒止损
    },
    'selector': {
        'max_continuous_limit': 10,        # 可转债无连板限制
    }
}

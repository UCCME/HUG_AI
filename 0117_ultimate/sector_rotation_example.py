"""
板块轮动策略使用示例
演示如何捕捉航空航天等强势板块趋势
"""
from pluggable_config import PluggableConfig, StrategyConfig
from strategy_factory import StrategyFactory
from strategies.sector_rotation_strategy import SectorRotationStrategy, SectorLeaderStrategy


def example_1_register_sector_strategies():
    """示例1：注册板块轮动策略"""
    print("\n" + "=" * 60)
    print("示例1：注册板块轮动策略")
    print("=" * 60)
    
    # 注册策略
    StrategyFactory.register('sector_rotation', SectorRotationStrategy)
    StrategyFactory.register('sector_leader', SectorLeaderStrategy)
    
    print("✅ 板块轮动策略已注册")
    print("✅ 板块龙头策略已注册")
    
    # 列出所有策略
    StrategyFactory.list_strategies()


def example_2_create_sector_rotation_config():
    """示例2：创建板块轮动配置"""
    print("\n" + "=" * 60)
    print("示例2：创建板块轮动配置")
    print("=" * 60)
    
    config = PluggableConfig()
    
    # 清空默认策略
    config.STRATEGIES = []
    
    # 添加板块轮动策略组合
    config.add_strategy(StrategyConfig(
        name='sector_rotation',
        weight=0.40,
        enabled=True,
        params={
            'lookback_period': 20,
            'strength_threshold': 0.05,
            'volume_threshold': 1.5,
            'momentum_period': 5
        }
    ))
    
    config.add_strategy(StrategyConfig(
        name='sector_leader',
        weight=0.30,
        enabled=True,
        params={
            'volume_rank_threshold': 3,
            'price_strength_threshold': 0.03
        }
    ))
    
    # 添加辅助策略
    config.add_strategy(StrategyConfig(
        name='ma',
        weight=0.15,
        enabled=True,
        params={'fast_period': 10, 'slow_period': 30}
    ))
    
    config.add_strategy(StrategyConfig(
        name='volume',
        weight=0.15,
        enabled=True,
        params={'volume_threshold': 1.5}
    ))
    
    # 调整风险参数
    config.STOP_LOSS_PCT = 0.08
    config.TAKE_PROFIT_PCT = 0.20
    config.TRAILING_STOP_ENABLED = True
    
    config.print_config()


def example_3_aerospace_sector_config():
    """示例3：航空航天板块专用配置"""
    print("\n" + "=" * 60)
    print("示例3：航空航天板块专用配置")
    print("=" * 60)
    
    config = PluggableConfig()
    
    # 航空航天板块特点：
    # 1. 政策驱动明显
    # 2. 资金集中度高
    # 3. 波动较大
    
    # 针对性配置
    config.STRATEGIES = []
    
    # 主策略：板块轮动（高权重）
    config.add_strategy(StrategyConfig(
        name='sector_rotation',
        weight=0.50,  # 50%权重
        enabled=True,
        params={
            'lookback_period': 15,  # 较短周期，快速响应
            'strength_threshold': 0.04,  # 4%阈值
            'volume_threshold': 2.0,  # 更高的成交量要求
            'momentum_period': 3  # 短期动量
        }
    ))
    
    # 辅助策略：龙头识别
    config.add_strategy(StrategyConfig(
        name='sector_leader',
        weight=0.30,
        enabled=True,
        params={
            'volume_rank_threshold': 2,  # 前2名
            'price_strength_threshold': 0.05  # 5%涨幅
        }
    ))
    
    # 趋势确认
    config.add_strategy(StrategyConfig(
        name='ma',
        weight=0.20,
        enabled=True,
        params={'fast_period': 5, 'slow_period': 20}
    ))
    
    # 风险控制参数
    config.STOP_LOSS_PCT = 0.10  # 10%止损（波动大）
    config.TAKE_PROFIT_PCT = 0.25  # 25%止盈
    config.TRAILING_STOP_ENABLED = True
    config.TRAILING_STOP_ACTIVATION = 0.05  # 5%后启动移动止损
    config.TRAILING_STOP_DISTANCE = 0.03  # 3%移动止损距离
    
    # 仓位管理
    config.POSITION_SIZE = 0.70  # 70%仓位
    config.MAX_POSITION_PCT = 0.20  # 单股最大20%
    
    print("航空航天板块配置:")
    config.print_config()
    
    print("\n配置特点:")
    print("  - 快速响应：15天回溯期")
    print("  - 高成交量要求：2倍放大")
    print("  - 严格风控：10%止损，25%止盈")
    print("  - 移动止损：保护利润")


def example_4_early_detection_config():
    """示例4：早期趋势捕捉配置"""
    print("\n" + "=" * 60)
    print("示例4：早期趋势捕捉配置")
    print("=" * 60)
    
    # 目标：在板块刚启动时就捕捉到
    config = PluggableConfig()
    config.STRATEGIES = []
    
    config.add_strategy(StrategyConfig(
        name='sector_rotation',
        weight=0.40,
        enabled=True,
        params={
            'lookback_period': 10,  # 更短回溯期
            'strength_threshold': 0.03,  # 更低阈值（3%）
            'volume_threshold': 1.3,  # 更低成交量要求
            'momentum_period': 3  # 短期动量
        }
    ))
    
    config.add_strategy(StrategyConfig(
        name='volume',
        weight=0.30,
        enabled=True,
        params={
            'volume_threshold': 1.3,
            'price_change_threshold': 0.02
        }
    ))
    
    config.add_strategy(StrategyConfig(
        name='macd',
        weight=0.30,
        enabled=True,
        params={'fast': 8, 'slow': 17, 'signal': 9}
    ))
    
    # 降低信号阈值，更容易触发
    config.SIGNAL_THRESHOLD = 0.15
    config.MIN_SIGNAL_COUNT = 2
    
    print("早期捕捉配置:")
    print("  - 10天回溯期（快速响应）")
    print("  - 3%强度阈值（更敏感）")
    print("  - 1.3倍成交量（降低门槛）")
    print("  - 信号阈值0.15（更容易触发）")
    print("\n⚠️  注意：更敏感意味着更多假信号，需要严格止损")


def example_5_risk_management():
    """示例5：板块轮动的风险管理"""
    print("\n" + "=" * 60)
    print("示例5：板块轮动的风险管理")
    print("=" * 60)
    
    print("板块轮动风险管理要点:")
    print("\n1. 止损策略:")
    print("   - 固定止损：8-10%")
    print("   - 移动止损：盈利5%后启动")
    print("   - 时间止损：持仓超过30天未盈利")
    
    print("\n2. 仓位管理:")
    print("   - 初始仓位：50-70%")
    print("   - 单股上限：15-20%")
    print("   - 分批建仓：避免一次性重仓")
    
    print("\n3. 止盈策略:")
    print("   - 目标止盈：20-30%")
    print("   - 分批止盈：达到15%后减半仓")
    print("   - 趋势止盈：跟随趋势，不设固定目标")
    
    print("\n4. 板块切换:")
    print("   - 相对强度转负：考虑换板块")
    print("   - 成交量萎缩：警惕趋势结束")
    print("   - 质量得分<50%：及时离场")


def example_6_aerospace_stocks():
    """示例6：航空航天板块股票池"""
    print("\n" + "=" * 60)
    print("示例6：航空航天板块股票池")
    print("=" * 60)
    
    aerospace_stocks = {
        '龙头股': [
            ('600893.SH', '航发动力', '航空发动机龙头'),
            ('600760.SH', '中航沈飞', '军用飞机龙头'),
            ('002013.SZ', '中航机电', '机电系统龙头'),
        ],
        '二线股': [
            ('000768.SZ', '中航西飞', '大型运输机'),
            ('600372.SH', '中航电子', '航空电子'),
            ('600038.SH', '中直股份', '直升机'),
        ],
        'ETF': [
            ('512900.SH', '航空航天ETF', '跟踪整个板块'),
        ]
    }
    
    print("航空航天板块股票池:")
    for category, stocks in aerospace_stocks.items():
        print(f"\n{category}:")
        for code, name, desc in stocks:
            print(f"  {code} - {name}: {desc}")
    
    print("\n选股建议:")
    print("  1. 龙头优先：流动性好，涨幅领先")
    print("  2. 分散持仓：不要全仓一只")
    print("  3. 关注催化剂：政策、订单、业绩")
    print("  4. ETF保底：不确定时选ETF")


def example_7_signal_interpretation():
    """示例7：信号解读"""
    print("\n" + "=" * 60)
    print("示例7：板块轮动信号解读")
    print("=" * 60)
    
    print("买入信号示例:")
    print("  信号类型: BUY")
    print("  置信度: 0.75")
    print("  原因: 强势板块(相对强度5.2%, 动量加速, 成交量放大, RSI健康, MACD正向)")
    print("  元数据:")
    print("    - relative_strength: 0.052")
    print("    - quality_score: 0.75")
    print("    - trend_quality: {")
    print("        'strong_momentum': True,")
    print("        'volume_confirmed': True,")
    print("        'rsi_healthy': True,")
    print("        'macd_positive': True")
    print("      }")
    
    print("\n解读:")
    print("  ✅ 板块跑赢大盘5.2%")
    print("  ✅ 4项质量指标全部通过")
    print("  ✅ 置信度0.75（较高）")
    print("  → 建议：可以建仓，设置8%止损")
    
    print("\n卖出信号示例:")
    print("  信号类型: SELL")
    print("  置信度: 0.65")
    print("  原因: 板块转弱(相对强度-6.1%)")
    print("  元数据:")
    print("    - relative_strength: -0.061")
    print("    - quality_score: 0.25")
    
    print("\n解读:")
    print("  ❌ 板块跑输大盘6.1%")
    print("  ❌ 质量得分仅25%")
    print("  ❌ 趋势已经转弱")
    print("  → 建议：及时离场，寻找新的强势板块")


if __name__ == "__main__":
    print("🚀 板块轮动策略使用示例")
    print("=" * 60)
    print("专门用于捕捉航空航天等强势板块趋势")
    
    examples = [
        ("注册板块轮动策略", example_1_register_sector_strategies),
        ("创建板块轮动配置", example_2_create_sector_rotation_config),
        ("航空航天板块专用配置", example_3_aerospace_sector_config),
        ("早期趋势捕捉配置", example_4_early_detection_config),
        ("风险管理要点", example_5_risk_management),
        ("航空航天股票池", example_6_aerospace_stocks),
        ("信号解读", example_7_signal_interpretation),
    ]
    
    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    choice = input("\n请选择要运行的示例 (1-7, 或 'all' 运行所有): ").strip()
    
    if choice.lower() == 'all':
        for name, func in examples:
            func()
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        examples[int(choice) - 1][1]()
    else:
        print("❌ 无效选项")

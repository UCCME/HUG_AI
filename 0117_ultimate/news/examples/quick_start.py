"""
快速开始示例
演示如何快速使用消息面数据系统
"""
import sys
sys.path.append('..')

from data_integrator import NewsDataIntegrator


def example_1_get_stock_news():
    """示例1：获取个股所有消息面数据"""
    print("\n" + "=" * 60)
    print("示例1：获取个股所有消息面数据")
    print("=" * 60)
    
    # 创建整合器
    integrator = NewsDataIntegrator()
    
    # 获取航发动力的所有数据
    symbol = "600893"
    data = integrator.get_all_news(symbol)
    
    # 查看数据
    print(f"\n获取到的数据类型：")
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"  - {key}: {len(value)} 个子项")
        else:
            print(f"  - {key}: {len(value) if hasattr(value, '__len__') else 'N/A'} 条")


def example_2_get_important_news():
    """示例2：只获取重要新闻"""
    print("\n" + "=" * 60)
    print("示例2：只获取重要新闻（大新闻筛选）")
    print("=" * 60)
    
    integrator = NewsDataIntegrator()
    
    # 获取市场重要新闻
    important_news = integrator.get_important_news_only()
    
    if not important_news.empty:
        print(f"\n筛选出 {len(important_news)} 条重要新闻：")
        for i, row in important_news.head(5).iterrows():
            print(f"\n{i+1}. [{row['source']}] {row['title']}")
            print(f"   重要性: {row['importance']}")
            print(f"   时间: {row['time']}")


def example_3_sentiment_analysis():
    """示例3：综合情绪分析"""
    print("\n" + "=" * 60)
    print("示例3：综合情绪分析")
    print("=" * 60)
    
    integrator = NewsDataIntegrator()
    
    # 分析航发动力的情绪
    symbol = "600893"
    sentiment = integrator.analyze_comprehensive_sentiment(symbol)
    
    print(f"\n综合情绪分析结果：")
    print(f"  整体情绪: {sentiment['overall_sentiment'].upper()}")
    print(f"  置信度: {sentiment['confidence']:.1%}")
    print(f"\n各数据源情绪：")
    for source, data in sentiment['sources'].items():
        print(f"  - {source}: {data['sentiment']} (权重: {data['weight']})")


def example_4_trading_signal():
    """示例4：生成交易信号"""
    print("\n" + "=" * 60)
    print("示例4：生成交易信号")
    print("=" * 60)
    
    integrator = NewsDataIntegrator()
    
    # 生成交易信号
    symbol = "600893"
    signal = integrator.generate_trading_signal(symbol)
    
    print(f"\n交易信号：")
    print(f"  信号: {signal['signal'].upper()}")
    print(f"  置信度: {signal['confidence']:.1%}")
    print(f"  重要新闻数: {signal['important_news_count']}")
    print(f"\n决策原因：")
    for reason in signal['reasons']:
        print(f"  - {reason}")


def example_5_sector_monitoring():
    """示例5：板块监控"""
    print("\n" + "=" * 60)
    print("示例5：板块监控")
    print("=" * 60)
    
    integrator = NewsDataIntegrator()
    
    # 监控航空航天板块
    sector = "航空航天"
    keywords = ["国防预算", "军工订单", "航空航天", "军民融合"]
    
    result = integrator.monitor_sector(sector, keywords)
    
    print(f"\n板块监控结果：")
    print(f"  板块: {result['sector']}")
    print(f"  新闻总数: {result['news_count']}")
    print(f"  龙头股票: {result['hot_stocks']}")
    print(f"\n关键词匹配：")
    for item in result['important_news']:
        print(f"  - {item['keyword']}: {item['count']} 条")


if __name__ == "__main__":
    print("🚀 消息面数据系统 - 快速开始")
    print("=" * 60)
    
    examples = [
        ("获取个股所有消息面数据", example_1_get_stock_news),
        ("只获取重要新闻", example_2_get_important_news),
        ("综合情绪分析", example_3_sentiment_analysis),
        ("生成交易信号", example_4_trading_signal),
        ("板块监控", example_5_sector_monitoring),
    ]
    
    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    choice = input("\n请选择要运行的示例 (1-5, 或 'all' 运行所有): ").strip()
    
    if choice.lower() == 'all':
        for name, func in examples:
            func()
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        examples[int(choice) - 1][1]()
    else:
        print("❌ 无效选项")

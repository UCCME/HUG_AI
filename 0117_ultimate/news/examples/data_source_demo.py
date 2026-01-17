"""
数据源演示
展示每个数据源的具体用法
"""
import sys
sys.path.append('..')

from api_sources import *
from crawler_sources import *


def demo_tushare():
    """Tushare Pro 演示"""
    print("\n" + "=" * 60)
    print("📰 Tushare Pro - 官方新闻联播")
    print("=" * 60)
    
    source = TushareSource()
    
    # 获取新闻联播
    news = source.get_major_news()
    if not news.empty:
        print(f"\n最新新闻联播（前3条）：")
        for i, row in news.head(3).iterrows():
            print(f"\n{i+1}. {row.get('title', 'N/A')}")
    
    print(f"\n数据源信息：")
    summary = source.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


def demo_akshare():
    """AkShare 演示"""
    print("\n" + "=" * 60)
    print("📊 AkShare - 数据搬运工")
    print("=" * 60)
    
    source = AkShareSource()
    
    # 获取个股新闻
    symbol = "600893"
    news = source.get_stock_news(symbol)
    
    if not news.empty:
        print(f"\n{symbol} 最新新闻（前3条）：")
        for i, row in news.head(3).iterrows():
            print(f"\n{i+1}. {row.get('标题', 'N/A')}")


def demo_cls():
    """财联社 演示"""
    print("\n" + "=" * 60)
    print("⚡ 财联社 - 最快快讯")
    print("=" * 60)
    
    source = CLSSource()
    
    # 获取重要快讯
    important = source.get_important_news(limit=5)
    
    if not important.empty:
        print(f"\n重要快讯（前3条）：")
        for i, row in important.head(3).iterrows():
            print(f"\n{i+1}. {row.get('title', 'N/A')}")
            print(f"   重要程度: {row.get('level', 0)}")


def demo_cninfo():
    """巨潮资讯 演示"""
    print("\n" + "=" * 60)
    print("📢 巨潮资讯 - 官方公告")
    print("=" * 60)
    
    source = CninfoSource()
    
    # 获取重大公告
    symbol = "600893"
    announcements = source.get_major_announcements(symbol, days=7)
    
    if not announcements.empty:
        print(f"\n{symbol} 重大公告（前3条）：")
        for i, row in announcements.head(3).iterrows():
            print(f"\n{i+1}. {row.get('title', 'N/A')}")
            print(f"   时间: {row.get('time', 'N/A')}")


def demo_wallstreetcn():
    """华尔街见闻 演示"""
    print("\n" + "=" * 60)
    print("🌍 华尔街见闻 - 大新闻筛选")
    print("=" * 60)
    
    source = WallstreetCNSource()
    
    # 获取重要新闻
    important = source.get_important_news(limit=5)
    
    if not important.empty:
        print(f"\n重要新闻（前3条）：")
        for i, row in important.head(3).iterrows():
            print(f"\n{i+1}. [{row.get('type', 'N/A')}] {row.get('title', 'N/A')}")


def demo_guba():
    """股吧 演示"""
    print("\n" + "=" * 60)
    print("💬 股吧 - 散户情绪（反向指标）")
    print("=" * 60)
    
    source = GubaSource()
    
    # 获取情绪指标
    symbol = "600893"
    indicator = source.get_sentiment_indicator(symbol)
    
    print(f"\n{symbol} 股吧情绪指标：")
    print(f"  热度等级: {indicator['heat_level']}")
    print(f"  情绪: {indicator['sentiment']}")
    print(f"  信号: {indicator['signal'].upper()}")
    print(f"  原因: {indicator['reason']}")


def demo_xueqiu():
    """雪球 演示"""
    print("\n" + "=" * 60)
    print("🎯 雪球 - 聪明钱情绪")
    print("=" * 60)
    
    source = XueqiuSource()
    
    # 获取聪明钱信号
    symbol = "SH600893"
    signal = source.get_smart_money_signal(symbol)
    
    print(f"\n{symbol} 聪明钱信号：")
    print(f"  情绪: {signal['sentiment']}")
    print(f"  信号: {signal['signal'].upper()}")
    print(f"  置信度: {signal['confidence']:.1%}")
    print(f"  原因: {signal['reason']}")


def demo_iwencai():
    """i问财 演示"""
    print("\n" + "=" * 60)
    print("🔍 i问财 - 自然语言搜索")
    print("=" * 60)
    
    source = IWencaiSource()
    
    # 搜索涨停原因
    result = source.get_limit_up_reasons()
    
    if not result.empty:
        print(f"\n今日涨停股票（前5只）：")
        for i, row in result.head(5).iterrows():
            print(f"\n{i+1}. {row.get('股票代码', 'N/A')} - {row.get('股票简称', 'N/A')}")
            if '涨停原因' in row:
                print(f"   原因: {row['涨停原因']}")


if __name__ == "__main__":
    print("🎯 数据源演示")
    print("=" * 60)
    
    demos = [
        ("Tushare Pro", demo_tushare),
        ("AkShare", demo_akshare),
        ("财联社", demo_cls),
        ("巨潮资讯", demo_cninfo),
        ("华尔街见闻", demo_wallstreetcn),
        ("股吧", demo_guba),
        ("雪球", demo_xueqiu),
        ("i问财", demo_iwencai),
    ]
    
    print("\n可用演示:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"{i}. {name}")
    
    choice = input("\n请选择要运行的演示 (1-8, 或 'all' 运行所有): ").strip()
    
    if choice.lower() == 'all':
        for name, func in demos:
            try:
                func()
            except Exception as e:
                print(f"❌ {name} 演示失败: {str(e)}")
    elif choice.isdigit() and 1 <= int(choice) <= len(demos):
        demos[int(choice) - 1][1]()
    else:
        print("❌ 无效选项")

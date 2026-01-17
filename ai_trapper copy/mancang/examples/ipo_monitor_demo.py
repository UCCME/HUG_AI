"""
IPO监控示例
演示如何使用IPO监控模块
"""

from datetime import datetime
from mancang import StrategyConfig
from mancang.strategy.ipo_monitor import IPOMonitor


def main():
    """主函数"""
    
    print("="*60)
    print("满仓大佬交易策略 - IPO监控")
    print("="*60)
    
    # 1. 获取配置
    config = StrategyConfig.get_config()
    
    # 2. 初始化IPO监控器
    ipo_monitor = IPOMonitor(config)
    
    # 3. 扫描IPO机会
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n扫描日期: {today}")
    print(f"时间窗口: 上市第{config['ipo_entry_day']}天")
    print(f"最少下跌天数: {config['ipo_min_decline_days']}天")
    print("\n正在扫描IPO机会...")
    
    opportunities = ipo_monitor.scan_ipo_opportunities(today, days=30)
    
    # 4. 显示结果
    if opportunities:
        print(f"\n发现 {len(opportunities)} 个IPO反包机会:")
        print("="*60)
        
        for i, ipo in enumerate(opportunities, 1):
            print(f"\n机会 {i}:")
            print(f"  股票代码: {ipo['symbol']}")
            print(f"  股票名称: {ipo['name']}")
            print(f"  上市日期: {ipo['list_date'].strftime('%Y-%m-%d')}")
            print(f"  上市天数: {ipo['days_since_ipo']}天")
            print(f"  发行价: ¥{ipo['issue_price']:.2f}")
            print(f"  当前价: ¥{ipo['current_price']:.2f}")
            print(f"  评分: {ipo['score']:.1f}")
            print(f"  原因: {ipo['reason']}")
            
            # 计算相对发行价的涨跌幅
            if ipo['issue_price'] > 0:
                change_from_issue = (ipo['current_price'] - ipo['issue_price']) / ipo['issue_price']
                print(f"  相对发行价: {change_from_issue:+.1%}")
    else:
        print("\n暂无IPO反包机会")
    
    # 5. 显示观察列表
    watchlist = ipo_monitor.get_watchlist()
    if watchlist:
        print(f"\n观察列表 ({len(watchlist)}只):")
        for item in watchlist:
            print(f"  - {item['symbol']} (上市日期: {item['list_date'].strftime('%Y-%m-%d')})")
    
    print("\n" + "="*60)
    print("IPO监控完成")
    print("="*60)


if __name__ == '__main__':
    main()

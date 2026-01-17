"""
定时任务调度器
用于实盘交易的定时任务管理
"""

import schedule
import time
from datetime import datetime, timedelta
from typing import Callable, Dict
from mancang.strategy.mancang_strategy import MancangStrategy
from mancang.utils.data_loader import DataLoader


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, strategy: MancangStrategy):
        """
        初始化调度器
        
        Args:
            strategy: 满仓策略实例
        """
        self.strategy = strategy
        self.data_loader = DataLoader(
            data_source=strategy.config.get('data_source', 'akshare')
        )
        self.is_running = False
        
    def setup_tasks(self):
        """设置定时任务"""
        
        # 06:00 - 检查美股数据
        schedule.every().day.at("06:00").do(self.check_us_market)
        
        # 09:25 - 开盘前准备
        schedule.every().day.at("09:25").do(self.pre_market_check)
        
        # 09:30-15:00 - 盘中监控（每小时）
        for hour in range(10, 15):
            schedule.every().day.at(f"{hour:02d}:00").do(self.intraday_monitor)
        
        # 15:30 - 盘后复盘
        schedule.every().day.at("15:30").do(self.after_market_review)
        
        print("定时任务已设置:")
        print("  06:00 - 美股数据检查")
        print("  09:25 - 开盘前准备")
        print("  10:00-14:00 - 盘中监控（每小时）")
        print("  15:30 - 盘后复盘")
    
    def check_us_market(self):
        """检查美股市场情绪"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 检查美股数据...")
        
        try:
            us_data = self.data_loader.load_us_market_data()
            
            if us_data:
                nasdaq_change = us_data.get('nasdaq_change', 0)
                
                print(f"纳斯达克变动: {nasdaq_change:+.2f}")
                
                if nasdaq_change < -100:
                    print("⚠️ 美股大跌，今日需谨慎")
                    # 可以调整为高风险模式
                    self.strategy.config['max_total_pos'] = self.strategy.config['max_total_pos_high_risk']
                elif nasdaq_change > 100:
                    print("✅ 美股大涨，市场情绪较好")
                    
        except Exception as e:
            print(f"检查美股数据失败: {str(e)}")
    
    def pre_market_check(self):
        """开盘前检查"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开盘前准备...")
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 1. 更新龙头池
            print("更新龙头池...")
            self.strategy._update_dragon_pool(today)
            
            # 2. 扫描IPO机会
            print("扫描IPO机会...")
            ipo_opportunities = self.strategy.ipo_monitor.scan_ipo_opportunities(today)
            
            if ipo_opportunities:
                print(f"发现 {len(ipo_opportunities)} 个IPO机会")
                for ipo in ipo_opportunities[:3]:
                    print(f"  - {ipo['symbol']} {ipo['name']} (评分: {ipo['score']:.1f})")
            
            # 3. 检查市场情绪
            market_data = self.data_loader.load_market_data(today)
            can_trade, sentiment = self.strategy.signal_generator.check_market_sentiment(market_data)
            
            print(f"市场情绪: {sentiment}")
            
            if not can_trade:
                print("⚠️ 市场情绪不足，今日建议观望")
            else:
                print("✅ 市场情绪良好，可以交易")
                
        except Exception as e:
            print(f"开盘前检查失败: {str(e)}")
    
    def intraday_monitor(self):
        """盘中监控"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 盘中监控...")
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 1. 检查持仓止损
            print("检查持仓止损...")
            exit_actions = self.strategy._check_exit_signals(today)
            
            if exit_actions:
                print(f"⚠️ 触发 {len(exit_actions)} 个卖出信号")
                for action in exit_actions:
                    print(f"  - {action['symbol']}: {action['reason']}")
            else:
                print("✅ 所有持仓正常")
            
            # 2. 检查冲高回落
            for symbol in self.strategy.risk_manager.positions.keys():
                try:
                    # 加载实时数据
                    data = self.data_loader.load_stock_data(
                        symbol,
                        (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                        today
                    )
                    
                    if not data.empty:
                        # 检测冲高回落
                        from mancang.utils.indicators import TechnicalIndicators
                        
                        is_surge = TechnicalIndicators.detect_surge_and_pullback(
                            data,
                            surge_threshold=self.strategy.config['take_profit_surge'],
                            pullback_threshold=self.strategy.config['take_profit_pullback']
                        )
                        
                        if is_surge.iloc[-1]:
                            print(f"⚠️ {symbol} 出现冲高回落，建议减仓")
                            
                except Exception as e:
                    continue
            
            # 3. 显示组合状态
            portfolio = self.strategy.risk_manager.get_portfolio_status()
            print(f"\n当前组合:")
            print(f"  总资产: ¥{portfolio['total_value']:,.2f}")
            print(f"  持仓数: {portfolio['position_count']}")
            print(f"  仓位: {portfolio['position_ratio']:.1%}")
            print(f"  收益: {portfolio['total_return']:+.2%}")
            
        except Exception as e:
            print(f"盘中监控失败: {str(e)}")
    
    def after_market_review(self):
        """盘后复盘"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 盘后复盘...")
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 1. 执行完整的每日策略
            print("执行每日策略...")
            result = self.strategy.run_daily(today)
            
            # 2. 生成复盘报告
            print("\n" + "="*60)
            print("复盘报告")
            print("="*60)
            
            # 市场数据
            market_data = self.data_loader.load_market_data(today)
            if market_data:
                print(f"\n市场概况:")
                print(f"  涨停: {market_data.get('limit_up_count', 0)}家")
                print(f"  跌停: {market_data.get('limit_down_count', 0)}家")
                print(f"  上涨: {market_data.get('up_count', 0)}家")
                print(f"  下跌: {market_data.get('down_count', 0)}家")
            
            # 龙头池
            if self.strategy.dragon_pool:
                print(f"\n龙头池 (Top 5):")
                for i, dragon in enumerate(self.strategy.dragon_pool[:5], 1):
                    print(f"  {i}. {dragon['symbol']} (评分: {dragon['score']:.1f})")
            
            # 持仓情况
            positions = self.strategy.risk_manager.positions
            if positions:
                print(f"\n当前持仓:")
                for symbol, pos in positions.items():
                    pnl_info = self.strategy.risk_manager.calculate_position_pnl(symbol)
                    print(f"  {symbol}: {pos['shares']}股 @{pos['entry_price']:.2f} "
                          f"盈亏: {pnl_info['pnl_ratio']:+.2%}")
            
            # 交易统计
            trade_stats = self.strategy.risk_manager.get_trade_statistics()
            if trade_stats:
                print(f"\n交易统计:")
                print(f"  总交易: {trade_stats.get('total_trades', 0)}笔")
                print(f"  胜率: {trade_stats.get('win_rate', 0):.1%}")
                print(f"  总盈亏: ¥{trade_stats.get('total_pnl', 0):,.2f}")
            
        except Exception as e:
            print(f"盘后复盘失败: {str(e)}")
    
    def start(self):
        """启动调度器"""
        self.setup_tasks()
        self.is_running = True
        
        print(f"\n调度器已启动，等待任务执行...")
        print("按 Ctrl+C 停止")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n调度器已停止")
            self.is_running = False
    
    def stop(self):
        """停止调度器"""
        self.is_running = False
        schedule.clear()
        print("调度器已停止")

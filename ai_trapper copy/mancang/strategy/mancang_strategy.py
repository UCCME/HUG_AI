"""
满仓大佬核心策略类
整合所有模块，实现完整的交易策略
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from mancang.config.strategy_config import StrategyConfig
from mancang.strategy.stock_selector import StockSelector
from mancang.strategy.signal_generator import SignalGenerator
from mancang.strategy.risk_manager import RiskManager
from mancang.strategy.ipo_monitor import IPOMonitor
from mancang.utils.data_loader import DataLoader


class MancangStrategy:
    """满仓大佬交易策略"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化策略
        
        Args:
            config: 策略配置字典（可选，默认使用StrategyConfig）
        """
        self.config = config or StrategyConfig.get_config()
        
        # 初始化各个模块
        self.stock_selector = StockSelector(self.config)
        self.signal_generator = SignalGenerator(self.config)
        self.risk_manager = RiskManager(
            self.config,
            self.config.get('initial_capital', 1000000)
        )
        self.ipo_monitor = IPOMonitor(self.config)
        self.data_loader = DataLoader(
            data_source=self.config.get('data_source', 'akshare'),
            token=self.config.get('tushare_token')
        )
        
        # 策略状态
        self.current_date = None
        self.dragon_pool = []  # 龙头池
        self.trade_log = []
        
    def run_daily(self, date: str) -> Dict:
        """
        执行每日策略
        
        Args:
            date: 交易日期 'YYYY-MM-DD'
            
        Returns:
            当日执行结果
        """
        self.current_date = date
        results = {
            'date': date,
            'actions': [],
            'signals': [],
            'portfolio': {}
        }
        
        print(f"\n{'='*60}")
        print(f"执行日期: {date}")
        print(f"{'='*60}")
        
        # 1. 检查市场情绪
        market_data = self.data_loader.load_market_data(date)
        can_trade, sentiment_score = self.signal_generator.check_market_sentiment(market_data)
        
        print(f"市场情绪分数: {sentiment_score}")
        
        if not can_trade:
            print(f"市场情绪不足({sentiment_score} < {self.config['min_market_sentiment']})，今日不交易")
            results['reason'] = '市场情绪不足'
            return results
        
        # 2. 检查持仓止损（最高优先级）
        exit_actions = self._check_exit_signals(date)
        results['actions'].extend(exit_actions)
        
        # 3. 更新龙头池
        self._update_dragon_pool(date)
        
        # 4. 扫描IPO机会
        ipo_opportunities = self.ipo_monitor.scan_ipo_opportunities(date)
        
        # 5. 生成买入信号
        entry_signals = self._generate_entry_signals(date, ipo_opportunities)
        results['signals'] = entry_signals
        
        # 6. 执行买入
        entry_actions = self._execute_entry_signals(entry_signals, date)
        results['actions'].extend(entry_actions)
        
        # 7. 更新组合状态
        results['portfolio'] = self.risk_manager.get_portfolio_status()
        
        # 8. 打印日志
        self._print_daily_summary(results)
        
        return results
    
    def _check_exit_signals(self, date: str) -> List[Dict]:
        """
        检查卖出信号
        
        Args:
            date: 日期
            
        Returns:
            卖出操作列表
        """
        actions = []
        
        for symbol in list(self.risk_manager.positions.keys()):
            try:
                position = self.risk_manager.positions[symbol]
                
                # 加载股票数据
                end_date = pd.to_datetime(date)
                start_date = end_date - pd.Timedelta(days=30)
                
                data = self.data_loader.load_stock_data(
                    symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if data.empty:
                    continue
                
                # 更新当前价格
                current_price = data['close'].iloc[-1]
                self.risk_manager.update_position_price(symbol, current_price)
                
                # 生成卖出信号
                should_exit, reason, exit_ratio = self.signal_generator.generate_exit_signal(
                    data,
                    position['entry_price'],
                    position.get('position_ratio', 1.0)
                )
                
                if should_exit:
                    # 执行卖出
                    if exit_ratio >= 1.0:
                        # 全部卖出
                        shares = self.risk_manager.close_position(symbol, current_price, date)
                        action_type = '清仓'
                    else:
                        # 部分卖出
                        shares = self.risk_manager.reduce_position(symbol, exit_ratio, current_price, date)
                        action_type = f'减仓{exit_ratio:.0%}'
                    
                    actions.append({
                        'type': 'SELL',
                        'symbol': symbol,
                        'shares': shares,
                        'price': current_price,
                        'reason': reason,
                        'action': action_type
                    })
                    
                    print(f"[卖出] {symbol} {action_type} {shares}股 @{current_price:.2f} - {reason}")
                    
            except Exception as e:
                print(f"检查{symbol}卖出信号失败: {str(e)}")
                continue
        
        return actions
    
    def _update_dragon_pool(self, date: str):
        """
        更新龙头池
        
        Args:
            date: 日期
        """
        try:
            # 选择龙头股
            dragons = self.stock_selector.select_dragon_heads(date, top_n=10)
            self.dragon_pool = dragons
            
            if dragons:
                print(f"\n龙头池更新: 发现 {len(dragons)} 只龙头股")
                for i, dragon in enumerate(dragons[:5], 1):
                    print(f"  {i}. {dragon['symbol']} (评分: {dragon['score']:.1f})")
        except Exception as e:
            print(f"更新龙头池失败: {str(e)}")
    
    def _generate_entry_signals(self, date: str, ipo_opportunities: List[Dict]) -> List[Dict]:
        """
        生成买入信号
        
        Args:
            date: 日期
            ipo_opportunities: IPO机会列表
            
        Returns:
            买入信号列表
        """
        signals = []
        
        # 1. 龙头回调低吸信号
        for dragon in self.dragon_pool[:5]:  # 只看前5只
            try:
                symbol = dragon['symbol']
                data = dragon['data']
                
                # 检查是否已持有
                if symbol in self.risk_manager.positions:
                    continue
                
                # 生成信号
                should_buy, reason, position_ratio = self.signal_generator.generate_entry_signal(
                    data,
                    signal_type='pullback'
                )
                
                if should_buy:
                    signals.append({
                        'symbol': symbol,
                        'type': '龙头回调',
                        'reason': reason,
                        'position_ratio': position_ratio,
                        'score': dragon['score'],
                        'data': data
                    })
                    
            except Exception as e:
                continue
        
        # 2. IPO反包信号
        for ipo in ipo_opportunities[:3]:  # 只看前3只
            try:
                symbol = ipo['symbol']
                
                if symbol in self.risk_manager.positions:
                    continue
                
                signals.append({
                    'symbol': symbol,
                    'type': 'IPO反包',
                    'reason': ipo['reason'],
                    'position_ratio': self.config['single_pos_limit'],
                    'score': ipo['score'],
                    'data': ipo['data']
                })
                
            except Exception as e:
                continue
        
        # 按评分排序
        signals.sort(key=lambda x: x['score'], reverse=True)
        
        return signals
    
    def _execute_entry_signals(self, signals: List[Dict], date: str) -> List[Dict]:
        """
        执行买入信号
        
        Args:
            signals: 买入信号列表
            date: 日期
            
        Returns:
            买入操作列表
        """
        actions = []
        
        for signal in signals:
            symbol = signal['symbol']
            
            # 检查是否可以开仓
            can_open, reason = self.risk_manager.can_open_position(symbol)
            
            if not can_open:
                print(f"[跳过] {symbol} - {reason}")
                continue
            
            try:
                # 获取当前价格
                current_price = signal['data']['close'].iloc[-1]
                
                # 计算仓位
                shares = self.risk_manager.calculate_position_size(
                    symbol,
                    current_price,
                    signal_strength=signal['position_ratio'] / self.config['single_pos_limit']
                )
                
                if shares <= 0:
                    continue
                
                # 执行买入
                self.risk_manager.add_position(symbol, shares, current_price, date)
                
                actions.append({
                    'type': 'BUY',
                    'symbol': symbol,
                    'shares': shares,
                    'price': current_price,
                    'reason': signal['reason'],
                    'signal_type': signal['type']
                })
                
                print(f"[买入] {symbol} {shares}股 @{current_price:.2f} - {signal['type']}: {signal['reason']}")
                
            except Exception as e:
                print(f"执行{symbol}买入失败: {str(e)}")
                continue
        
        return actions
    
    def _print_daily_summary(self, results: Dict):
        """
        打印每日总结
        
        Args:
            results: 执行结果
        """
        print(f"\n{'='*60}")
        print(f"每日总结 - {results['date']}")
        print(f"{'='*60}")
        
        portfolio = results['portfolio']
        print(f"总资产: ¥{portfolio['total_value']:,.2f}")
        print(f"持仓市值: ¥{portfolio['position_value']:,.2f}")
        print(f"可用资金: ¥{portfolio['available_cash']:,.2f}")
        print(f"总收益: ¥{portfolio['total_pnl']:,.2f} ({portfolio['total_return']:.2%})")
        print(f"仓位比例: {portfolio['position_ratio']:.1%}")
        print(f"持仓数量: {portfolio['position_count']}")
        
        if results['actions']:
            print(f"\n今日操作: {len(results['actions'])}笔")
            for action in results['actions']:
                print(f"  - {action}")
    
    def get_performance_report(self) -> Dict:
        """
        获取策略表现报告
        
        Returns:
            表现报告字典
        """
        portfolio = self.risk_manager.get_portfolio_status()
        trade_stats = self.risk_manager.get_trade_statistics()
        
        return {
            'portfolio': portfolio,
            'trade_statistics': trade_stats,
            'positions': self.risk_manager.positions,
            'dragon_pool': self.dragon_pool
        }
    
    def backtest(self, start_date: str, end_date: str) -> Dict:
        """
        回测策略
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            回测结果
        """
        print(f"\n开始回测: {start_date} 至 {end_date}")
        print(f"初始资金: ¥{self.config['initial_capital']:,.2f}")
        
        # 生成交易日列表（简化版，实际应该使用交易日历）
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        date_range = pd.date_range(start, end, freq='B')  # B = 工作日
        
        daily_results = []
        
        for date in date_range:
            date_str = date.strftime('%Y-%m-%d')
            
            try:
                result = self.run_daily(date_str)
                daily_results.append(result)
            except Exception as e:
                print(f"执行{date_str}失败: {str(e)}")
                continue
        
        # 生成回测报告
        final_report = self.get_performance_report()
        final_report['daily_results'] = daily_results
        
        print(f"\n{'='*60}")
        print("回测完成")
        print(f"{'='*60}")
        
        return final_report

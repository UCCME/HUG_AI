"""
松松交易策略主模块
整合选股、信号生成、风险控制等模块，实现完整的交易策略
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .stock_selector import StockSelector
from .signal_generator import SignalGenerator
from .risk_manager import RiskManager
from ..utils.indicators import TechnicalIndicators
from ..utils.data_loader import DataLoader


class SongSongStrategy:
    """
    松松交易策略
    
    策略核心：
    1. 选股：题材龙头、资金流入前10、中小市值、板块效应强
    2. 买入：竞价弱转强、早盘快速板、龙头回封板
    3. 卖出：次日竞价不及预期、炸板止损、获利目标
    4. 风控：单笔亏损<1%、半仓滚动、动态仓位、空仓等待
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化策略
        
        Args:
            config: 策略配置
        """
        self.config = config or self._default_config()
        
        # 初始化各模块
        self.selector = StockSelector(self.config.get('selector', {}))
        self.signal_gen = SignalGenerator(self.config.get('signal', {}))
        self.risk_mgr = RiskManager(self.config.get('risk', {}))
        self.indicators = TechnicalIndicators()
        self.data_loader = DataLoader(self.config.get('data_source', 'local'))
        
        # 策略状态
        self.capital = self.config.get('initial_capital', 1000000)
        self.current_date = None
        
    def _default_config(self) -> Dict:
        """默认策略配置"""
        return {
            'initial_capital': 1000000,      # 初始资金100万
            'data_source': 'local',          # 数据源
            'strategy_mode': 'half_position', # 策略模式：half_position（半仓滚动）
            'max_positions': 1,               # 最大持仓数：每天只买一只
            'enable_融资': False,             # 是否启用融资
        }
    
    def run(self, 
            start_date: str, 
            end_date: str,
            symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """
        运行策略
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 股票池（如果为None则全市场选股）
            
        Returns:
            回测结果DataFrame
        """
        results = []
        
        # 获取交易日历
        trade_dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        for date in trade_dates:
            date_str = date.strftime('%Y-%m-%d')
            self.current_date = date_str
            
            # 获取市场数据
            market_data = self.data_loader.load_market_data(date_str)
            
            # 计算市场情绪
            market_sentiment = self._calculate_market_sentiment(market_data)
            
            # 处理持仓
            self._process_positions(date_str, market_data, market_sentiment)
            
            # 寻找新机会
            if self._should_look_for_opportunity(market_sentiment):
                self._find_and_execute_trades(date_str, market_data, market_sentiment)
            
            # 记录当日结果
            daily_result = self._calculate_daily_result(date_str)
            results.append(daily_result)
        
        return pd.DataFrame(results)
    
    def _calculate_market_sentiment(self, market_data: pd.DataFrame) -> float:
        """
        计算市场情绪
        
        Args:
            market_data: 市场数据
            
        Returns:
            市场情绪分数 0-100
        """
        if len(market_data) == 0:
            return 50.0
        
        # 涨跌家数比
        up_count = (market_data['change_pct'] > 0).sum()
        total_count = len(market_data)
        up_ratio = up_count / total_count if total_count > 0 else 0.5
        
        # 涨停家数
        limit_up_count = (market_data['change_pct'] >= 9.9).sum()
        limit_up_ratio = limit_up_count / total_count if total_count > 0 else 0
        
        # 平均涨幅
        avg_change = market_data['change_pct'].mean()
        
        # 综合评分
        sentiment = (
            up_ratio * 40 +
            limit_up_ratio * 100 * 30 +
            (avg_change + 5) * 6  # 归一化到0-60
        )
        
        return np.clip(sentiment, 0, 100)
    
    def _process_positions(self, 
                          date: str,
                          market_data: pd.DataFrame,
                          market_sentiment: float):
        """
        处理现有持仓
        
        Args:
            date: 日期
            market_data: 市场数据
            market_sentiment: 市场情绪
        """
        for symbol in list(self.risk_mgr.positions.keys()):
            position = self.risk_mgr.positions[symbol]
            
            # 获取股票数据
            stock_data = market_data[market_data['symbol'] == symbol]
            if len(stock_data) == 0:
                continue
            
            current_data = stock_data.iloc[0]
            
            # 获取历史数据
            hist_data = self.data_loader.load_stock_data(
                symbol,
                start_date=(pd.Timestamp(date) - pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
                end_date=date
            )
            
            # 构建市场状态
            market_status = self._build_market_status(
                symbol, current_data, hist_data, market_data
            )
            
            # 检查卖出信号
            should_sell, reason, sell_price = self.signal_gen.generate_sell_signal(
                symbol,
                position['cost'],
                current_data,
                hist_data,
                market_status
            )
            
            if should_sell:
                # 执行卖出
                self.risk_mgr.record_trade(
                    symbol=symbol,
                    action='sell',
                    price=sell_price,
                    quantity=position['quantity'],
                    date=date,
                    reason=reason
                )
                print(f"{date} 卖出 {symbol} @ {sell_price:.2f}, 原因: {reason}")
    
    def _should_look_for_opportunity(self, market_sentiment: float) -> bool:
        """
        判断是否应该寻找新机会
        
        Args:
            market_sentiment: 市场情绪
            
        Returns:
            是否寻找机会
        """
        # 市场情绪差，空仓等待
        if market_sentiment < self.config.get('min_market_sentiment', 40):
            return False
        
        # 已达最大持仓数
        if len(self.risk_mgr.positions) >= self.config['max_positions']:
            return False
        
        return True
    
    def _find_and_execute_trades(self, 
                                 date: str,
                                 market_data: pd.DataFrame,
                                 market_sentiment: float):
        """
        寻找并执行交易
        
        Args:
            date: 日期
            market_data: 市场数据
            market_sentiment: 市场情绪
        """
        # 选股
        candidates = self.selector.select_stocks(date, market_data)
        
        if not candidates:
            return
        
        # 遍历候选股票
        for symbol in candidates[:3]:  # 最多检查前3只
            # 检查是否可以开仓
            can_open, reason = self.risk_mgr.should_take_position(
                symbol, date, market_sentiment
            )
            
            if not can_open:
                continue
            
            # 获取股票数据
            stock_data = market_data[market_data['symbol'] == symbol]
            if len(stock_data) == 0:
                continue
            
            current_data = stock_data.iloc[0]
            
            # 获取历史数据
            hist_data = self.data_loader.load_stock_data(
                symbol,
                start_date=(pd.Timestamp(date) - pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
                end_date=date
            )
            
            # 构建市场状态
            market_status = self._build_market_status(
                symbol, current_data, hist_data, market_data
            )
            
            # 检查买入信号
            should_buy, reason, buy_price = self.signal_gen.generate_buy_signal(
                symbol,
                current_data,
                hist_data,
                market_status
            )
            
            if should_buy:
                # 计算持仓评分
                position_score = self.signal_gen.calculate_position_score(
                    symbol, current_data, hist_data, market_status
                )
                
                # 计算仓位
                position_size = self.risk_mgr.calculate_position_size(
                    symbol,
                    buy_price,
                    self.capital,
                    position_score,
                    market_sentiment
                )
                
                if position_size > 0:
                    quantity = int(position_size / buy_price / 100) * 100  # 整百股
                    
                    # 执行买入
                    self.risk_mgr.record_trade(
                        symbol=symbol,
                        action='buy',
                        price=buy_price,
                        quantity=quantity,
                        date=date,
                        reason=reason
                    )
                    
                    print(f"{date} 买入 {symbol} @ {buy_price:.2f}, 数量: {quantity}, 原因: {reason}")
                    
                    # 每天只买一只
                    break
    
    def _build_market_status(self, 
                            symbol: str,
                            current_data: pd.Series,
                            hist_data: pd.DataFrame,
                            market_data: pd.DataFrame) -> Dict:
        """
        构建市场状态信息
        
        Args:
            symbol: 股票代码
            current_data: 当前数据
            hist_data: 历史数据
            market_data: 市场数据
            
        Returns:
            市场状态字典
        """
        # 获取涨停板信息
        limit_up_stocks = self.data_loader.load_limit_up_stocks(self.current_date)
        limit_info = limit_up_stocks[limit_up_stocks['symbol'] == symbol]
        
        # 计算板块强度
        sector_strength = 0.0
        # 这里简化处理，实际应该识别股票所属板块
        
        market_status = {
            'date': self.current_date,
            'market_sentiment': self._calculate_market_sentiment(market_data),
            'sector_strength': sector_strength,
        }
        
        # 添加涨停板信息
        if len(limit_info) > 0:
            info = limit_info.iloc[0]
            market_status.update({
                'limit_up_time': info.get('limit_up_time'),
                'open_count': info.get('open_count', 0),
                'is_sealed': info.get('sealed', False)
            })
        
        # 添加量比信息
        if len(hist_data) >= 5:
            avg_volume = hist_data['volume'].tail(5).mean()
            current_volume = current_data.get('volume', avg_volume)
            market_status['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        return market_status
    
    def _calculate_daily_result(self, date: str) -> Dict:
        """
        计算当日结果
        
        Args:
            date: 日期
            
        Returns:
            当日结果字典
        """
        # 计算持仓市值
        position_value = 0.0
        for symbol, pos in self.risk_mgr.positions.items():
            # 这里应该获取最新价格，简化处理
            position_value += pos['cost'] * pos['quantity']
        
        cash = self.capital - position_value
        total_value = cash + position_value
        
        return {
            'date': date,
            'cash': cash,
            'position_value': position_value,
            'total_value': total_value,
            'return': (total_value - self.config['initial_capital']) / self.config['initial_capital'],
            'positions': len(self.risk_mgr.positions)
        }
    
    def get_performance_report(self) -> Dict:
        """
        获取策略表现报告
        
        Returns:
            表现报告字典
        """
        stats = self.risk_mgr.get_statistics()
        
        return {
            '总交易次数': stats['total_trades'],
            '胜率': f"{stats['win_rate']*100:.2f}%",
            '平均收益': f"{stats['avg_profit']*100:.2f}%",
            '最大亏损': f"{stats.get('max_loss', 0)*100:.2f}%",
            '最大盈利': f"{stats.get('max_profit', 0)*100:.2f}%",
            '夏普比率': f"{stats.get('sharpe_ratio', 0):.2f}",
            '当前持仓': len(self.risk_mgr.positions)
        }

"""
选股模块
实现松松的选股标准：题材龙头、资金流入、市值筛选、板块效应
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from ..utils.indicators import TechnicalIndicators
from ..utils.data_loader import DataLoader


class StockSelector:
    """选股器类"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化选股器
        
        Args:
            config: 选股配置参数
        """
        self.config = config or self._default_config()
        self.indicators = TechnicalIndicators()
        self.data_loader = DataLoader()
        
    def _default_config(self) -> Dict:
        """默认选股配置"""
        return {
            'min_market_cap': 20e8,      # 最小市值20亿
            'max_market_cap': 500e8,     # 最大市值500亿（中小市值）
            'min_turnover': 5.0,         # 最小换手率5%
            'max_continuous_limit': 3,    # 最大连板数3板
            'money_flow_top_n': 10,      # 资金流入前N名
            'sector_min_stocks': 3,       # 板块最少股票数
            'sector_min_limit_up': 2      # 板块最少涨停数
        }
    
    def select_stocks(self, 
                     date: str, 
                     market_data: pd.DataFrame) -> List[str]:
        """
        主选股流程
        
        Args:
            date: 交易日期
            market_data: 市场数据
            
        Returns:
            选中的股票代码列表
        """
        # 1. 基础筛选
        candidates = self._basic_filter(market_data)
        
        # 2. 板块效应筛选
        sector_leaders = self._select_sector_leaders(candidates, date)
        
        # 3. 资金流向筛选
        top_money_flow = self._select_by_money_flow(sector_leaders)
        
        # 4. 题材热度筛选
        hot_stocks = self._select_hot_topics(top_money_flow, date)
        
        return hot_stocks
    
    def _basic_filter(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        基础筛选条件
        - 市值范围：中小市值
        - 非ST股票
        - 有一定换手率
        - 不是连续3板以上
        
        Args:
            market_data: 市场数据
            
        Returns:
            筛选后的数据
        """
        filtered = market_data.copy()
        
        # 市值筛选
        filtered = filtered[
            (filtered['market_cap'] >= self.config['min_market_cap']) &
            (filtered['market_cap'] <= self.config['max_market_cap'])
        ]
        
        # 排除ST股票
        if 'name' in filtered.columns:
            filtered = filtered[~filtered['name'].str.contains('ST', na=False)]
        
        # 换手率筛选
        if 'turnover_rate' in filtered.columns:
            filtered = filtered[
                filtered['turnover_rate'] >= self.config['min_turnover']
            ]
        
        # 排除高连板股票
        if 'continuous_limit_days' in filtered.columns:
            filtered = filtered[
                filtered['continuous_limit_days'] <= self.config['max_continuous_limit']
            ]
        
        return filtered
    
    def _select_sector_leaders(self, 
                               candidates: pd.DataFrame, 
                               date: str) -> pd.DataFrame:
        """
        选择板块龙头股
        板块效应：板块内有多只涨停股，选择其中的龙头
        
        Args:
            candidates: 候选股票
            date: 日期
            
        Returns:
            板块龙头股票
        """
        # 加载板块数据
        sector_data = self.data_loader.load_sector_data(date)
        
        # 统计每个板块的涨停数量
        sector_stats = {}
        for sector, stocks in sector_data.items():
            sector_stocks = candidates[candidates['symbol'].isin(stocks)]
            
            if len(sector_stocks) >= self.config['sector_min_stocks']:
                limit_up_count = (sector_stocks['change_pct'] >= 9.9).sum()
                
                if limit_up_count >= self.config['sector_min_limit_up']:
                    sector_stats[sector] = {
                        'stocks': stocks,
                        'limit_up_count': limit_up_count,
                        'avg_change': sector_stocks['change_pct'].mean()
                    }
        
        # 选择热门板块的龙头股
        leaders = []
        for sector, stats in sorted(
            sector_stats.items(), 
            key=lambda x: (x[1]['limit_up_count'], x[1]['avg_change']),
            reverse=True
        )[:3]:  # 选择前3个最强板块
            sector_stocks = candidates[
                candidates['symbol'].isin(stats['stocks'])
            ].copy()
            
            # 板块内按资金流入排序，选择龙头
            sector_stocks = sector_stocks.sort_values(
                'money_flow', 
                ascending=False
            )
            
            leaders.extend(sector_stocks.head(2)['symbol'].tolist())
        
        return candidates[candidates['symbol'].isin(leaders)]
    
    def _select_by_money_flow(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """
        按主力资金流入筛选
        "开盘半小时按主力净流入排序，净流入排名前10的纳入观察池"
        
        Args:
            candidates: 候选股票
            
        Returns:
            资金流入前N的股票
        """
        if len(candidates) == 0:
            return candidates
        
        # 按主力资金流入排序
        sorted_stocks = candidates.sort_values(
            'money_flow', 
            ascending=False
        )
        
        # 选择前N名
        top_n = self.config['money_flow_top_n']
        return sorted_stocks.head(top_n)
    
    def _select_hot_topics(self, 
                          candidates: pd.DataFrame, 
                          date: str) -> List[str]:
        """
        选择热点题材股票
        基于近期涨停板、市场情绪等因素
        
        Args:
            candidates: 候选股票
            date: 日期
            
        Returns:
            热点题材股票代码列表
        """
        if len(candidates) == 0:
            return []
        
        # 加载涨停板数据
        limit_up_stocks = self.data_loader.load_limit_up_stocks(date)
        
        # 优先选择涨停股
        limit_up_candidates = candidates[
            candidates['symbol'].isin(limit_up_stocks['symbol'])
        ]
        
        if len(limit_up_candidates) > 0:
            # 合并涨停信息
            result = limit_up_candidates.merge(
                limit_up_stocks[['symbol', 'limit_up_time', 'open_count', 'sealed']],
                on='symbol',
                how='left'
            )
            
            # 优先选择：
            # 1. 早盘快速封板（9:30-10:00）
            # 2. 封死涨停（sealed=True）
            # 3. 炸板次数少（open_count小）
            result['priority_score'] = (
                (pd.to_datetime(result['limit_up_time']) < pd.Timestamp('10:00:00')).astype(int) * 3 +
                result['sealed'].astype(int) * 2 +
                (3 - result['open_count'].clip(0, 3))
            )
            
            result = result.sort_values('priority_score', ascending=False)
            
            return result['symbol'].tolist()
        
        # 如果没有涨停股，选择资金流入最大的
        return candidates.nlargest(5, 'money_flow')['symbol'].tolist()
    
    def is_early_limit_up(self, 
                         symbol: str, 
                         limit_up_time: str) -> bool:
        """
        判断是否为早盘快速板（9:30-10:00）
        
        Args:
            symbol: 股票代码
            limit_up_time: 涨停时间
            
        Returns:
            是否为早盘快速板
        """
        if pd.isna(limit_up_time):
            return False
        
        time = pd.to_datetime(limit_up_time).time()
        return time <= pd.Timestamp('10:00:00').time()
    
    def evaluate_sector_strength(self, 
                                sector: str, 
                                date: str) -> float:
        """
        评估板块强度
        
        Args:
            sector: 板块名称
            date: 日期
            
        Returns:
            板块强度分数
        """
        sector_data = self.data_loader.load_sector_data(date)
        
        if sector not in sector_data:
            return 0.0
        
        stocks = sector_data[sector]
        market_data = self.data_loader.load_market_data(date)
        
        sector_stocks = market_data[market_data['symbol'].isin(stocks)]
        
        if len(sector_stocks) == 0:
            return 0.0
        
        # 计算板块强度指标
        avg_change = sector_stocks['change_pct'].mean()
        limit_up_ratio = (sector_stocks['change_pct'] >= 9.9).sum() / len(sector_stocks)
        avg_turnover = sector_stocks.get('turnover_rate', pd.Series([0])).mean()
        
        # 综合评分
        strength = (
            avg_change * 0.4 +
            limit_up_ratio * 100 * 0.4 +
            avg_turnover * 0.2
        )
        
        return strength

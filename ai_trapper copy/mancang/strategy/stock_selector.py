"""
选股模块
负责龙头识别、板块分析和股票筛选
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from mancang.utils.indicators import TechnicalIndicators
from mancang.utils.data_loader import DataLoader


class StockSelector:
    """股票选择器类"""
    
    def __init__(self, config: Dict):
        """
        初始化选股器
        
        Args:
            config: 策略配置字典
        """
        self.config = config
        self.data_loader = DataLoader(
            data_source=config.get('data_source', 'akshare'),
            token=config.get('tushare_token')
        )
    
    def select_dragon_heads(self, date: str, top_n: int = 10) -> List[Dict]:
        """
        选择龙头股
        
        Args:
            date: 日期
            top_n: 返回前N只龙头
            
        Returns:
            龙头股列表
        """
        # 1. 获取市场数据
        market_data = self.data_loader.load_market_data(date)
        
        if not market_data or market_data.get('limit_up_count', 0) < self.config['sector_min_limit_up']:
            return []
        
        # 2. 获取涨停股票列表
        limit_up_stocks = market_data.get('limit_up_stocks', [])
        
        if not limit_up_stocks:
            return []
        
        # 3. 分析每只涨停股
        dragon_candidates = []
        
        for symbol in limit_up_stocks[:50]:  # 限制分析数量
            try:
                # 加载股票数据
                end_date = pd.to_datetime(date)
                start_date = end_date - pd.Timedelta(days=60)
                
                stock_data = self.data_loader.load_stock_data(
                    symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if stock_data.empty or len(stock_data) < 10:
                    continue
                
                # 计算龙头评分
                score = self._calculate_dragon_score(stock_data, symbol, date)
                
                if score > 0:
                    dragon_candidates.append({
                        'symbol': symbol,
                        'score': score,
                        'data': stock_data
                    })
                    
            except Exception as e:
                continue
        
        # 4. 按评分排序
        dragon_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return dragon_candidates[:top_n]
    
    def _calculate_dragon_score(self, data: pd.DataFrame, symbol: str, date: str) -> float:
        """
        计算龙头评分
        
        Args:
            data: 股票数据
            symbol: 股票代码
            date: 日期
            
        Returns:
            评分（0-100）
        """
        score = 0.0
        
        try:
            # 1. 连板数评分（最高30分）
            consecutive_limit_up = TechnicalIndicators.count_consecutive_limit_up(data)
            current_boards = consecutive_limit_up.iloc[-1]
            
            if current_boards >= self.config['dragon_min_limit_up_days']:
                score += min(current_boards * 10, 30)
            
            # 2. 成交量评分（最高25分）
            volume_ratio = TechnicalIndicators.calculate_volume_ratio(data, period=5)
            current_volume_ratio = volume_ratio.iloc[-1]
            
            if current_volume_ratio >= 2.0:
                score += min(current_volume_ratio * 5, 25)
            
            # 3. 资金流入评分（最高25分）
            money_flow = self.data_loader.load_money_flow(symbol, date)
            
            if money_flow:
                main_inflow_pct = money_flow.get('main_net_inflow_pct', 0)
                if main_inflow_pct > 0:
                    score += min(main_inflow_pct * 2.5, 25)
            
            # 4. 市值评分（最高10分）
            # 中小市值更容易成为龙头
            market_cap = data.get('market_cap', pd.Series([0])).iloc[-1] if 'market_cap' in data.columns else 0
            
            if self.config['min_market_cap'] <= market_cap / 1e8 <= self.config['max_market_cap']:
                # 市值在合理区间
                score += 10
            
            # 5. 趋势评分（最高10分）
            if TechnicalIndicators.is_uptrend(data, period=3).iloc[-1]:
                score += 10
            
        except Exception as e:
            pass
        
        return score
    
    def identify_hot_sectors(self, date: str, min_stocks: int = 3) -> List[Dict]:
        """
        识别热点板块
        
        Args:
            date: 日期
            min_stocks: 板块内最少股票数
            
        Returns:
            热点板块列表
        """
        try:
            # 获取板块数据
            sector_df = self.data_loader.load_sector_data(date)
            
            if sector_df.empty:
                return []
            
            # 获取市场涨停数据
            market_data = self.data_loader.load_market_data(date)
            limit_up_stocks = market_data.get('limit_up_stocks', [])
            
            # 分析每个板块
            hot_sectors = []
            
            for _, sector in sector_df.iterrows():
                sector_name = sector.get('板块名称', '')
                sector_stocks = sector.get('包含股票', [])
                
                if not sector_stocks or len(sector_stocks) < min_stocks:
                    continue
                
                # 计算板块内涨停股数量
                limit_up_count = len([s for s in sector_stocks if s in limit_up_stocks])
                
                if limit_up_count >= self.config['sector_min_limit_up']:
                    hot_sectors.append({
                        'name': sector_name,
                        'stocks': sector_stocks,
                        'limit_up_count': limit_up_count,
                        'total_stocks': len(sector_stocks),
                        'heat_score': limit_up_count / len(sector_stocks) * 100
                    })
            
            # 按热度排序
            hot_sectors.sort(key=lambda x: x['heat_score'], reverse=True)
            
            return hot_sectors
            
        except Exception as e:
            print(f"识别热点板块失败: {str(e)}")
            return []
    
    def select_sector_rotation_stocks(self, date: str, 
                                     main_sector: str,
                                     hedge_sector: str) -> List[str]:
        """
        选择板块轮动股票
        
        Args:
            date: 日期
            main_sector: 主线板块
            hedge_sector: 对冲板块
            
        Returns:
            股票代码列表
        """
        try:
            # 获取对冲板块的前排股票
            sector_df = self.data_loader.load_sector_data(date)
            
            # 查找对冲板块
            hedge_stocks = []
            
            for _, sector in sector_df.iterrows():
                if hedge_sector in sector.get('板块名称', ''):
                    hedge_stocks = sector.get('包含股票', [])[:5]  # 取前5只
                    break
            
            return hedge_stocks
            
        except Exception as e:
            print(f"选择轮动股票失败: {str(e)}")
            return []
    
    def filter_stocks(self, stock_list: List[str], date: str) -> List[Dict]:
        """
        过滤股票（基础筛选）
        
        Args:
            stock_list: 股票代码列表
            date: 日期
            
        Returns:
            过滤后的股票列表
        """
        filtered_stocks = []
        
        for symbol in stock_list:
            try:
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
                
                # 基础过滤条件
                latest = data.iloc[-1]
                
                # 1. 市值过滤
                market_cap = latest.get('market_cap', 0) / 1e8  # 转换为亿
                if not (self.config['min_market_cap'] <= market_cap <= self.config['max_market_cap']):
                    continue
                
                # 2. 换手率过滤
                turnover_rate = latest.get('turnover_rate', 0)
                if turnover_rate < self.config['min_turnover_rate']:
                    continue
                
                # 3. ST股票过滤
                name = latest.get('name', '')
                if 'ST' in name or '*ST' in name:
                    continue
                
                # 4. 连板数过滤
                consecutive_boards = TechnicalIndicators.count_consecutive_limit_up(data).iloc[-1]
                if consecutive_boards > self.config['chase_limit']:
                    continue
                
                filtered_stocks.append({
                    'symbol': symbol,
                    'data': data,
                    'market_cap': market_cap,
                    'turnover_rate': turnover_rate,
                    'consecutive_boards': consecutive_boards
                })
                
            except Exception as e:
                continue
        
        return filtered_stocks
    
    def rank_by_money_flow(self, stock_list: List[str], date: str, top_n: int = 10) -> List[str]:
        """
        按资金流入排名
        
        Args:
            stock_list: 股票代码列表
            date: 日期
            top_n: 返回前N只
            
        Returns:
            排序后的股票代码列表
        """
        stocks_with_flow = []
        
        for symbol in stock_list:
            try:
                money_flow = self.data_loader.load_money_flow(symbol, date)
                
                if money_flow:
                    main_inflow = money_flow.get('main_net_inflow', 0)
                    stocks_with_flow.append({
                        'symbol': symbol,
                        'main_inflow': main_inflow
                    })
            except Exception as e:
                continue
        
        # 按资金流入排序
        stocks_with_flow.sort(key=lambda x: x['main_inflow'], reverse=True)
        
        return [s['symbol'] for s in stocks_with_flow[:top_n]]

"""
IPO新股监控模块
专门监控新股反包机会
"""

import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from mancang.utils.indicators import TechnicalIndicators
from mancang.utils.data_loader import DataLoader


class IPOMonitor:
    """IPO新股监控器"""
    
    def __init__(self, config: Dict):
        """
        初始化IPO监控器
        
        Args:
            config: 策略配置字典
        """
        self.config = config
        self.data_loader = DataLoader(
            data_source=config.get('data_source', 'akshare'),
            token=config.get('tushare_token')
        )
        self.ipo_watchlist = []  # IPO观察列表
    
    def scan_ipo_opportunities(self, date: str, days: int = 30) -> List[Dict]:
        """
        扫描IPO机会
        
        Args:
            date: 当前日期
            days: 扫描最近N天内上市的新股
            
        Returns:
            IPO机会列表
        """
        # 1. 获取新股列表
        ipo_list = self.data_loader.load_ipo_list(days=days)
        
        if ipo_list.empty:
            return []
        
        opportunities = []
        current_date = pd.to_datetime(date)
        
        # 2. 分析每只新股
        for _, ipo in ipo_list.iterrows():
            symbol = ipo['symbol']
            list_date = ipo['list_date']
            
            # 计算上市天数
            days_since_ipo = (current_date - list_date).days
            
            # 检查是否在目标时间窗口
            if days_since_ipo < self.config['ipo_entry_day'] - 2:
                # 还未到时间窗口，加入观察列表
                self._add_to_watchlist(symbol, list_date)
                continue
            
            if days_since_ipo > self.config['ipo_entry_day'] + 3:
                # 已过时间窗口
                continue
            
            # 3. 加载股票数据
            try:
                start_date = list_date
                end_date = current_date
                
                stock_data = self.data_loader.load_stock_data(
                    symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if stock_data.empty or len(stock_data) < self.config['ipo_min_decline_days']:
                    continue
                
                # 4. 检测反包信号
                is_rebound, reason = TechnicalIndicators.detect_ipo_rebound(
                    stock_data,
                    list_date,
                    entry_day=self.config['ipo_entry_day'],
                    min_decline_days=self.config['ipo_min_decline_days']
                )
                
                if is_rebound:
                    # 5. 计算评分
                    score = self._calculate_ipo_score(stock_data, ipo)
                    
                    opportunities.append({
                        'symbol': symbol,
                        'name': ipo.get('name', ''),
                        'list_date': list_date,
                        'days_since_ipo': days_since_ipo,
                        'issue_price': ipo.get('issue_price', 0),
                        'current_price': stock_data['close'].iloc[-1],
                        'score': score,
                        'reason': reason,
                        'data': stock_data
                    })
                    
            except Exception as e:
                continue
        
        # 6. 按评分排序
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return opportunities
    
    def _calculate_ipo_score(self, data: pd.DataFrame, ipo_info: pd.Series) -> float:
        """
        计算IPO评分
        
        Args:
            data: 股票数据
            ipo_info: IPO信息
            
        Returns:
            评分（0-100）
        """
        score = 0.0
        
        try:
            latest = data.iloc[-1]
            
            # 1. 反包力度评分（最高30分）
            # 反包阳线越大，分数越高
            if len(data) >= 2:
                prev = data.iloc[-2]
                rebound_strength = (latest['close'] - prev['open']) / prev['open']
                score += min(rebound_strength * 100, 30)
            
            # 2. 下跌幅度评分（最高25分）
            # 从最高点下跌越多，反弹空间越大
            high_since_ipo = data['high'].max()
            decline_from_high = (high_since_ipo - latest['close']) / high_since_ipo
            score += min(decline_from_high * 100, 25)
            
            # 3. 量能评分（最高25分）
            volume_ratio = TechnicalIndicators.calculate_volume_ratio(data, period=min(5, len(data)))
            if len(volume_ratio) > 0:
                current_volume_ratio = volume_ratio.iloc[-1]
                if current_volume_ratio > 1.5:
                    score += min(current_volume_ratio * 10, 25)
            
            # 4. 相对发行价位置评分（最高20分）
            issue_price = ipo_info.get('issue_price', 0)
            if issue_price > 0:
                price_vs_issue = latest['close'] / issue_price
                if price_vs_issue < 1.5:  # 离发行价不太远
                    score += 20
                elif price_vs_issue < 2.0:
                    score += 10
            
        except Exception as e:
            pass
        
        return score
    
    def _add_to_watchlist(self, symbol: str, list_date: pd.Timestamp):
        """
        添加到观察列表
        
        Args:
            symbol: 股票代码
            list_date: 上市日期
        """
        # 避免重复添加
        if not any(item['symbol'] == symbol for item in self.ipo_watchlist):
            self.ipo_watchlist.append({
                'symbol': symbol,
                'list_date': list_date,
                'added_date': datetime.now()
            })
    
    def get_watchlist(self) -> List[Dict]:
        """
        获取观察列表
        
        Returns:
            观察列表
        """
        return self.ipo_watchlist
    
    def check_ipo_signal(self, symbol: str, date: str) -> Tuple[bool, str, float]:
        """
        检查单只IPO股票的信号
        
        Args:
            symbol: 股票代码
            date: 日期
            
        Returns:
            (是否有信号, 原因, 建议仓位)
        """
        try:
            # 获取IPO信息
            ipo_list = self.data_loader.load_ipo_list(days=60)
            ipo_info = ipo_list[ipo_list['symbol'] == symbol]
            
            if ipo_info.empty:
                return False, "非新股", 0.0
            
            list_date = ipo_info['list_date'].iloc[0]
            current_date = pd.to_datetime(date)
            days_since_ipo = (current_date - list_date).days
            
            # 检查时间窗口
            if days_since_ipo < self.config['ipo_entry_day'] - 2:
                return False, f"未到时间窗口（第{days_since_ipo}天）", 0.0
            
            if days_since_ipo > self.config['ipo_entry_day'] + 3:
                return False, "已过时间窗口", 0.0
            
            # 加载数据
            stock_data = self.data_loader.load_stock_data(
                symbol,
                list_date.strftime('%Y-%m-%d'),
                current_date.strftime('%Y-%m-%d')
            )
            
            if stock_data.empty:
                return False, "数据不足", 0.0
            
            # 检测反包信号
            is_rebound, reason = TechnicalIndicators.detect_ipo_rebound(
                stock_data,
                list_date,
                entry_day=self.config['ipo_entry_day'],
                min_decline_days=self.config['ipo_min_decline_days']
            )
            
            if not is_rebound:
                return False, reason, 0.0
            
            # 计算建议仓位
            score = self._calculate_ipo_score(stock_data, ipo_info.iloc[0])
            position_ratio = self.config['single_pos_limit'] * (score / 100)
            
            return True, "IPO反包信号", position_ratio
            
        except Exception as e:
            return False, f"检查失败: {str(e)}", 0.0
    
    def clean_watchlist(self, current_date: str):
        """
        清理过期的观察列表
        
        Args:
            current_date: 当前日期
        """
        current = pd.to_datetime(current_date)
        
        # 移除超过时间窗口的股票
        self.ipo_watchlist = [
            item for item in self.ipo_watchlist
            if (current - item['list_date']).days <= self.config['ipo_entry_day'] + 5
        ]
    
    def get_ipo_statistics(self) -> Dict:
        """
        获取IPO统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'watchlist_count': len(self.ipo_watchlist),
            'watchlist': self.ipo_watchlist
        }

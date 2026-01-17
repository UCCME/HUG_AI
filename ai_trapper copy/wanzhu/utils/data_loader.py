"""
数据加载模块
用于从不同数据源加载股票数据
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime, timedelta


class DataLoader:
    """数据加载器类"""
    
    def __init__(self, data_source: str = 'local'):
        """
        初始化数据加载器
        
        Args:
            data_source: 数据源类型 ('local', 'tushare', 'akshare'等)
        """
        self.data_source = data_source
        
    def load_stock_data(self, 
                       symbol: str, 
                       start_date: str, 
                       end_date: str,
                       fields: Optional[List[str]] = None) -> pd.DataFrame:
        """
        加载股票历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            fields: 需要的字段列表
            
        Returns:
            股票数据DataFrame
        """
        if self.data_source == 'local':
            return self._load_local_data(symbol, start_date, end_date)
        elif self.data_source == 'tushare':
            return self._load_tushare_data(symbol, start_date, end_date, fields)
        elif self.data_source == 'akshare':
            return self._load_akshare_data(symbol, start_date, end_date)
        else:
            raise ValueError(f"不支持的数据源: {self.data_source}")
    
    def _load_local_data(self, 
                        symbol: str, 
                        start_date: str, 
                        end_date: str) -> pd.DataFrame:
        """
        从本地文件加载数据（示例实现）
        
        Returns:
            模拟数据DataFrame
        """
        # 这里返回模拟数据，实际使用时应该从本地文件读取
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        np.random.seed(42)
        base_price = 100
        
        data = {
            'date': dates,
            'open': base_price + np.random.randn(len(dates)).cumsum() * 0.5,
            'high': base_price + np.random.randn(len(dates)).cumsum() * 0.5 + 1,
            'low': base_price + np.random.randn(len(dates)).cumsum() * 0.5 - 1,
            'close': base_price + np.random.randn(len(dates)).cumsum() * 0.5,
            'volume': np.random.randint(1000000, 10000000, len(dates)),
            'amount': np.random.randint(100000000, 1000000000, len(dates))
        }
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        return df
    
    def _load_tushare_data(self, 
                          symbol: str, 
                          start_date: str, 
                          end_date: str,
                          fields: Optional[List[str]] = None) -> pd.DataFrame:
        """
        从Tushare加载数据
        需要先安装tushare并配置token
        """
        try:
            import tushare as ts
            
            # 需要设置tushare token
            # ts.set_token('your_token_here')
            pro = ts.pro_api()
            
            df = pro.daily(
                ts_code=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                fields=fields
            )
            
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.set_index('trade_date').sort_index()
            
            return df
            
        except ImportError:
            raise ImportError("请先安装tushare: pip install tushare")
    
    def _load_akshare_data(self, 
                          symbol: str, 
                          start_date: str, 
                          end_date: str) -> pd.DataFrame:
        """
        从AKShare加载数据
        """
        try:
            import akshare as ak
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )
            
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            
            return df
            
        except ImportError:
            raise ImportError("请先安装akshare: pip install akshare")
    
    def load_market_data(self, 
                        date: str, 
                        market: str = 'all') -> pd.DataFrame:
        """
        加载市场所有股票的快照数据
        
        Args:
            date: 日期
            market: 市场类型 ('all', 'sh', 'sz')
            
        Returns:
            市场数据DataFrame
        """
        # 示例实现，实际应该从真实数据源获取
        symbols = [f"{i:06d}" for i in range(600000, 600100)]
        
        data = {
            'symbol': symbols,
            'name': [f"股票{i}" for i in range(len(symbols))],
            'close': np.random.uniform(10, 100, len(symbols)),
            'change_pct': np.random.uniform(-10, 10, len(symbols)),
            'volume': np.random.randint(1000000, 100000000, len(symbols)),
            'money_flow': np.random.uniform(-1e8, 1e8, len(symbols)),
            'market_cap': np.random.uniform(1e9, 1e11, len(symbols))
        }
        
        return pd.DataFrame(data)
    
    def load_sector_data(self, date: str) -> Dict[str, List[str]]:
        """
        加载板块数据
        
        Args:
            date: 日期
            
        Returns:
            板块到股票列表的字典
        """
        # 示例实现
        sectors = {
            '人工智能': ['600000', '600001', '600002'],
            '新能源': ['600010', '600011', '600012'],
            '芯片': ['600020', '600021', '600022'],
            '医药': ['600030', '600031', '600032']
        }
        
        return sectors
    
    def load_limit_up_stocks(self, date: str) -> pd.DataFrame:
        """
        加载涨停股票列表
        
        Args:
            date: 日期
            
        Returns:
            涨停股票DataFrame
        """
        # 示例实现
        data = {
            'symbol': ['600000', '600001', '600002'],
            'name': ['股票A', '股票B', '股票C'],
            'limit_up_time': ['09:30:00', '09:45:00', '10:00:00'],
            'open_count': [1, 3, 0],  # 炸板次数
            'sealed': [True, False, True]  # 是否封死
        }
        
        return pd.DataFrame(data)

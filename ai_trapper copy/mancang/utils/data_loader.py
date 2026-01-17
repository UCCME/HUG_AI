"""
数据加载模块
支持从多个数据源加载A股数据
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class DataLoader:
    """数据加载器类"""
    
    def __init__(self, data_source: str = 'akshare', token: Optional[str] = None):
        """
        初始化数据加载器
        
        Args:
            data_source: 数据源类型 ('akshare', 'tushare', 'custom')
            token: API token（如需要）
        """
        self.data_source = data_source
        self.token = token
        
        if data_source == 'tushare' and token:
            try:
                import tushare as ts
                ts.set_token(token)
                self.pro = ts.pro_api()
            except ImportError:
                raise ImportError("请安装 tushare: pip install tushare")
        elif data_source == 'akshare':
            try:
                import akshare as ak
                self.ak = ak
            except ImportError:
                raise ImportError("请安装 akshare: pip install akshare")
    
    def load_stock_data(self, 
                       symbol: str, 
                       start_date: str, 
                       end_date: str,
                       adjust: str = 'qfq') -> pd.DataFrame:
        """
        加载股票历史数据
        
        Args:
            symbol: 股票代码（如 '000001' 或 'sh000001'）
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            adjust: 复权类型 ('qfq'前复权, 'hfq'后复权, None不复权)
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        if self.data_source == 'akshare':
            return self._load_from_akshare(symbol, start_date, end_date, adjust)
        elif self.data_source == 'tushare':
            return self._load_from_tushare(symbol, start_date, end_date, adjust)
        else:
            raise ValueError(f"不支持的数据源: {self.data_source}")
    
    def _load_from_akshare(self, symbol: str, start_date: str, 
                          end_date: str, adjust: str) -> pd.DataFrame:
        """从AKShare加载数据"""
        try:
            # 处理股票代码格式
            if symbol.startswith('sh') or symbol.startswith('sz'):
                symbol = symbol[2:]
            
            # 加载数据
            df = self.ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust=adjust if adjust else ""
            )
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '换手率': 'turnover_rate'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            
            return df
            
        except Exception as e:
            raise Exception(f"AKShare加载数据失败: {str(e)}")
    
    def _load_from_tushare(self, symbol: str, start_date: str, 
                          end_date: str, adjust: str) -> pd.DataFrame:
        """从Tushare加载数据"""
        try:
            # 处理股票代码格式（Tushare格式：000001.SZ）
            if not ('.' in symbol):
                if symbol.startswith('6'):
                    ts_code = f"{symbol}.SH"
                else:
                    ts_code = f"{symbol}.SZ"
            else:
                ts_code = symbol
            
            # 加载数据
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            
            # 标准化列名
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume',
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.sort_index()
            
            return df
            
        except Exception as e:
            raise Exception(f"Tushare加载数据失败: {str(e)}")
    
    def load_market_data(self, date: str) -> Dict[str, Any]:
        """
        加载市场整体数据
        
        Args:
            date: 日期 'YYYY-MM-DD'
            
        Returns:
            市场数据字典
        """
        if self.data_source == 'akshare':
            try:
                # 获取涨跌停数据
                limit_up_df = self.ak.stock_zt_pool_em(date=date.replace('-', ''))
                limit_down_df = self.ak.stock_dt_pool_em(date=date.replace('-', ''))
                
                # 获取市场概况
                market_df = self.ak.stock_zh_a_spot_em()
                
                return {
                    'limit_up_count': len(limit_up_df),
                    'limit_down_count': len(limit_down_df),
                    'limit_up_stocks': limit_up_df['代码'].tolist() if not limit_up_df.empty else [],
                    'total_stocks': len(market_df),
                    'up_count': len(market_df[market_df['涨跌幅'] > 0]),
                    'down_count': len(market_df[market_df['涨跌幅'] < 0]),
                }
            except Exception as e:
                print(f"加载市场数据失败: {str(e)}")
                return {}
        else:
            return {}
    
    def load_sector_data(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        加载板块数据
        
        Args:
            date: 日期（可选）
            
        Returns:
            板块数据DataFrame
        """
        if self.data_source == 'akshare':
            try:
                # 获取板块行情
                sector_df = self.ak.stock_board_industry_name_em()
                return sector_df
            except Exception as e:
                print(f"加载板块数据失败: {str(e)}")
                return pd.DataFrame()
        else:
            return pd.DataFrame()
    
    def load_stock_list(self, market: str = 'all') -> pd.DataFrame:
        """
        加载股票列表
        
        Args:
            market: 市场类型 ('all', 'sh', 'sz', 'cyb', 'kcb')
            
        Returns:
            股票列表DataFrame
        """
        if self.data_source == 'akshare':
            try:
                df = self.ak.stock_zh_a_spot_em()
                
                # 标准化列名
                df = df.rename(columns={
                    '代码': 'symbol',
                    '名称': 'name',
                    '最新价': 'price',
                    '涨跌幅': 'pct_change',
                    '涨跌额': 'change',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '换手率': 'turnover_rate',
                    '市盈率': 'pe',
                    '市净率': 'pb',
                    '总市值': 'market_cap',
                    '流通市值': 'circulating_market_cap'
                })
                
                # 过滤市场
                if market != 'all':
                    if market == 'sh':
                        df = df[df['symbol'].str.startswith('6')]
                    elif market == 'sz':
                        df = df[df['symbol'].str.startswith('0')]
                    elif market == 'cyb':
                        df = df[df['symbol'].str.startswith('3')]
                    elif market == 'kcb':
                        df = df[df['symbol'].str.startswith('688')]
                
                return df
                
            except Exception as e:
                print(f"加载股票列表失败: {str(e)}")
                return pd.DataFrame()
        else:
            return pd.DataFrame()
    
    def load_ipo_list(self, days: int = 30) -> pd.DataFrame:
        """
        加载新股列表
        
        Args:
            days: 最近N天内上市的新股
            
        Returns:
            新股列表DataFrame
        """
        if self.data_source == 'akshare':
            try:
                # 获取新股数据
                ipo_df = self.ak.stock_zh_a_new_em()
                
                # 标准化列名
                ipo_df = ipo_df.rename(columns={
                    '股票代码': 'symbol',
                    '股票简称': 'name',
                    '上市日期': 'list_date',
                    '发行价格': 'issue_price',
                    '最新价': 'price',
                })
                
                # 转换日期
                ipo_df['list_date'] = pd.to_datetime(ipo_df['list_date'])
                
                # 过滤最近N天
                cutoff_date = datetime.now() - timedelta(days=days)
                ipo_df = ipo_df[ipo_df['list_date'] >= cutoff_date]
                
                return ipo_df
                
            except Exception as e:
                print(f"加载新股列表失败: {str(e)}")
                return pd.DataFrame()
        else:
            return pd.DataFrame()
    
    def load_money_flow(self, symbol: str, date: Optional[str] = None) -> Dict[str, float]:
        """
        加载资金流向数据
        
        Args:
            symbol: 股票代码
            date: 日期（可选）
            
        Returns:
            资金流向字典
        """
        if self.data_source == 'akshare':
            try:
                # 获取个股资金流
                df = self.ak.stock_individual_fund_flow_rank(indicator="今日")
                
                # 查找目标股票
                stock_data = df[df['代码'] == symbol]
                
                if not stock_data.empty:
                    return {
                        'main_net_inflow': float(stock_data['主力净流入-净额'].iloc[0]),
                        'main_net_inflow_pct': float(stock_data['主力净流入-净占比'].iloc[0]),
                        'super_large_net_inflow': float(stock_data['超大单净流入-净额'].iloc[0]),
                        'large_net_inflow': float(stock_data['大单净流入-净额'].iloc[0]),
                        'medium_net_inflow': float(stock_data['中单净流入-净额'].iloc[0]),
                        'small_net_inflow': float(stock_data['小单净流入-净额'].iloc[0]),
                    }
                else:
                    return {}
                    
            except Exception as e:
                print(f"加载资金流向失败: {str(e)}")
                return {}
        else:
            return {}
    
    def load_us_market_data(self) -> Dict[str, Any]:
        """
        加载美股市场数据（纳指、特斯拉、英伟达）
        
        Returns:
            美股数据字典
        """
        if self.data_source == 'akshare':
            try:
                # 获取美股指数
                nasdaq = self.ak.index_us_stock_sina(symbol=".IXIC")  # 纳斯达克
                
                return {
                    'nasdaq_close': float(nasdaq['close'].iloc[-1]) if not nasdaq.empty else 0,
                    'nasdaq_change': float(nasdaq['close'].iloc[-1] - nasdaq['close'].iloc[-2]) if len(nasdaq) > 1 else 0,
                }
            except Exception as e:
                print(f"加载美股数据失败: {str(e)}")
                return {}
        else:
            return {}

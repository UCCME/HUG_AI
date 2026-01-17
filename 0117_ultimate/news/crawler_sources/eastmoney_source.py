"""
东方财富数据源
个股研报、龙虎榜、大宗交易等数据中心
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


class EastMoneySource:
    """
    东方财富数据源
    
    核心价值：
    - 数据量最大
    - 涵盖A股所有公开数据
    - AJAX加载JSON数据
    - 无需解析HTML
    
    使用方式：
    直接抓包获取JSON数据
    """
    
    def __init__(self):
        """初始化东方财富数据源"""
        self.base_url = "http://www.eastmoney.com"
        self.api_url = "http://push2.eastmoney.com/api/qt"
        self.data_url = "http://data.eastmoney.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://data.eastmoney.com/'
        }
        print("✅ 东方财富数据源初始化成功")
    
    def get_longhubang(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取龙虎榜数据
        
        Args:
            date: 日期（YYYY-MM-DD）
            
        Returns:
            DataFrame: 龙虎榜数据
        """
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            url = f"{self.data_url}/DataCenter_V3/Stock2016/TradeDetail/pagesize=200,page=1,sortRule=-1,sortType=,startDate={date},endDate={date},gpfw=0,js=var data_tab_1.html"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                # 解析返回的JavaScript数据
                content = response.text
                if 'var data_tab_1=' in content:
                    # 提取JSON数据
                    import json
                    import re
                    
                    match = re.search(r'var data_tab_1=({.*?});', content)
                    if match:
                        data = json.loads(match.group(1))
                        if 'data' in data:
                            df = pd.DataFrame(data['data'])
                            print(f"✅ 获取到 {len(df)} 条龙虎榜数据")
                            return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取龙虎榜失败: {str(e)}")
            return pd.DataFrame()
    
    def get_block_trade(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取大宗交易数据
        
        Args:
            date: 日期（YYYY-MM-DD）
            
        Returns:
            DataFrame: 大宗交易数据
        """
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # 使用AkShare获取（更稳定）
            try:
                import akshare as ak
                df = ak.stock_dzjy_sctj(start_date=date.replace('-', ''), 
                                       end_date=date.replace('-', ''))
                if df is not None and not df.empty:
                    print(f"✅ 获取到 {len(df)} 条大宗交易数据")
                    return df
            except:
                pass
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取大宗交易失败: {str(e)}")
            return pd.DataFrame()
    
    def get_margin_trading(self, symbol: str) -> pd.DataFrame:
        """
        获取融资融券数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame: 融资融券数据
        """
        try:
            import akshare as ak
            df = ak.stock_margin_detail_em(symbol=symbol)
            if df is not None and not df.empty:
                print(f"✅ 获取到{symbol}融资融券数据")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取融资融券失败: {str(e)}")
            return pd.DataFrame()
    
    def get_institutional_research(self, symbol: str) -> pd.DataFrame:
        """
        获取机构调研数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame: 机构调研数据
        """
        try:
            import akshare as ak
            df = ak.stock_institute_research_em(symbol=symbol)
            if df is not None and not df.empty:
                print(f"✅ 获取到{symbol}机构调研数据")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取机构调研失败: {str(e)}")
            return pd.DataFrame()
    
    def get_hot_stocks_ranking(self) -> pd.DataFrame:
        """
        获取热门股票排行
        
        Returns:
            DataFrame: 热门股票数据
        """
        try:
            import akshare as ak
            df = ak.stock_hot_rank_em()
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 只热门股票")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取热门股票失败: {str(e)}")
            return pd.DataFrame()
    
    def get_stock_data_center(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取个股数据中心全部数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 包含所有数据的字典
        """
        print(f"\n{'='*60}")
        print(f"开始采集 {symbol} 的数据中心数据")
        print(f"{'='*60}\n")
        
        data = {
            'margin_trading': self.get_margin_trading(symbol),
            'institutional_research': self.get_institutional_research(symbol),
        }
        
        print(f"\n{'='*60}")
        print("数据采集完成")
        print(f"{'='*60}\n")
        
        return data
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': '东方财富',
            'type': '爬虫挖掘型',
            'features': [
                '数据量最大',
                '龙虎榜数据',
                '大宗交易',
                '融资融券',
                '机构调研'
            ],
            'data_quality': '⭐⭐⭐⭐',
            'update_frequency': '每日更新',
            'cost': '免费',
            'difficulty': '简单（AJAX JSON）',
            'best_for': '资金流向分析、机构行为追踪',
            'status': '已初始化'
        }

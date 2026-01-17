"""
AkShare 数据源
开源财经数据接口之王，封装了几十个网站的接口
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


class AkShareSource:
    """
    AkShare 数据源
    
    核心价值：
    - 开源免费
    - 数据源最全（封装了几十个网站）
    - 不需要维护爬虫
    - 接口统一规范
    
    使用方式：
    pip install akshare
    """
    
    def __init__(self):
        """初始化 AkShare 数据源"""
        self.ak = None
        self._init_api()
    
    def _init_api(self):
        """初始化 AkShare"""
        try:
            import akshare as ak
            self.ak = ak
            print("✅ AkShare 初始化成功")
        except ImportError:
            print("❌ 请先安装 akshare: pip install akshare")
            self.ak = None
    
    def get_stock_news(self, symbol: str) -> pd.DataFrame:
        """
        获取个股新闻（东方财富）
        
        Args:
            symbol: 股票代码（如：600893）
            
        Returns:
            DataFrame: 新闻数据
        """
        if self.ak is None:
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_news_em(symbol=symbol)
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 条{symbol}新闻")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取新闻失败: {str(e)}")
            return pd.DataFrame()
    
    def get_announcements(self, symbol: str) -> pd.DataFrame:
        """
        获取公司公告
        
        Args:
            symbol: 股票名称（如：航发动力）
            
        Returns:
            DataFrame: 公告数据
        """
        if self.ak is None:
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_notice_report(symbol=symbol)
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 条{symbol}公告")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取公告失败: {str(e)}")
            return pd.DataFrame()
    
    def get_research_reports(self, symbol: str) -> pd.DataFrame:
        """
        获取研报评级
        
        Args:
            symbol: 股票代码（如：600893）
            
        Returns:
            DataFrame: 研报数据
        """
        if self.ak is None:
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_research_report_em(symbol=symbol)
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 条{symbol}研报")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取研报失败: {str(e)}")
            return pd.DataFrame()
    
    def get_fund_flow(self, symbol: str, market: str = "sh") -> pd.DataFrame:
        """
        获取资金流向
        
        Args:
            symbol: 股票代码
            market: 市场（sh/sz）
            
        Returns:
            DataFrame: 资金流向数据
        """
        if self.ak is None:
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_individual_fund_flow(symbol=symbol, market=market)
            if df is not None and not df.empty:
                print(f"✅ 获取到{symbol}资金流向数据")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取资金流向失败: {str(e)}")
            return pd.DataFrame()
    
    def get_hsgt_flow(self, symbol: str) -> pd.DataFrame:
        """
        获取北向资金流向
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame: 北向资金数据
        """
        if self.ak is None:
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_hsgt_individual_em(symbol=symbol)
            if df is not None and not df.empty:
                print(f"✅ 获取到{symbol}北向资金数据")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取北向资金失败: {str(e)}")
            return pd.DataFrame()
    
    def get_guba_sentiment(self, symbol: str) -> pd.DataFrame:
        """
        获取股吧情绪
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame: 股吧数据
        """
        if self.ak is None:
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_comment_em(symbol=symbol)
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 条{symbol}股吧帖子")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取股吧数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_hot_stocks(self) -> pd.DataFrame:
        """
        获取热门股票
        
        Returns:
            DataFrame: 热门股票数据
        """
        if self.ak is None:
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_hot_rank_em()
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 只热门股票")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取热门股票失败: {str(e)}")
            return pd.DataFrame()
    
    def get_stock_info(self, symbol: str) -> pd.DataFrame:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame: 股票信息
        """
        if self.ak is None:
            return pd.DataFrame()
        
        try:
            df = self.ak.stock_individual_info_em(symbol=symbol)
            if df is not None and not df.empty:
                print(f"✅ 获取到{symbol}基本信息")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取股票信息失败: {str(e)}")
            return pd.DataFrame()
    
    def get_all_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取个股所有数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 包含所有数据的字典
        """
        print(f"\n{'='*60}")
        print(f"开始采集 {symbol} 的所有数据")
        print(f"{'='*60}\n")
        
        # 获取股票信息
        info_df = self.get_stock_info(symbol)
        stock_name = ""
        if not info_df.empty:
            stock_name = info_df.loc[info_df['item'] == '股票简称', 'value'].values[0]
        
        # 判断市场
        market = "sh" if symbol.startswith('6') else "sz"
        
        data = {
            'info': info_df,
            'news': self.get_stock_news(symbol),
            'announcements': self.get_announcements(stock_name) if stock_name else pd.DataFrame(),
            'research_reports': self.get_research_reports(symbol),
            'fund_flow': self.get_fund_flow(symbol, market),
            'hsgt_flow': self.get_hsgt_flow(symbol),
            'guba_sentiment': self.get_guba_sentiment(symbol)
        }
        
        print(f"\n{'='*60}")
        print("数据采集完成")
        print(f"{'='*60}\n")
        
        return data
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': 'AkShare',
            'type': 'API直达型',
            'features': [
                '开源免费',
                '数据源最全',
                '接口统一',
                '无需维护爬虫'
            ],
            'data_quality': '⭐⭐⭐⭐',
            'update_frequency': '实时',
            'cost': '完全免费',
            'difficulty': '非常简单',
            'status': '已初始化' if self.ak else '未初始化'
        }

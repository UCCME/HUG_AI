"""
Tushare Pro 数据源
提供官方新闻联播摘要和财经快讯
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


class TushareSource:
    """
    Tushare Pro 数据源
    
    核心价值：
    - 结构化最强的金融数据
    - 官方新闻联播摘要（cctv_news）
    - 主要财经网站快讯
    
    使用方式：
    1. 注册 Tushare Pro 账号：https://tushare.pro/register
    2. 获取 Token
    3. 初始化时传入 Token
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化 Tushare 数据源
        
        Args:
            token: Tushare Pro Token（可选，如果已设置环境变量）
        """
        self.token = token
        self.pro = None
        self._init_api()
    
    def _init_api(self):
        """初始化 Tushare API"""
        try:
            import tushare as ts
            
            if self.token:
                ts.set_token(self.token)
            
            self.pro = ts.pro_api()
            print("✅ Tushare Pro 初始化成功")
            
        except ImportError:
            print("❌ 请先安装 tushare: pip install tushare")
            self.pro = None
        except Exception as e:
            print(f"❌ Tushare 初始化失败: {str(e)}")
            print("提示：请确保已设置正确的 Token")
            self.pro = None
    
    def get_cctv_news(self, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取新闻联播摘要
        
        Args:
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            
        Returns:
            DataFrame: 新闻联播数据
        """
        if self.pro is None:
            print("❌ Tushare 未初始化")
            return pd.DataFrame()
        
        try:
            # 默认获取最近7天
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            
            df = self.pro.cctv_news(start_date=start_date, end_date=end_date)
            
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 条新闻联播")
                return df
            else:
                print("⚠️  未获取到新闻联播数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 获取新闻联播失败: {str(e)}")
            return pd.DataFrame()
    
    def get_news(self, src: str = 'sina', start_date: Optional[str] = None,
                 end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取财经新闻
        
        Args:
            src: 新闻源（sina/wallstreetcn/10jqka/eastmoney/yuncaijing）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            
        Returns:
            DataFrame: 新闻数据
        """
        if self.pro is None:
            print("❌ Tushare 未初始化")
            return pd.DataFrame()
        
        try:
            # 默认获取最近7天
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            
            df = self.pro.news(src=src, start_date=start_date, end_date=end_date)
            
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 条{src}新闻")
                return df
            else:
                print(f"⚠️  未获取到{src}新闻数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 获取新闻失败: {str(e)}")
            return pd.DataFrame()
    
    def get_major_news(self, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取重大新闻（新闻联播）
        
        这是最权威的消息源，适合做事件驱动策略
        
        Returns:
            DataFrame: 重大新闻数据
        """
        return self.get_cctv_news(start_date, end_date)
    
    def search_news(self, keyword: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
        """
        搜索包含关键词的新闻
        
        Args:
            keyword: 搜索关键词
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 搜索结果
        """
        # 获取所有新闻源的数据
        sources = ['sina', 'wallstreetcn', '10jqka', 'eastmoney']
        all_news = []
        
        for src in sources:
            df = self.get_news(src, start_date, end_date)
            if not df.empty:
                all_news.append(df)
        
        if not all_news:
            return pd.DataFrame()
        
        # 合并所有新闻
        combined = pd.concat(all_news, ignore_index=True)
        
        # 搜索关键词
        if 'title' in combined.columns:
            mask = combined['title'].str.contains(keyword, case=False, na=False)
            result = combined[mask]
            print(f"✅ 找到 {len(result)} 条包含'{keyword}'的新闻")
            return result
        
        return pd.DataFrame()
    
    def get_summary(self) -> Dict:
        """
        获取数据源摘要信息
        
        Returns:
            Dict: 摘要信息
        """
        return {
            'source': 'Tushare Pro',
            'type': 'API直达型',
            'features': [
                '官方新闻联播摘要',
                '多源财经快讯',
                '结构化数据',
                '适合NLP训练'
            ],
            'data_quality': '⭐⭐⭐⭐⭐',
            'update_frequency': '实时',
            'cost': '免费（有积分限制）',
            'difficulty': '简单',
            'status': '已初始化' if self.pro else '未初始化'
        }

"""
东方财富股吧数据源
散户评论、情绪宣泄、热度监控
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


class GubaSource:
    """
    东方财富股吧数据源
    
    核心价值：
    - 反向指标
    - 热度监控
    - 散户情绪
    - 发帖频率统计
    
    使用方式：
    需要处理反爬，统计发帖频率和阅读量
    """
    
    def __init__(self):
        """初始化股吧数据源"""
        self.base_url = "http://guba.eastmoney.com"
        self.api_url = "http://guba.eastmoney.com/list"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://guba.eastmoney.com/'
        }
        print("✅ 股吧数据源初始化成功")
    
    def get_posts(self, symbol: str, page: int = 1) -> pd.DataFrame:
        """
        获取股吧帖子
        
        Args:
            symbol: 股票代码
            page: 页码
            
        Returns:
            DataFrame: 帖子数据
        """
        try:
            # 优先使用AkShare
            import akshare as ak
            df = ak.stock_comment_em(symbol=symbol)
            
            if df is not None and not df.empty:
                print(f"✅ 获取到 {len(df)} 条{symbol}股吧帖子")
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取股吧帖子失败: {str(e)}")
            return pd.DataFrame()
    
    def get_hot_posts(self, symbol: str, limit: int = 50) -> pd.DataFrame:
        """
        获取热门帖子
        
        Args:
            symbol: 股票代码
            limit: 获取数量
            
        Returns:
            DataFrame: 热门帖子
        """
        df = self.get_posts(symbol)
        
        if df.empty:
            return pd.DataFrame()
        
        # 按阅读量或评论数排序
        if '阅读' in df.columns:
            hot = df.nlargest(limit, '阅读')
            print(f"✅ 筛选出 {len(hot)} 条热门帖子")
            return hot
        elif '评论' in df.columns:
            hot = df.nlargest(limit, '评论')
            print(f"✅ 筛选出 {len(hot)} 条热门帖子")
            return hot
        
        return df.head(limit)
    
    def calculate_heat_score(self, symbol: str) -> Dict:
        """
        计算股吧热度得分
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 热度分析结果
        """
        df = self.get_posts(symbol)
        
        result = {
            'symbol': symbol,
            'total_posts': 0,
            'total_views': 0,
            'total_comments': 0,
            'avg_views': 0,
            'avg_comments': 0,
            'heat_level': 'low',
            'sentiment': 'neutral'
        }
        
        if df.empty:
            return result
        
        result['total_posts'] = len(df)
        
        if '阅读' in df.columns:
            result['total_views'] = df['阅读'].sum()
            result['avg_views'] = df['阅读'].mean()
        
        if '评论' in df.columns:
            result['total_comments'] = df['评论'].sum()
            result['avg_comments'] = df['评论'].mean()
        
        # 计算热度等级
        if result['avg_views'] > 10000:
            result['heat_level'] = 'very_high'
        elif result['avg_views'] > 5000:
            result['heat_level'] = 'high'
        elif result['avg_views'] > 2000:
            result['heat_level'] = 'medium'
        else:
            result['heat_level'] = 'low'
        
        # 简单情绪分析（基于标题关键词）
        if '标题' in df.columns:
            positive_keywords = ['涨', '牛', '利好', '突破', '上涨', '看好']
            negative_keywords = ['跌', '熊', '利空', '下跌', '看空', '割肉']
            
            positive_count = 0
            negative_count = 0
            
            for title in df['标题']:
                for keyword in positive_keywords:
                    if keyword in str(title):
                        positive_count += 1
                        break
                for keyword in negative_keywords:
                    if keyword in str(title):
                        negative_count += 1
                        break
            
            if positive_count > negative_count * 1.5:
                result['sentiment'] = 'bullish'
            elif negative_count > positive_count * 1.5:
                result['sentiment'] = 'bearish'
        
        return result
    
    def monitor_posting_frequency(self, symbol: str, hours: int = 24) -> Dict:
        """
        监控发帖频率
        
        Args:
            symbol: 股票代码
            hours: 监控时间范围（小时）
            
        Returns:
            Dict: 发帖频率分析
        """
        df = self.get_posts(symbol)
        
        result = {
            'symbol': symbol,
            'time_range_hours': hours,
            'total_posts': 0,
            'posts_per_hour': 0,
            'is_abnormal': False,
            'trend': 'stable'
        }
        
        if df.empty:
            return result
        
        result['total_posts'] = len(df)
        result['posts_per_hour'] = len(df) / hours
        
        # 判断是否异常（发帖频率过高）
        if result['posts_per_hour'] > 50:  # 每小时超过50条
            result['is_abnormal'] = True
            result['trend'] = 'surging'
        elif result['posts_per_hour'] > 20:
            result['trend'] = 'increasing'
        elif result['posts_per_hour'] < 5:
            result['trend'] = 'decreasing'
        
        return result
    
    def get_sentiment_indicator(self, symbol: str) -> Dict:
        """
        获取情绪指标（反向指标）
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 情绪指标
        """
        heat = self.calculate_heat_score(symbol)
        freq = self.monitor_posting_frequency(symbol)
        
        indicator = {
            'symbol': symbol,
            'heat_level': heat['heat_level'],
            'sentiment': heat['sentiment'],
            'posting_frequency': freq['posts_per_hour'],
            'is_overheated': False,
            'signal': 'hold',
            'reason': ''
        }
        
        # 反向指标逻辑
        if (heat['heat_level'] == 'very_high' and 
            heat['sentiment'] == 'bullish' and 
            freq['is_abnormal']):
            indicator['is_overheated'] = True
            indicator['signal'] = 'sell'  # 反向指标：过度乐观时卖出
            indicator['reason'] = '散户过度乐观，热度异常，建议反向操作'
        
        elif (heat['heat_level'] == 'low' and 
              heat['sentiment'] == 'bearish'):
            indicator['signal'] = 'buy'  # 反向指标：过度悲观时买入
            indicator['reason'] = '散户过度悲观，可能是底部信号'
        
        else:
            indicator['reason'] = '情绪正常，无明确信号'
        
        return indicator
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': '东方财富股吧',
            'type': '爬虫挖掘型',
            'features': [
                '散户情绪',
                '反向指标',
                '热度监控',
                '发帖频率'
            ],
            'data_quality': '⭐⭐⭐',
            'update_frequency': '实时',
            'cost': '免费',
            'difficulty': '中等（需处理反爬）',
            'best_for': '反向指标、情绪监控、热度追踪',
            'status': '已初始化'
        }

"""
华尔街见闻数据源
深度宏观、深度文章、精华资讯
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


class WallstreetCNSource:
    """
    华尔街见闻数据源
    
    核心价值：
    - 编辑筛选过的"大新闻"
    - 质量高、噪音少
    - 深度宏观分析
    - 重磅资讯标记
    
    使用方式：
    抓取文章列表API，关注"重磅"或"VIP"标记
    """
    
    def __init__(self):
        """初始化华尔街见闻数据源"""
        self.base_url = "https://wallstreetcn.com"
        self.api_url = "https://api-one-wscn.awtmt.com/apiv1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://wallstreetcn.com/'
        }
        print("✅ 华尔街见闻数据源初始化成功")
    
    def get_news_flash(self, limit: int = 100) -> pd.DataFrame:
        """
        获取快讯
        
        Args:
            limit: 获取数量
            
        Returns:
            DataFrame: 快讯数据
        """
        try:
            url = f"{self.api_url}/content/lives"
            params = {
                'channel': 'global-channel',
                'client': 'web',
                'limit': limit,
                'accept': 'live'
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'items' in data['data']:
                    items = data['data']['items']
                    
                    records = []
                    for item in items:
                        record = {
                            'id': item.get('id'),
                            'title': item.get('title', ''),
                            'content': item.get('content_text', ''),
                            'display_time': item.get('display_time'),
                            'importance': item.get('importance', 0),
                            'uri': item.get('uri', ''),
                            'tags': ','.join([tag.get('name', '') for tag in item.get('tags', [])])
                        }
                        records.append(record)
                    
                    df = pd.DataFrame(records)
                    print(f"✅ 获取到 {len(df)} 条华尔街见闻快讯")
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取快讯失败: {str(e)}")
            return pd.DataFrame()
    
    def get_articles(self, limit: int = 50, category: str = 'all') -> pd.DataFrame:
        """
        获取深度文章
        
        Args:
            limit: 获取数量
            category: 分类（all/global/a-stock/us-stock等）
            
        Returns:
            DataFrame: 文章数据
        """
        try:
            url = f"{self.api_url}/content/articles"
            params = {
                'channel': f'{category}-channel' if category != 'all' else 'global-channel',
                'client': 'web',
                'limit': limit,
                'accept': 'article'
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'items' in data['data']:
                    items = data['data']['items']
                    
                    records = []
                    for item in items:
                        record = {
                            'id': item.get('id'),
                            'title': item.get('title', ''),
                            'summary': item.get('summary', ''),
                            'display_time': item.get('display_time'),
                            'author': item.get('author', {}).get('display_name', ''),
                            'is_vip': item.get('is_vip', False),
                            'is_priced': item.get('is_priced', False),
                            'uri': item.get('uri', ''),
                            'image': item.get('image_uri', '')
                        }
                        records.append(record)
                    
                    df = pd.DataFrame(records)
                    print(f"✅ 获取到 {len(df)} 篇华尔街见闻文章")
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取文章失败: {str(e)}")
            return pd.DataFrame()
    
    def get_important_news(self, limit: int = 50) -> pd.DataFrame:
        """
        获取重要新闻（筛选重磅内容）
        
        Args:
            limit: 获取数量
            
        Returns:
            DataFrame: 重要新闻
        """
        # 获取快讯
        flash_df = self.get_news_flash(limit)
        
        # 获取文章
        article_df = self.get_articles(limit)
        
        important_items = []
        
        # 筛选重要快讯（importance >= 5）
        if not flash_df.empty and 'importance' in flash_df.columns:
            important_flash = flash_df[flash_df['importance'] >= 5]
            for _, row in important_flash.iterrows():
                important_items.append({
                    'type': '快讯',
                    'title': row['title'],
                    'content': row.get('content', ''),
                    'time': row['display_time'],
                    'importance': row['importance'],
                    'source': '华尔街见闻'
                })
        
        # 筛选VIP文章
        if not article_df.empty and 'is_vip' in article_df.columns:
            vip_articles = article_df[article_df['is_vip'] == True]
            for _, row in vip_articles.iterrows():
                important_items.append({
                    'type': 'VIP文章',
                    'title': row['title'],
                    'content': row.get('summary', ''),
                    'time': row['display_time'],
                    'author': row.get('author', ''),
                    'source': '华尔街见闻'
                })
        
        if important_items:
            result = pd.DataFrame(important_items)
            print(f"✅ 筛选出 {len(result)} 条重要新闻")
            return result
        
        return pd.DataFrame()
    
    def search_by_keyword(self, keyword: str, limit: int = 50) -> pd.DataFrame:
        """
        按关键词搜索
        
        Args:
            keyword: 搜索关键词
            limit: 获取数量
            
        Returns:
            DataFrame: 搜索结果
        """
        # 获取快讯和文章
        flash_df = self.get_news_flash(limit)
        article_df = self.get_articles(limit)
        
        results = []
        
        # 搜索快讯
        if not flash_df.empty:
            mask = (flash_df['title'].str.contains(keyword, case=False, na=False) |
                   flash_df['content'].str.contains(keyword, case=False, na=False))
            matched = flash_df[mask]
            for _, row in matched.iterrows():
                results.append({
                    'type': '快讯',
                    'title': row['title'],
                    'content': row.get('content', ''),
                    'time': row['display_time']
                })
        
        # 搜索文章
        if not article_df.empty:
            mask = (article_df['title'].str.contains(keyword, case=False, na=False) |
                   article_df['summary'].str.contains(keyword, case=False, na=False))
            matched = article_df[mask]
            for _, row in matched.iterrows():
                results.append({
                    'type': '文章',
                    'title': row['title'],
                    'content': row.get('summary', ''),
                    'time': row['display_time']
                })
        
        if results:
            result_df = pd.DataFrame(results)
            print(f"✅ 找到 {len(result_df)} 条包含'{keyword}'的内容")
            return result_df
        
        return pd.DataFrame()
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': '华尔街见闻',
            'type': '爬虫挖掘型',
            'features': [
                '编辑筛选的大新闻',
                '质量高噪音少',
                '深度宏观分析',
                'VIP重磅标记'
            ],
            'data_quality': '⭐⭐⭐⭐⭐',
            'update_frequency': '实时',
            'cost': '部分免费（VIP内容收费）',
            'difficulty': '中等',
            'best_for': '宏观分析、大事件捕捉、深度研究',
            'status': '已初始化'
        }

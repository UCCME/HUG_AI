"""
财联社数据源
A股最快的短快讯（电报）
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
import warnings
warnings.filterwarnings('ignore')


class CLSSource:
    """
    财联社数据源
    
    核心价值：
    - A股最快的快讯
    - 包含涨停分析、题材预测
    - JSON格式清晰
    - 适合轮询抓取
    
    使用方式：
    直接抓取 Web API（JSON格式）
    """
    
    def __init__(self):
        """初始化财联社数据源"""
        self.base_url = "https://www.cls.cn"
        self.api_url = "https://www.cls.cn/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.cls.cn/',
            'Accept': 'application/json'
        }
        print("✅ 财联社数据源初始化成功")
    
    def get_telegraph(self, limit: int = 100) -> pd.DataFrame:
        """
        获取财联社电报（快讯）
        
        Args:
            limit: 获取数量
            
        Returns:
            DataFrame: 电报数据
        """
        try:
            url = f"{self.api_url}/telegraph/list"
            params = {
                'app': 'CailianpressWeb',
                'category': 'telegram',
                'last_time': '',
                'limit': limit,
                'os': 'web',
                'refresh_type': 1,
                'rn': limit,
                'sv': '7.7.5'
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'roll_data' in data['data']:
                    items = data['data']['roll_data']
                    
                    # 解析数据
                    records = []
                    for item in items:
                        record = {
                            'id': item.get('id'),
                            'title': item.get('title', ''),
                            'content': item.get('content', ''),
                            'ctime': item.get('ctime', ''),
                            'brief': item.get('brief', ''),
                            'level': item.get('level', 0),  # 重要程度
                            'stock_list': item.get('stock_list', [])  # 相关股票
                        }
                        records.append(record)
                    
                    df = pd.DataFrame(records)
                    print(f"✅ 获取到 {len(df)} 条财联社电报")
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取财联社电报失败: {str(e)}")
            return pd.DataFrame()
    
    def get_important_news(self, limit: int = 50) -> pd.DataFrame:
        """
        获取重要快讯
        
        筛选重要程度高的快讯
        
        Args:
            limit: 获取数量
            
        Returns:
            DataFrame: 重要快讯
        """
        df = self.get_telegraph(limit)
        
        if df.empty:
            return pd.DataFrame()
        
        # 筛选重要快讯（level >= 2）
        if 'level' in df.columns:
            important = df[df['level'] >= 2]
            print(f"✅ 筛选出 {len(important)} 条重要快讯")
            return important
        
        return df
    
    def get_stock_related_news(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        获取个股相关快讯
        
        Args:
            symbol: 股票代码（如：600893）
            limit: 获取数量
            
        Returns:
            DataFrame: 相关快讯
        """
        df = self.get_telegraph(limit)
        
        if df.empty:
            return pd.DataFrame()
        
        # 筛选包含该股票的快讯
        if 'stock_list' in df.columns:
            mask = df['stock_list'].apply(
                lambda x: any(symbol in str(stock) for stock in x) if x else False
            )
            related = df[mask]
            print(f"✅ 找到 {len(related)} 条{symbol}相关快讯")
            return related
        
        # 如果没有stock_list字段，通过内容搜索
        if 'content' in df.columns:
            mask = df['content'].str.contains(symbol, case=False, na=False)
            related = df[mask]
            print(f"✅ 找到 {len(related)} 条{symbol}相关快讯")
            return related
        
        return pd.DataFrame()
    
    def get_sector_news(self, sector: str, limit: int = 100) -> pd.DataFrame:
        """
        获取板块相关快讯
        
        Args:
            sector: 板块名称（如：航空航天、新能源）
            limit: 获取数量
            
        Returns:
            DataFrame: 板块快讯
        """
        df = self.get_telegraph(limit)
        
        if df.empty:
            return pd.DataFrame()
        
        # 通过标题和内容搜索
        if 'title' in df.columns and 'content' in df.columns:
            mask = (df['title'].str.contains(sector, case=False, na=False) |
                   df['content'].str.contains(sector, case=False, na=False))
            related = df[mask]
            print(f"✅ 找到 {len(related)} 条{sector}板块快讯")
            return related
        
        return pd.DataFrame()
    
    def search_keywords(self, keywords: List[str], limit: int = 100) -> pd.DataFrame:
        """
        搜索包含关键词的快讯
        
        Args:
            keywords: 关键词列表
            limit: 获取数量
            
        Returns:
            DataFrame: 搜索结果
        """
        df = self.get_telegraph(limit)
        
        if df.empty:
            return pd.DataFrame()
        
        # 搜索关键词
        if 'content' in df.columns:
            mask = pd.Series([False] * len(df))
            for keyword in keywords:
                mask |= df['content'].str.contains(keyword, case=False, na=False)
            
            result = df[mask]
            print(f"✅ 找到 {len(result)} 条包含关键词的快讯")
            return result
        
        return pd.DataFrame()
    
    def monitor_realtime(self, callback=None, interval: int = 60):
        """
        实时监控快讯
        
        Args:
            callback: 回调函数，接收新快讯
            interval: 轮询间隔（秒）
        """
        import time
        
        last_id = None
        print(f"🔄 开始实时监控财联社快讯（间隔{interval}秒）")
        print("按 Ctrl+C 停止监控")
        
        try:
            while True:
                df = self.get_telegraph(limit=20)
                
                if not df.empty and 'id' in df.columns:
                    # 获取最新的快讯
                    current_id = df.iloc[0]['id']
                    
                    if last_id is not None and current_id != last_id:
                        # 有新快讯
                        new_items = df[df['id'] > last_id]
                        
                        for _, item in new_items.iterrows():
                            print(f"\n🔔 新快讯: {item['title']}")
                            print(f"   内容: {item.get('brief', item.get('content', ''))[:100]}")
                            print(f"   时间: {item['ctime']}")
                            
                            if callback:
                                callback(item)
                    
                    last_id = current_id
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  停止监控")
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': '财联社',
            'type': 'API直达型',
            'features': [
                'A股最快快讯',
                '涨停分析',
                '题材预测',
                'JSON格式清晰'
            ],
            'data_quality': '⭐⭐⭐⭐⭐',
            'update_frequency': '实时（秒级）',
            'cost': '免费',
            'difficulty': '简单',
            'best_for': '短线交易、题材炒作、实时监控',
            'status': '已初始化'
        }

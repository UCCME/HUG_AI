"""
雪球数据源
深度逻辑讨论、大V观点、聪明钱情绪
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


class XueqiuSource:
    """
    雪球数据源
    
    核心价值：
    - 聪明钱的情绪
    - 深度逻辑讨论
    - 大V观点
    - 专业用户更多
    
    使用方式：
    需要处理Cookie和Headers
    """
    
    def __init__(self):
        """初始化雪球数据源"""
        self.base_url = "https://xueqiu.com"
        self.api_url = "https://stock.xueqiu.com/v5/stock"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://xueqiu.com/',
            'Accept': 'application/json'
        }
        self.cookies = {}
        print("✅ 雪球数据源初始化成功")
        print("⚠️  注意：雪球需要Cookie认证，部分功能可能受限")
    
    def _get_token(self):
        """获取访问Token"""
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                self.cookies = response.cookies.get_dict()
                return True
            return False
        except:
            return False
    
    def get_hot_discussions(self, symbol: str, count: int = 20) -> pd.DataFrame:
        """
        获取热门讨论
        
        Args:
            symbol: 股票代码（如：SH600893）
            count: 获取数量
            
        Returns:
            DataFrame: 讨论数据
        """
        try:
            # 确保有token
            if not self.cookies:
                self._get_token()
            
            url = f"{self.api_url}/hot_stock/list.json"
            params = {
                'symbol': symbol,
                'count': count,
                'comment': 0
            }
            
            response = requests.get(url, params=params, headers=self.headers, 
                                  cookies=self.cookies, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'items' in data['data']:
                    items = data['data']['items']
                    
                    records = []
                    for item in items:
                        record = {
                            'id': item.get('id'),
                            'title': item.get('title', ''),
                            'text': item.get('text', ''),
                            'created_at': item.get('created_at'),
                            'user_name': item.get('user', {}).get('screen_name', ''),
                            'user_followers': item.get('user', {}).get('followers_count', 0),
                            'like_count': item.get('like_count', 0),
                            'reply_count': item.get('reply_count', 0),
                            'retweet_count': item.get('retweet_count', 0)
                        }
                        records.append(record)
                    
                    df = pd.DataFrame(records)
                    print(f"✅ 获取到 {len(df)} 条{symbol}雪球讨论")
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取雪球讨论失败: {str(e)}")
            return pd.DataFrame()
    
    def get_big_v_opinions(self, symbol: str) -> pd.DataFrame:
        """
        获取大V观点
        
        筛选粉丝数多的用户的讨论
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame: 大V观点
        """
        df = self.get_hot_discussions(symbol, count=50)
        
        if df.empty:
            return pd.DataFrame()
        
        # 筛选粉丝数 > 10000 的用户
        if 'user_followers' in df.columns:
            big_v = df[df['user_followers'] > 10000]
            print(f"✅ 筛选出 {len(big_v)} 条大V观点")
            return big_v
        
        return df
    
    def analyze_sentiment(self, symbol: str) -> Dict:
        """
        分析雪球情绪
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 情绪分析结果
        """
        df = self.get_hot_discussions(symbol, count=100)
        
        result = {
            'symbol': symbol,
            'total_discussions': 0,
            'avg_likes': 0,
            'avg_replies': 0,
            'sentiment_score': 0.5,
            'sentiment': 'neutral',
            'quality_score': 0,
            'big_v_ratio': 0
        }
        
        if df.empty:
            return result
        
        result['total_discussions'] = len(df)
        
        if 'like_count' in df.columns:
            result['avg_likes'] = df['like_count'].mean()
        
        if 'reply_count' in df.columns:
            result['avg_replies'] = df['reply_count'].mean()
        
        # 质量得分（基于互动数据）
        if result['avg_likes'] > 0 and result['avg_replies'] > 0:
            result['quality_score'] = (result['avg_likes'] + result['avg_replies'] * 2) / 3
        
        # 大V占比
        if 'user_followers' in df.columns:
            big_v_count = len(df[df['user_followers'] > 10000])
            result['big_v_ratio'] = big_v_count / len(df) if len(df) > 0 else 0
        
        # 情绪分析（基于文本关键词）
        if 'text' in df.columns:
            positive_keywords = ['看好', '买入', '上涨', '利好', '突破', '牛市']
            negative_keywords = ['看空', '卖出', '下跌', '利空', '风险', '熊市']
            
            positive_count = 0
            negative_count = 0
            
            for text in df['text']:
                text_str = str(text)
                for keyword in positive_keywords:
                    if keyword in text_str:
                        positive_count += 1
                        break
                for keyword in negative_keywords:
                    if keyword in text_str:
                        negative_count += 1
                        break
            
            total = positive_count + negative_count
            if total > 0:
                result['sentiment_score'] = positive_count / total
                
                if result['sentiment_score'] > 0.6:
                    result['sentiment'] = 'bullish'
                elif result['sentiment_score'] < 0.4:
                    result['sentiment'] = 'bearish'
        
        return result
    
    def get_smart_money_signal(self, symbol: str) -> Dict:
        """
        获取聪明钱信号
        
        重点关注大V和高质量讨论
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 聪明钱信号
        """
        sentiment = self.analyze_sentiment(symbol)
        big_v_df = self.get_big_v_opinions(symbol)
        
        signal = {
            'symbol': symbol,
            'sentiment': sentiment['sentiment'],
            'quality_score': sentiment['quality_score'],
            'big_v_count': len(big_v_df) if not big_v_df.empty else 0,
            'signal': 'hold',
            'confidence': 0.0,
            'reason': ''
        }
        
        # 生成信号
        if (sentiment['sentiment'] == 'bullish' and 
            sentiment['big_v_ratio'] > 0.2 and 
            sentiment['quality_score'] > 10):
            signal['signal'] = 'buy'
            signal['confidence'] = min(0.7, sentiment['sentiment_score'])
            signal['reason'] = '聪明钱看好，大V占比高，讨论质量高'
        
        elif (sentiment['sentiment'] == 'bearish' and 
              sentiment['big_v_ratio'] > 0.2):
            signal['signal'] = 'sell'
            signal['confidence'] = min(0.6, 1 - sentiment['sentiment_score'])
            signal['reason'] = '聪明钱看空，大V占比高'
        
        else:
            signal['reason'] = '聪明钱观点不明确或质量不足'
        
        return signal
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': '雪球',
            'type': '爬虫挖掘型',
            'features': [
                '聪明钱情绪',
                '深度讨论',
                '大V观点',
                '高质量内容'
            ],
            'data_quality': '⭐⭐⭐⭐',
            'update_frequency': '实时',
            'cost': '免费',
            'difficulty': '中等（需Cookie）',
            'best_for': '专业投资者情绪、深度分析',
            'status': '已初始化（需Cookie认证）'
        }

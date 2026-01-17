"""
数据整合器
整合10个数据源，提供统一的数据获取和分析接口
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# API直达型
from .api_sources import (
    TushareSource,
    AkShareSource,
    Jin10Source,
    CLSSource,
    CninfoSource
)

# 爬虫挖掘型
from .crawler_sources import (
    WallstreetCNSource,
    EastMoneySource,
    GubaSource,
    XueqiuSource,
    IWencaiSource
)


class NewsDataIntegrator:
    """
    消息面数据整合器
    
    功能：
    1. 统一管理10个数据源
    2. 一键获取所有消息面数据
    3. 智能筛选重要新闻
    4. 综合情绪分析
    5. 生成交易信号
    """
    
    def __init__(self, tushare_token: Optional[str] = None):
        """
        初始化数据整合器
        
        Args:
            tushare_token: Tushare Pro Token（可选）
        """
        print("\n" + "=" * 60)
        print("🚀 初始化消息面数据整合器")
        print("=" * 60)
        
        # 初始化API直达型数据源
        self.tushare = TushareSource(token=tushare_token)
        self.akshare = AkShareSource()
        self.jin10 = Jin10Source()
        self.cls = CLSSource()
        self.cninfo = CninfoSource()
        
        # 初始化爬虫挖掘型数据源
        self.wallstreetcn = WallstreetCNSource()
        self.eastmoney = EastMoneySource()
        self.guba = GubaSource()
        self.xueqiu = XueqiuSource()
        self.iwencai = IWencaiSource()
        
        print("\n✅ 所有数据源初始化完成")
        print("=" * 60 + "\n")
    
    def get_all_news(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取个股所有消息面数据
        
        Args:
            symbol: 股票代码（如：600893）
            
        Returns:
            Dict: 包含所有数据的字典
        """
        print(f"\n{'='*60}")
        print(f"📊 开始采集 {symbol} 的所有消息面数据")
        print(f"{'='*60}\n")
        
        data = {}
        
        # 1. AkShare（最全面）
        print("1️⃣  AkShare 数据采集...")
        data['akshare'] = self.akshare.get_all_data(symbol)
        
        # 2. 财联社快讯
        print("\n2️⃣  财联社快讯...")
        data['cls_telegraph'] = self.cls.get_stock_related_news(symbol)
        
        # 3. 巨潮公告
        print("\n3️⃣  巨潮公告...")
        data['cninfo_announcements'] = self.cninfo.get_major_announcements(symbol)
        
        # 4. 华尔街见闻
        print("\n4️⃣  华尔街见闻...")
        data['wallstreetcn_news'] = self.wallstreetcn.search_by_keyword(symbol)
        
        # 5. 东方财富数据中心
        print("\n5️⃣  东方财富数据中心...")
        data['eastmoney'] = self.eastmoney.get_stock_data_center(symbol)
        
        # 6. 股吧情绪
        print("\n6️⃣  股吧情绪...")
        data['guba_posts'] = self.guba.get_posts(symbol)
        data['guba_sentiment'] = self.guba.calculate_heat_score(symbol)
        
        # 7. 雪球讨论
        print("\n7️⃣  雪球讨论...")
        xq_symbol = f"SH{symbol}" if symbol.startswith('6') else f"SZ{symbol}"
        data['xueqiu_discussions'] = self.xueqiu.get_hot_discussions(xq_symbol)
        data['xueqiu_sentiment'] = self.xueqiu.analyze_sentiment(xq_symbol)
        
        print(f"\n{'='*60}")
        print("✅ 数据采集完成")
        print(f"{'='*60}\n")
        
        return data
    
    def get_important_news_only(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        只获取重要新闻（大新闻筛选）
        
        Args:
            symbol: 股票代码（可选，不提供则获取市场重要新闻）
            
        Returns:
            DataFrame: 重要新闻
        """
        important_items = []
        
        # 1. 新闻联播（最权威）
        if self.tushare.pro:
            cctv = self.tushare.get_major_news()
            if not cctv.empty:
                for _, row in cctv.head(10).iterrows():
                    important_items.append({
                        'source': '新闻联播',
                        'type': '权威新闻',
                        'title': row.get('title', ''),
                        'content': row.get('content', ''),
                        'time': row.get('date', ''),
                        'importance': '⭐⭐⭐⭐⭐'
                    })
        
        # 2. 财联社重要快讯
        cls_important = self.cls.get_important_news()
        if not cls_important.empty:
            for _, row in cls_important.head(10).iterrows():
                important_items.append({
                    'source': '财联社',
                    'type': '重要快讯',
                    'title': row.get('title', ''),
                    'content': row.get('brief', row.get('content', '')),
                    'time': row.get('ctime', ''),
                    'importance': '⭐⭐⭐⭐'
                })
        
        # 3. 华尔街见闻重磅
        wsj_important = self.wallstreetcn.get_important_news()
        if not wsj_important.empty:
            for _, row in wsj_important.head(10).iterrows():
                important_items.append({
                    'source': '华尔街见闻',
                    'type': row.get('type', '重磅'),
                    'title': row.get('title', ''),
                    'content': row.get('content', ''),
                    'time': row.get('time', ''),
                    'importance': '⭐⭐⭐⭐'
                })
        
        # 4. 个股重大公告
        if symbol:
            announcements = self.cninfo.get_major_announcements(symbol)
            if not announcements.empty:
                for _, row in announcements.head(5).iterrows():
                    important_items.append({
                        'source': '巨潮资讯',
                        'type': '重大公告',
                        'title': row.get('title', ''),
                        'content': '',
                        'time': row.get('time', ''),
                        'importance': '⭐⭐⭐⭐⭐'
                    })
        
        if important_items:
            df = pd.DataFrame(important_items)
            print(f"✅ 筛选出 {len(df)} 条重要新闻")
            return df
        
        return pd.DataFrame()
    
    def analyze_comprehensive_sentiment(self, symbol: str) -> Dict:
        """
        综合情绪分析
        
        整合多个数据源的情绪指标
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 综合情绪分析结果
        """
        print(f"\n{'='*60}")
        print(f"🎯 综合情绪分析 - {symbol}")
        print(f"{'='*60}\n")
        
        result = {
            'symbol': symbol,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'overall_sentiment': 'neutral',
            'confidence': 0.0,
            'sources': {}
        }
        
        # 1. 股吧情绪（散户）
        print("分析股吧情绪...")
        guba_sentiment = self.guba.calculate_heat_score(symbol)
        result['sources']['guba'] = {
            'sentiment': guba_sentiment.get('sentiment', 'neutral'),
            'heat_level': guba_sentiment.get('heat_level', 'low'),
            'weight': 0.2
        }
        
        # 2. 雪球情绪（聪明钱）
        print("分析雪球情绪...")
        xq_symbol = f"SH{symbol}" if symbol.startswith('6') else f"SZ{symbol}"
        xueqiu_sentiment = self.xueqiu.analyze_sentiment(xq_symbol)
        result['sources']['xueqiu'] = {
            'sentiment': xueqiu_sentiment.get('sentiment', 'neutral'),
            'quality_score': xueqiu_sentiment.get('quality_score', 0),
            'weight': 0.3
        }
        
        # 3. 新闻情绪
        print("分析新闻情绪...")
        news_df = self.akshare.get_stock_news(symbol)
        news_sentiment = 'neutral'
        if not news_df.empty and '标题' in news_df.columns:
            positive_count = 0
            negative_count = 0
            for title in news_df['标题'].head(20):
                if any(kw in str(title) for kw in ['利好', '上涨', '增长', '突破']):
                    positive_count += 1
                if any(kw in str(title) for kw in ['利空', '下跌', '风险', '亏损']):
                    negative_count += 1
            
            if positive_count > negative_count * 1.5:
                news_sentiment = 'bullish'
            elif negative_count > positive_count * 1.5:
                news_sentiment = 'bearish'
        
        result['sources']['news'] = {
            'sentiment': news_sentiment,
            'weight': 0.3
        }
        
        # 4. 公告情绪
        print("分析公告情绪...")
        announcements = self.cninfo.get_major_announcements(symbol, days=7)
        announcement_sentiment = 'neutral'
        if not announcements.empty and 'title' in announcements.columns:
            positive_count = 0
            negative_count = 0
            for title in announcements['title']:
                if any(kw in str(title) for kw in ['业绩预增', '重大合同', '增持']):
                    positive_count += 1
                if any(kw in str(title) for kw in ['业绩预亏', '减持', '风险']):
                    negative_count += 1
            
            if positive_count > negative_count:
                announcement_sentiment = 'bullish'
            elif negative_count > positive_count:
                announcement_sentiment = 'bearish'
        
        result['sources']['announcement'] = {
            'sentiment': announcement_sentiment,
            'weight': 0.2
        }
        
        # 综合计算
        sentiment_scores = {
            'bullish': 1.0,
            'neutral': 0.5,
            'bearish': 0.0
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for source, data in result['sources'].items():
            sentiment = data.get('sentiment', 'neutral')
            weight = data.get('weight', 0.0)
            score = sentiment_scores.get(sentiment, 0.5)
            weighted_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            final_score = weighted_score / total_weight
            result['confidence'] = abs(final_score - 0.5) * 2  # 0-1
            
            if final_score > 0.6:
                result['overall_sentiment'] = 'bullish'
            elif final_score < 0.4:
                result['overall_sentiment'] = 'bearish'
        
        print(f"\n{'='*60}")
        print(f"综合情绪: {result['overall_sentiment'].upper()}")
        print(f"置信度: {result['confidence']:.2%}")
        print(f"{'='*60}\n")
        
        return result
    
    def generate_trading_signal(self, symbol: str) -> Dict:
        """
        生成交易信号
        
        基于综合消息面分析
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 交易信号
        """
        print(f"\n{'='*60}")
        print(f"🎯 生成交易信号 - {symbol}")
        print(f"{'='*60}\n")
        
        # 综合情绪分析
        sentiment = self.analyze_comprehensive_sentiment(symbol)
        
        # 获取重要新闻
        important_news = self.get_important_news_only(symbol)
        
        # 股吧反向指标
        guba_indicator = self.guba.get_sentiment_indicator(symbol)
        
        # 雪球聪明钱信号
        xq_symbol = f"SH{symbol}" if symbol.startswith('6') else f"SZ{symbol}"
        xueqiu_signal = self.xueqiu.get_smart_money_signal(xq_symbol)
        
        signal = {
            'symbol': symbol,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'signal': 'hold',
            'confidence': 0.0,
            'reasons': [],
            'sentiment': sentiment,
            'important_news_count': len(important_news) if not important_news.empty else 0
        }
        
        # 决策逻辑
        reasons = []
        score = 0.5  # 中性
        
        # 1. 综合情绪权重 40%
        if sentiment['overall_sentiment'] == 'bullish':
            score += 0.2
            reasons.append(f"综合情绪正面(置信度{sentiment['confidence']:.1%})")
        elif sentiment['overall_sentiment'] == 'bearish':
            score -= 0.2
            reasons.append(f"综合情绪负面(置信度{sentiment['confidence']:.1%})")
        
        # 2. 重要新闻权重 30%
        if signal['important_news_count'] > 0:
            score += 0.15
            reasons.append(f"有{signal['important_news_count']}条重要新闻")
        
        # 3. 聪明钱信号权重 20%
        if xueqiu_signal['signal'] == 'buy':
            score += 0.1
            reasons.append("雪球聪明钱看好")
        elif xueqiu_signal['signal'] == 'sell':
            score -= 0.1
            reasons.append("雪球聪明钱看空")
        
        # 4. 股吧反向指标权重 10%
        if guba_indicator['signal'] == 'sell':  # 反向
            score -= 0.05
            reasons.append("股吧过度乐观(反向指标)")
        elif guba_indicator['signal'] == 'buy':  # 反向
            score += 0.05
            reasons.append("股吧过度悲观(反向指标)")
        
        # 生成最终信号
        signal['confidence'] = abs(score - 0.5) * 2
        signal['reasons'] = reasons
        
        if score > 0.6:
            signal['signal'] = 'buy'
        elif score < 0.4:
            signal['signal'] = 'sell'
        
        print(f"交易信号: {signal['signal'].upper()}")
        print(f"置信度: {signal['confidence']:.1%}")
        print(f"原因: {', '.join(reasons)}")
        print(f"{'='*60}\n")
        
        return signal
    
    def monitor_sector(self, sector: str, keywords: List[str]) -> Dict:
        """
        监控板块消息面
        
        Args:
            sector: 板块名称（如：航空航天）
            keywords: 关键词列表
            
        Returns:
            Dict: 板块监控结果
        """
        print(f"\n{'='*60}")
        print(f"📡 监控板块消息面 - {sector}")
        print(f"{'='*60}\n")
        
        result = {
            'sector': sector,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'news_count': 0,
            'important_news': [],
            'hot_stocks': [],
            'sentiment': 'neutral'
        }
        
        # 1. 财联社板块新闻
        print(f"搜索{sector}板块新闻...")
        cls_news = self.cls.get_sector_news(sector)
        result['news_count'] += len(cls_news) if not cls_news.empty else 0
        
        # 2. 华尔街见闻相关新闻
        print(f"搜索华尔街见闻...")
        wsj_news = self.wallstreetcn.search_by_keyword(sector)
        result['news_count'] += len(wsj_news) if not wsj_news.empty else 0
        
        # 3. i问财板块龙头
        print(f"查询板块龙头...")
        leaders = self.iwencai.get_sector_leaders(sector)
        if not leaders.empty and '股票代码' in leaders.columns:
            result['hot_stocks'] = leaders['股票代码'].head(5).tolist()
        
        # 4. 关键词搜索
        print(f"搜索关键词...")
        for keyword in keywords:
            keyword_news = self.cls.search_keywords([keyword])
            if not keyword_news.empty:
                result['important_news'].append({
                    'keyword': keyword,
                    'count': len(keyword_news)
                })
        
        print(f"\n板块新闻总数: {result['news_count']}")
        print(f"龙头股票: {result['hot_stocks']}")
        print(f"{'='*60}\n")
        
        return result
    
    def get_summary(self) -> Dict:
        """获取整合器摘要信息"""
        return {
            'name': '消息面数据整合器',
            'version': '1.0.0',
            'data_sources': 10,
            'api_sources': 5,
            'crawler_sources': 5,
            'features': [
                '一键获取所有消息面数据',
                '智能筛选重要新闻',
                '综合情绪分析',
                '交易信号生成',
                '板块监控'
            ],
            'sources': {
                'API直达型': [
                    'Tushare Pro',
                    'AkShare',
                    '金十数据',
                    '财联社',
                    '巨潮资讯'
                ],
                '爬虫挖掘型': [
                    '华尔街见闻',
                    '东方财富',
                    '股吧',
                    '雪球',
                    'i问财'
                ]
            }
        }

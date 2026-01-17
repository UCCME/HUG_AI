"""
消息面数据采集器
提供完整的消息面数据获取和处理功能
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')


class NewsDataCollector:
    """
    消息面数据采集器
    
    支持采集：
    1. 新闻资讯
    2. 公司公告
    3. 研报评级
    4. 资金流向
    5. 股吧情绪
    6. 搜索热度
    """
    
    def __init__(self, symbol: str):
        """
        初始化采集器
        
        Args:
            symbol: 股票代码（如：600893）
        """
        self.symbol = symbol
        self.data_cache = {}
    
    def collect_news(self, days: int = 30) -> pd.DataFrame:
        """
        采集新闻数据
        
        Args:
            days: 回溯天数
            
        Returns:
            DataFrame: 新闻数据
        """
        try:
            import akshare as ak
            
            # 东方财富新闻
            news_df = ak.stock_news_em(symbol=self.symbol)
            
            if news_df is not None and not news_df.empty:
                # 转换时间格式
                news_df['发布时间'] = pd.to_datetime(news_df['发布时间'])
                
                # 过滤时间范围
                cutoff_date = datetime.now() - timedelta(days=days)
                news_df = news_df[news_df['发布时间'] >= cutoff_date]
                
                print(f"✅ 采集到 {len(news_df)} 条新闻")
                return news_df
            else:
                print("⚠️  未获取到新闻数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 新闻采集失败: {str(e)}")
            return pd.DataFrame()
    
    def collect_announcements(self) -> pd.DataFrame:
        """
        采集公司公告
        
        Returns:
            DataFrame: 公告数据
        """
        try:
            import akshare as ak
            
            # 获取股票名称
            stock_info = ak.stock_individual_info_em(symbol=self.symbol)
            stock_name = stock_info.loc[stock_info['item'] == '股票简称', 'value'].values[0]
            
            # 公司公告
            announcement_df = ak.stock_notice_report(symbol=stock_name)
            
            if announcement_df is not None and not announcement_df.empty:
                print(f"✅ 采集到 {len(announcement_df)} 条公告")
                return announcement_df
            else:
                print("⚠️  未获取到公告数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 公告采集失败: {str(e)}")
            return pd.DataFrame()
    
    def collect_research_reports(self) -> pd.DataFrame:
        """
        采集研报评级
        
        Returns:
            DataFrame: 研报数据
        """
        try:
            import akshare as ak
            
            # 研报
            report_df = ak.stock_research_report_em(symbol=self.symbol)
            
            if report_df is not None and not report_df.empty:
                print(f"✅ 采集到 {len(report_df)} 条研报")
                return report_df
            else:
                print("⚠️  未获取到研报数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 研报采集失败: {str(e)}")
            return pd.DataFrame()
    
    def collect_fund_flow(self, days: int = 30) -> pd.DataFrame:
        """
        采集资金流向
        
        Args:
            days: 回溯天数
            
        Returns:
            DataFrame: 资金流向数据
        """
        try:
            import akshare as ak
            
            # 个股资金流
            fund_df = ak.stock_individual_fund_flow(
                symbol=self.symbol,
                market="sh" if self.symbol.startswith('6') else "sz"
            )
            
            if fund_df is not None and not fund_df.empty:
                # 只保留最近N天
                fund_df = fund_df.head(days)
                print(f"✅ 采集到 {len(fund_df)} 天资金流向")
                return fund_df
            else:
                print("⚠️  未获取到资金流向数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 资金流向采集失败: {str(e)}")
            return pd.DataFrame()
    
    def collect_hsgt_flow(self) -> pd.DataFrame:
        """
        采集北向资金流向
        
        Returns:
            DataFrame: 北向资金数据
        """
        try:
            import akshare as ak
            
            # 北向资金
            hsgt_df = ak.stock_hsgt_individual_em(symbol=self.symbol)
            
            if hsgt_df is not None and not hsgt_df.empty:
                print(f"✅ 采集到北向资金数据")
                return hsgt_df
            else:
                print("⚠️  未获取到北向资金数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 北向资金采集失败: {str(e)}")
            return pd.DataFrame()
    
    def collect_guba_sentiment(self) -> pd.DataFrame:
        """
        采集股吧情绪
        
        Returns:
            DataFrame: 股吧数据
        """
        try:
            import akshare as ak
            
            # 股吧
            guba_df = ak.stock_comment_em(symbol=self.symbol)
            
            if guba_df is not None and not guba_df.empty:
                print(f"✅ 采集到 {len(guba_df)} 条股吧帖子")
                return guba_df
            else:
                print("⚠️  未获取到股吧数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 股吧采集失败: {str(e)}")
            return pd.DataFrame()
    
    def collect_search_index(self, keyword: str = None) -> pd.DataFrame:
        """
        采集搜索指数
        
        Args:
            keyword: 搜索关键词（默认使用股票名称）
            
        Returns:
            DataFrame: 搜索指数数据
        """
        try:
            import akshare as ak
            
            if keyword is None:
                # 获取股票名称
                stock_info = ak.stock_individual_info_em(symbol=self.symbol)
                keyword = stock_info.loc[stock_info['item'] == '股票简称', 'value'].values[0]
            
            # 百度指数
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            baidu_df = ak.baidu_search_index(
                word=keyword,
                start_date=start_date,
                end_date=end_date
            )
            
            if baidu_df is not None and not baidu_df.empty:
                print(f"✅ 采集到搜索指数数据")
                return baidu_df
            else:
                print("⚠️  未获取到搜索指数数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 搜索指数采集失败: {str(e)}")
            return pd.DataFrame()
    
    def collect_all(self) -> Dict[str, pd.DataFrame]:
        """
        采集所有消息面数据
        
        Returns:
            Dict: 包含所有数据的字典
        """
        print(f"\n{'='*60}")
        print(f"开始采集 {self.symbol} 的消息面数据")
        print(f"{'='*60}\n")
        
        data = {
            'news': self.collect_news(),
            'announcements': self.collect_announcements(),
            'research_reports': self.collect_research_reports(),
            'fund_flow': self.collect_fund_flow(),
            'hsgt_flow': self.collect_hsgt_flow(),
            'guba_sentiment': self.collect_guba_sentiment(),
            'search_index': self.collect_search_index()
        }
        
        print(f"\n{'='*60}")
        print("数据采集完成")
        print(f"{'='*60}\n")
        
        self.data_cache = data
        return data
    
    def analyze_sentiment(self, text: str) -> float:
        """
        分析文本情绪
        
        Args:
            text: 文本内容
            
        Returns:
            float: 情绪得分（0-1，越大越正面）
        """
        try:
            from snownlp import SnowNLP
            s = SnowNLP(text)
            return s.sentiments
        except:
            # 如果没有安装snownlp，使用简单的关键词方法
            positive_keywords = ['利好', '上涨', '增长', '突破', '创新', '合作', '订单', '盈利']
            negative_keywords = ['利空', '下跌', '亏损', '风险', '减持', '诉讼', '处罚', '预警']
            
            score = 0.5  # 中性
            for keyword in positive_keywords:
                if keyword in text:
                    score += 0.05
            for keyword in negative_keywords:
                if keyword in text:
                    score -= 0.05
            
            return max(0.0, min(1.0, score))
    
    def generate_report(self) -> Dict:
        """
        生成消息面分析报告
        
        Returns:
            Dict: 分析报告
        """
        if not self.data_cache:
            self.collect_all()
        
        report = {
            'symbol': self.symbol,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'news_count': len(self.data_cache.get('news', [])),
            'announcement_count': len(self.data_cache.get('announcements', [])),
            'research_count': len(self.data_cache.get('research_reports', [])),
            'sentiment_score': 0.5,
            'heat_score': 1.0,
            'fund_flow_trend': 'neutral',
            'overall_rating': 'neutral'
        }
        
        # 计算新闻情绪
        news_df = self.data_cache.get('news', pd.DataFrame())
        if not news_df.empty and '标题' in news_df.columns:
            sentiments = news_df['标题'].apply(self.analyze_sentiment)
            report['sentiment_score'] = sentiments.mean()
        
        # 计算热度
        if report['news_count'] > 0:
            # 简化：新闻数量作为热度指标
            report['heat_score'] = min(report['news_count'] / 10, 3.0)
        
        # 资金流向趋势
        fund_df = self.data_cache.get('fund_flow', pd.DataFrame())
        if not fund_df.empty and '主力净流入' in fund_df.columns:
            recent_flow = fund_df.head(5)['主力净流入'].sum()
            if recent_flow > 0:
                report['fund_flow_trend'] = 'positive'
            elif recent_flow < 0:
                report['fund_flow_trend'] = 'negative'
        
        # 综合评级
        if report['sentiment_score'] > 0.6 and report['fund_flow_trend'] == 'positive':
            report['overall_rating'] = 'bullish'
        elif report['sentiment_score'] < 0.4 and report['fund_flow_trend'] == 'negative':
            report['overall_rating'] = 'bearish'
        
        return report
    
    def print_report(self):
        """打印分析报告"""
        report = self.generate_report()
        
        print(f"\n{'='*60}")
        print(f"📊 消息面分析报告 - {report['symbol']}")
        print(f"{'='*60}")
        print(f"日期: {report['date']}")
        print(f"\n数据统计:")
        print(f"  - 新闻数量: {report['news_count']} 条")
        print(f"  - 公告数量: {report['announcement_count']} 条")
        print(f"  - 研报数量: {report['research_count']} 条")
        print(f"\n情绪分析:")
        print(f"  - 情绪得分: {report['sentiment_score']:.2f} ", end='')
        if report['sentiment_score'] > 0.6:
            print("(正面 ✅)")
        elif report['sentiment_score'] < 0.4:
            print("(负面 ❌)")
        else:
            print("(中性 ⚠️)")
        print(f"  - 热度得分: {report['heat_score']:.2f}x")
        print(f"\n资金流向:")
        print(f"  - 趋势: {report['fund_flow_trend']}")
        print(f"\n综合评级: {report['overall_rating'].upper()}")
        print(f"{'='*60}\n")


def example_usage():
    """使用示例"""
    print("🚀 消息面数据采集示例\n")
    
    # 航空航天板块股票
    aerospace_stocks = {
        '600893': '航发动力',
        '600760': '中航沈飞',
        '002013': '中航机电'
    }
    
    print("选择要分析的股票:")
    for i, (code, name) in enumerate(aerospace_stocks.items(), 1):
        print(f"{i}. {code} - {name}")
    
    choice = input("\n请输入序号 (1-3): ").strip()
    
    if choice.isdigit() and 1 <= int(choice) <= 3:
        code = list(aerospace_stocks.keys())[int(choice) - 1]
        name = aerospace_stocks[code]
        
        print(f"\n开始分析 {code} - {name}\n")
        
        # 创建采集器
        collector = NewsDataCollector(symbol=code)
        
        # 采集数据
        data = collector.collect_all()
        
        # 生成报告
        collector.print_report()
        
        # 显示部分数据
        print("\n📰 最新新闻:")
        news_df = data.get('news', pd.DataFrame())
        if not news_df.empty and '标题' in news_df.columns:
            for i, row in news_df.head(5).iterrows():
                print(f"  - {row['标题']}")
        
        print("\n📢 最新公告:")
        announcement_df = data.get('announcements', pd.DataFrame())
        if not announcement_df.empty and '公告标题' in announcement_df.columns:
            for i, row in announcement_df.head(3).iterrows():
                print(f"  - {row['公告标题']}")
    else:
        print("❌ 无效选项")


if __name__ == "__main__":
    # 检查依赖
    try:
        import akshare
        print("✅ akshare 已安装")
    except ImportError:
        print("❌ 请先安装 akshare: pip install akshare")
        exit(1)
    
    # 运行示例
    example_usage()

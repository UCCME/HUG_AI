"""
巨潮资讯网数据源
官方法定披露渠道
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


class CninfoSource:
    """
    巨潮资讯网数据源
    
    核心价值：
    - 官方法定披露渠道
    - 公告原文
    - 第一时间发布
    - 事件驱动策略必选
    
    使用方式：
    抓取公告搜索API
    """
    
    def __init__(self):
        """初始化巨潮资讯数据源"""
        self.base_url = "http://www.cninfo.com.cn"
        self.api_url = "http://www.cninfo.com.cn/new"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        }
        print("✅ 巨潮资讯数据源初始化成功")
    
    def get_announcements(self, stock_code: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         category: Optional[str] = None,
                         page_num: int = 1,
                         page_size: int = 30) -> pd.DataFrame:
        """
        获取公司公告
        
        Args:
            stock_code: 股票代码（如：600893）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            category: 公告类别
            page_num: 页码
            page_size: 每页数量
            
        Returns:
            DataFrame: 公告数据
        """
        try:
            url = f"{self.api_url}/hisAnnouncement/query"
            
            # 默认日期范围
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            params = {
                'pageNum': page_num,
                'pageSize': page_size,
                'stock': stock_code or '',
                'searchkey': '',
                'category': category or '',
                'trade': '',
                'column': 'szse' if stock_code and stock_code.startswith('0') else 'sse',
                'columnTitle': '历史公告查询',
                'seDate': f"{start_date}~{end_date}",
                'sortName': '',
                'sortType': '',
                'isHLtitle': 'true'
            }
            
            response = requests.post(url, data=params, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'announcements' in data:
                    items = data['announcements']
                    
                    # 解析数据
                    records = []
                    for item in items:
                        record = {
                            'code': item.get('secCode'),
                            'name': item.get('secName'),
                            'title': item.get('announcementTitle'),
                            'time': item.get('announcementTime'),
                            'type': item.get('announcementType'),
                            'url': f"{self.base_url}/{item.get('adjunctUrl')}" if item.get('adjunctUrl') else '',
                            'id': item.get('announcementId')
                        }
                        records.append(record)
                    
                    df = pd.DataFrame(records)
                    print(f"✅ 获取到 {len(df)} 条公告")
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取公告失败: {str(e)}")
            return pd.DataFrame()
    
    def get_major_announcements(self, stock_code: Optional[str] = None,
                               days: int = 7) -> pd.DataFrame:
        """
        获取重大公告
        
        筛选重要公告类型
        
        Args:
            stock_code: 股票代码
            days: 回溯天数
            
        Returns:
            DataFrame: 重大公告
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        df = self.get_announcements(stock_code, start_date, end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        # 重大公告关键词
        major_keywords = [
            '业绩预告', '业绩快报', '年度报告', '半年度报告',
            '重大合同', '重大资产重组', '股权激励',
            '增持', '减持', '停牌', '复牌',
            '分红', '配股', '增发',
            '诉讼', '仲裁', '处罚'
        ]
        
        if 'title' in df.columns:
            mask = pd.Series([False] * len(df))
            for keyword in major_keywords:
                mask |= df['title'].str.contains(keyword, case=False, na=False)
            
            major = df[mask]
            print(f"✅ 筛选出 {len(major)} 条重大公告")
            return major
        
        return df
    
    def get_performance_announcements(self, stock_code: Optional[str] = None) -> pd.DataFrame:
        """
        获取业绩公告
        
        Args:
            stock_code: 股票代码
            
        Returns:
            DataFrame: 业绩公告
        """
        df = self.get_announcements(stock_code)
        
        if df.empty:
            return pd.DataFrame()
        
        # 业绩相关关键词
        keywords = ['业绩预告', '业绩快报', '年度报告', '半年度报告', '季度报告']
        
        if 'title' in df.columns:
            mask = pd.Series([False] * len(df))
            for keyword in keywords:
                mask |= df['title'].str.contains(keyword, case=False, na=False)
            
            result = df[mask]
            print(f"✅ 找到 {len(result)} 条业绩公告")
            return result
        
        return pd.DataFrame()
    
    def get_contract_announcements(self, stock_code: Optional[str] = None) -> pd.DataFrame:
        """
        获取合同订单公告
        
        Args:
            stock_code: 股票代码
            
        Returns:
            DataFrame: 合同公告
        """
        df = self.get_announcements(stock_code)
        
        if df.empty:
            return pd.DataFrame()
        
        # 合同订单关键词
        keywords = ['重大合同', '中标', '订单', '采购', '销售合同']
        
        if 'title' in df.columns:
            mask = pd.Series([False] * len(df))
            for keyword in keywords:
                mask |= df['title'].str.contains(keyword, case=False, na=False)
            
            result = df[mask]
            print(f"✅ 找到 {len(result)} 条合同订单公告")
            return result
        
        return pd.DataFrame()
    
    def get_shareholder_change_announcements(self, stock_code: Optional[str] = None) -> pd.DataFrame:
        """
        获取股东变动公告
        
        Args:
            stock_code: 股票代码
            
        Returns:
            DataFrame: 股东变动公告
        """
        df = self.get_announcements(stock_code)
        
        if df.empty:
            return pd.DataFrame()
        
        # 股东变动关键词
        keywords = ['增持', '减持', '股权转让', '股东变动', '权益变动']
        
        if 'title' in df.columns:
            mask = pd.Series([False] * len(df))
            for keyword in keywords:
                mask |= df['title'].str.contains(keyword, case=False, na=False)
            
            result = df[mask]
            print(f"✅ 找到 {len(result)} 条股东变动公告")
            return result
        
        return pd.DataFrame()
    
    def classify_announcement(self, title: str) -> Dict:
        """
        分类公告并评估影响
        
        Args:
            title: 公告标题
            
        Returns:
            Dict: 分类结果和影响评估
        """
        result = {
            'category': 'other',
            'impact': 'neutral',
            'importance': 'low',
            'keywords': []
        }
        
        # 利好公告
        positive_keywords = {
            '业绩预增': ('performance', 'positive', 'high'),
            '业绩大幅增长': ('performance', 'positive', 'high'),
            '重大合同': ('contract', 'positive', 'high'),
            '中标': ('contract', 'positive', 'medium'),
            '股权激励': ('incentive', 'positive', 'medium'),
            '增持': ('shareholder', 'positive', 'medium'),
            '分红': ('dividend', 'positive', 'low'),
        }
        
        # 利空公告
        negative_keywords = {
            '业绩预亏': ('performance', 'negative', 'high'),
            '业绩下滑': ('performance', 'negative', 'high'),
            '减持': ('shareholder', 'negative', 'medium'),
            '诉讼': ('legal', 'negative', 'medium'),
            '处罚': ('legal', 'negative', 'medium'),
            '风险提示': ('risk', 'negative', 'low'),
        }
        
        # 检查利好关键词
        for keyword, (cat, impact, importance) in positive_keywords.items():
            if keyword in title:
                result['category'] = cat
                result['impact'] = impact
                result['importance'] = importance
                result['keywords'].append(keyword)
        
        # 检查利空关键词
        for keyword, (cat, impact, importance) in negative_keywords.items():
            if keyword in title:
                result['category'] = cat
                result['impact'] = impact
                result['importance'] = importance
                result['keywords'].append(keyword)
        
        return result
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': '巨潮资讯网',
            'type': 'API直达型',
            'features': [
                '官方法定披露',
                '公告原文',
                '第一时间发布',
                '权威可靠'
            ],
            'data_quality': '⭐⭐⭐⭐⭐',
            'update_frequency': '实时',
            'cost': '免费',
            'difficulty': '中等',
            'best_for': '事件驱动策略、基本面分析',
            'status': '已初始化'
        }

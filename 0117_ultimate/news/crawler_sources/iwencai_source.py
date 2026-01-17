"""
同花顺i问财数据源
自然语言搜索、逻辑归因、数据清洗器
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
import warnings
warnings.filterwarnings('ignore')


class IWencaiSource:
    """
    同花顺i问财数据源
    
    核心价值：
    - 自然语言搜索
    - 逻辑归因
    - 数据清洗器
    - 返回结构化表格
    
    使用方式：
    模拟HTTP请求，解析JSON数据
    """
    
    def __init__(self):
        """初始化i问财数据源"""
        self.base_url = "http://www.iwencai.com"
        self.api_url = "http://www.iwencai.com/unifiedwap/unified-wap/v2/result/get-robot-data"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.iwencai.com/',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.cookies = {}
        print("✅ i问财数据源初始化成功")
    
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
    
    def search(self, query: str, perpage: int = 50) -> pd.DataFrame:
        """
        自然语言搜索
        
        Args:
            query: 搜索问题（如："今日涨停原因"）
            perpage: 每页数量
            
        Returns:
            DataFrame: 搜索结果
        """
        try:
            # 确保有token
            if not self.cookies:
                self._get_token()
            
            data = {
                'question': query,
                'perpage': perpage,
                'page': 1,
                'secondary_intent': 'stock',
                'log_info': json.dumps({
                    'input_type': 'typewrite'
                })
            }
            
            response = requests.post(self.api_url, json=data, headers=self.headers,
                                   cookies=self.cookies, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                
                if 'data' in result and 'answer' in result['data']:
                    answer = result['data']['answer']
                    
                    # 提取表格数据
                    if 'components' in answer:
                        for component in answer['components']:
                            if component.get('type') == 'table':
                                table_data = component.get('data', {}).get('datas', [])
                                if table_data:
                                    df = pd.DataFrame(table_data)
                                    print(f"✅ 搜索'{query}'返回 {len(df)} 条结果")
                                    return df
            
            print(f"⚠️  搜索'{query}'未返回数据")
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 搜索失败: {str(e)}")
            return pd.DataFrame()
    
    def get_limit_up_reasons(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取涨停原因
        
        Args:
            date: 日期（YYYY-MM-DD）
            
        Returns:
            DataFrame: 涨停股票及原因
        """
        if date is None:
            query = "今日涨停原因"
        else:
            query = f"{date}涨停原因"
        
        return self.search(query)
    
    def get_sector_leaders(self, sector: str) -> pd.DataFrame:
        """
        获取板块龙头
        
        Args:
            sector: 板块名称（如：航空航天）
            
        Returns:
            DataFrame: 板块龙头股票
        """
        query = f"{sector}板块龙头股"
        return self.search(query)
    
    def get_performance_forecast(self, condition: str = "业绩预增") -> pd.DataFrame:
        """
        获取业绩预告
        
        Args:
            condition: 条件（业绩预增/业绩预亏等）
            
        Returns:
            DataFrame: 业绩预告股票
        """
        query = f"{condition}的股票"
        return self.search(query)
    
    def get_institutional_holdings(self, min_ratio: float = 10.0) -> pd.DataFrame:
        """
        获取机构持仓
        
        Args:
            min_ratio: 最小持仓比例（%）
            
        Returns:
            DataFrame: 机构重仓股
        """
        query = f"机构持仓比例大于{min_ratio}%的股票"
        return self.search(query)
    
    def get_technical_signals(self, signal_type: str = "金叉") -> pd.DataFrame:
        """
        获取技术信号
        
        Args:
            signal_type: 信号类型（金叉/死叉/突破等）
            
        Returns:
            DataFrame: 符合技术信号的股票
        """
        query = f"今日{signal_type}的股票"
        return self.search(query)
    
    def get_custom_query(self, query: str) -> pd.DataFrame:
        """
        自定义查询
        
        支持任意自然语言问题
        
        Args:
            query: 自然语言问题
            
        Returns:
            DataFrame: 查询结果
        """
        return self.search(query)
    
    def analyze_query_result(self, df: pd.DataFrame) -> Dict:
        """
        分析查询结果
        
        Args:
            df: 查询结果DataFrame
            
        Returns:
            Dict: 分析结果
        """
        result = {
            'total_count': 0,
            'has_data': False,
            'columns': [],
            'summary': {}
        }
        
        if df.empty:
            return result
        
        result['total_count'] = len(df)
        result['has_data'] = True
        result['columns'] = df.columns.tolist()
        
        # 统计摘要
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                result['summary'][col] = {
                    'mean': df[col].mean(),
                    'max': df[col].max(),
                    'min': df[col].min()
                }
        
        return result
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': '同花顺i问财',
            'type': '爬虫挖掘型',
            'features': [
                '自然语言搜索',
                '逻辑归因',
                '数据清洗器',
                '结构化表格'
            ],
            'data_quality': '⭐⭐⭐⭐⭐',
            'update_frequency': '实时',
            'cost': '免费',
            'difficulty': '中等',
            'best_for': '特定逻辑挖掘、快速筛选、归因分析',
            'status': '已初始化'
        }

"""
金十数据源
提供全球宏观数据和财经日历
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')


class Jin10Source:
    """
    金十数据源
    
    核心价值：
    - 清洗度最高的宏观数据
    - 数值化数据（公布值、预测值、前值）
    - 适合写策略判断逻辑
    - 全球财经日历
    
    使用方式：
    1. 通过 AkShare 调用（推荐）
    2. 直接抓取 Web API
    """
    
    def __init__(self):
        """初始化金十数据源"""
        self.ak = None
        self.base_url = "https://flash-api.jin10.com"
        self._init_api()
    
    def _init_api(self):
        """初始化 API"""
        try:
            import akshare as ak
            self.ak = ak
            print("✅ 金十数据源初始化成功")
        except ImportError:
            print("⚠️  AkShare 未安装，将使用直接API方式")
            self.ak = None
    
    def get_economic_calendar(self, start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取财经日历
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            DataFrame: 财经日历数据
        """
        if self.ak is None:
            print("❌ 请先安装 akshare")
            return pd.DataFrame()
        
        try:
            # 默认获取今天的数据
            if start_date is None:
                start_date = datetime.now().strftime('%Y-%m-%d')
            if end_date is None:
                end_date = start_date
            
            df = self.ak.macro_cons_gold_volume()
            
            if df is not None and not df.empty:
                print(f"✅ 获取到财经日历数据")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取财经日历失败: {str(e)}")
            return pd.DataFrame()
    
    def get_flash_news(self, limit: int = 100) -> pd.DataFrame:
        """
        获取金十快讯
        
        Args:
            limit: 获取数量
            
        Returns:
            DataFrame: 快讯数据
        """
        try:
            # 使用金十数据的快讯API
            url = f"{self.base_url}/get_flash"
            params = {
                'limit': limit,
                'channel': '-1'  # 全部频道
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    print(f"✅ 获取到 {len(df)} 条金十快讯")
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取金十快讯失败: {str(e)}")
            return pd.DataFrame()
    
    def get_important_events(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取重要事件
        
        Args:
            date: 日期（YYYY-MM-DD）
            
        Returns:
            DataFrame: 重要事件数据
        """
        if self.ak is None:
            print("❌ 请先安装 akshare")
            return pd.DataFrame()
        
        try:
            # 获取财经日历中的重要事件
            df = self.ak.macro_cons_gold_volume()
            
            if df is not None and not df.empty:
                # 筛选重要性高的事件
                if '重要性' in df.columns:
                    important = df[df['重要性'] == '高']
                    print(f"✅ 获取到 {len(important)} 个重要事件")
                    return important
                return df
            
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 获取重要事件失败: {str(e)}")
            return pd.DataFrame()
    
    def check_data_surprise(self, actual: float, forecast: float, 
                           threshold: float = 0.1) -> Dict:
        """
        检查数据是否超预期
        
        Args:
            actual: 实际公布值
            forecast: 预测值
            threshold: 超预期阈值（默认10%）
            
        Returns:
            Dict: 分析结果
        """
        if forecast == 0:
            return {
                'is_surprise': False,
                'direction': 'neutral',
                'magnitude': 0,
                'signal': 'hold'
            }
        
        diff_pct = (actual - forecast) / abs(forecast)
        
        result = {
            'actual': actual,
            'forecast': forecast,
            'diff': actual - forecast,
            'diff_pct': diff_pct,
            'is_surprise': abs(diff_pct) > threshold,
            'direction': 'positive' if diff_pct > 0 else 'negative',
            'magnitude': abs(diff_pct),
            'signal': 'hold'
        }
        
        # 生成交易信号
        if result['is_surprise']:
            if diff_pct > threshold:
                result['signal'] = 'buy'  # 超预期利好
            elif diff_pct < -threshold:
                result['signal'] = 'sell'  # 超预期利空
        
        return result
    
    def get_macro_indicators(self) -> pd.DataFrame:
        """
        获取宏观指标
        
        Returns:
            DataFrame: 宏观指标数据
        """
        if self.ak is None:
            print("❌ 请先安装 akshare")
            return pd.DataFrame()
        
        try:
            # 获取中国宏观数据
            indicators = {}
            
            # GDP
            try:
                gdp = self.ak.macro_china_gdp()
                if not gdp.empty:
                    indicators['GDP'] = gdp
            except:
                pass
            
            # CPI
            try:
                cpi = self.ak.macro_china_cpi()
                if not cpi.empty:
                    indicators['CPI'] = cpi
            except:
                pass
            
            # PMI
            try:
                pmi = self.ak.macro_china_pmi()
                if not pmi.empty:
                    indicators['PMI'] = pmi
            except:
                pass
            
            if indicators:
                print(f"✅ 获取到 {len(indicators)} 个宏观指标")
                return pd.DataFrame(indicators)
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取宏观指标失败: {str(e)}")
            return pd.DataFrame()
    
    def get_summary(self) -> Dict:
        """获取数据源摘要信息"""
        return {
            'source': '金十数据',
            'type': 'API直达型',
            'features': [
                '清洗度最高',
                '数值化数据',
                '全球财经日历',
                '适合策略判断'
            ],
            'data_quality': '⭐⭐⭐⭐⭐',
            'update_frequency': '实时',
            'cost': '免费',
            'difficulty': '简单',
            'best_for': '宏观数据分析、事件驱动策略',
            'status': '已初始化' if self.ak else '部分功能可用'
        }

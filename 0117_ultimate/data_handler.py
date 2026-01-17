"""
数据获取和处理模块
整合多数据源支持和技术指标计算
"""
import pandas as pd
import numpy as np
import yfinance as yf
import os
from typing import Optional
import warnings
import time
import random
from config import UltimateConfig
from indicators import TechnicalIndicators

warnings.filterwarnings('ignore')

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️  提示：未安装 akshare，将使用 yfinance 作为备选方案")


class DataHandler:
    """数据处理类，负责数据获取、清洗和技术指标计算"""
    
    def __init__(self, config: UltimateConfig):
        self.config = config
        self.data = None
        self.indicators = TechnicalIndicators()
        
    def _normalize_dataframe(self, data: pd.DataFrame) -> pd.DataFrame:
        """标准化数据列名"""
        if data is None or data.empty:
            return pd.DataFrame()
        
        # 处理多层列索引
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        
        # 列名映射规则
        rename_rules = {
            'open': ['Open', 'OPEN'],
            'high': ['High', 'HIGH'],
            'low': ['Low', 'LOW'],
            'close': ['Close', 'CLOSE', 'price'],
            'volume': ['Volume', 'VOLUME', 'vol']
        }
        
        # 统一转换为小写列名
        column_mapping = {}
        for col in data.columns:
            col_lower = col.lower()
            for target, keywords in rename_rules.items():
                if col_lower in [k.lower() for k in keywords] or col_lower == target:
                    column_mapping[col] = target
                    break
        
        if column_mapping:
            data = data.rename(columns=column_mapping)
        
        # 确保必需列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required_columns if c not in data.columns]
        if missing:
            raise ValueError(f"数据缺少必需列: {missing}")
        
        data = data[required_columns]
        data = data.dropna()
        data.index = pd.to_datetime(data.index)
        
        return data
    
    def _load_local_data(self, file_path: str) -> pd.DataFrame:
        """加载本地CSV数据"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"本地数据文件不存在: {file_path}")
        
        print(f"📂 正在加载本地数据: {file_path}")
        data = pd.read_csv(file_path, index_col=0, parse_dates=True)
        data = self._normalize_dataframe(data)
        
        if data.empty:
            raise ValueError("本地数据为空或格式不正确")
        
        print(f"✅ 成功加载 {len(data)} 条数据记录")
        return data
    
    def _download_yfinance(self, symbol: str, start_date: str, end_date: str, max_retries: int = 3) -> pd.DataFrame:
        """使用yfinance下载数据"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = (2 ** attempt) * 2 + random.uniform(0, 2)
                    print(f"等待 {wait_time:.1f} 秒后重试...")
                    time.sleep(wait_time)
                
                print(f"正在从 yfinance 获取 {symbol} 数据... (尝试 {attempt + 1}/{max_retries})")
                
                data = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    timeout=30
                )
                
                data = self._normalize_dataframe(data)
                
                if data.empty:
                    if attempt < max_retries - 1:
                        print("数据为空，准备重试...")
                        continue
                    else:
                        raise Exception("下载的数据为空")
                
                print(f"✅ 成功获取 {len(data)} 条数据记录")
                return data
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"获取失败: {str(e)}，准备重试...")
                    continue
                else:
                    raise e
        
        return pd.DataFrame()
    
    def _download_akshare(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用AkShare下载数据"""
        if not AKSHARE_AVAILABLE:
            raise Exception("AkShare 不可用")
        
        try:
            print(f"正在使用 AkShare 获取 {symbol} 数据...")
            data = ak.futures_main_sina(symbol=symbol, start_date=start_date, end_date=end_date)
            
            if data is None or data.empty:
                raise Exception("AkShare 返回空数据")
            
            # 设置日期索引
            date_cols = [c for c in data.columns if 'date' in c.lower() or '日期' in c]
            if date_cols:
                data[date_cols[0]] = pd.to_datetime(data[date_cols[0]])
                data = data.set_index(date_cols[0])
            
            data = self._normalize_dataframe(data)
            
            if data.empty:
                raise Exception("AkShare 数据格式不符合预期")
            
            print(f"✅ 成功获取 {len(data)} 条数据记录")
            return data
            
        except Exception as e:
            print(f"AkShare 获取数据失败: {str(e)}")
            raise e
    
    def fetch_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取行情数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            标准化的行情数据DataFrame
        """
        print("=" * 60)
        print("🔄 步骤 1/4: 数据获取和预处理")
        print("=" * 60)
        
        data = None
        
        # 根据配置选择数据源
        if self.config.DATA_PROVIDER == "local":
            if not self.config.LOCAL_DATA_PATH:
                raise ValueError("本地数据模式需要设置 LOCAL_DATA_PATH")
            data = self._load_local_data(self.config.LOCAL_DATA_PATH)
            
        elif self.config.DATA_PROVIDER == "akshare":
            if not self.config.symbol:
                raise ValueError("AkShare 模式需要设置 AK_SYMBOL")
            try:
                data = self._download_akshare(self.config.symbol, start_date, end_date)
            except Exception as e:
                print(f"⚠️  AkShare 失败，尝试使用 yfinance 备选方案")
                data = self._download_yfinance(self.config.SYMBOL, start_date, end_date)
                
        else:  # yfinance
            data = self._download_yfinance(self.config.SYMBOL, start_date, end_date)
        
        if data.empty:
            raise ValueError("无法获取有效数据")
        
        # 筛选日期范围
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        data = data[(data.index >= start_dt) & (data.index <= end_dt)]
        
        self.data = data
        return data
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            data: 原始OHLCV数据
            
        Returns:
            添加了技术指标的DataFrame
        """
        print("\n" + "=" * 60)
        print("📊 步骤 2/4: 计算技术指标")
        print("=" * 60)
        
        # 使用indicators模块计算所有指标
        data_with_indicators = self.indicators.calculate_all_indicators(data, self.config)
        
        print(f"✅ 成功计算 {len(data_with_indicators.columns) - 5} 个技术指标")
        
        return data_with_indicators
    
    def prepare_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        准备完整的回测数据（获取数据 + 计算指标）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            包含所有指标的完整数据
        """
        # 获取原始数据
        data = self.fetch_data(start_date, end_date)
        
        # 计算技术指标
        data = self.calculate_indicators(data)
        
        # 删除NaN值
        data = data.dropna()
        
        print(f"\n✅ 数据准备完成，共 {len(data)} 条有效记录")
        
        return data

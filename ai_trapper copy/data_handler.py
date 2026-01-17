"""
数据获取和处理模块
负责获取黄金期货数据并计算技术指标
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class DataHandler:
    """
    数据处理类，负责数据获取、清洗和技术指标计算
    """
    
    def __init__(self, symbol: str = "GC=F", csv_file: Optional[str] = None):
        self.symbol = symbol
        self.data = None
        self.csv_file = csv_file  # 添加CSV文件路径选项
        
    def load_from_csv(self, csv_file: str) -> pd.DataFrame:
        """
        从本地CSV文件加载数据（支持15分钟级别的黄金数据）
        
        Args:
            csv_file: CSV文件路径
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            print(f"正在从本地CSV文件加载数据: {csv_file}")
            
            # 读取CSV文件，使用分号作为分隔符
            data = pd.read_csv(csv_file, sep=';')
            
            print(f"原始数据列名: {data.columns.tolist()}")
            print(f"原始数据行数: {len(data)}")
            
            # 转换日期列
            if 'Date' in data.columns:
                data['Date'] = pd.to_datetime(data['Date'], format='%Y.%m.%d %H:%M')
                data.set_index('Date', inplace=True)
            else:
                raise ValueError("CSV文件中缺少Date列")
            
            # 确保必要的列存在
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                raise ValueError(f"CSV文件缺少必要的列: {missing_columns}")
            
            # 只保留需要的列
            data = data[required_columns]
            
            # 删除缺失值
            data = data.dropna()
            
            # 按时间排序
            data = data.sort_index()
            
            self.data = data
            print(f"✅ 成功从CSV加载 {len(data)} 条数据")
            print(f"数据时间范围: {data.index[0]} 至 {data.index[-1]}")
            print(f"数据列: {data.columns.tolist()}")
            
            return data
            
        except Exception as e:
            print(f"❌ 从CSV加载数据失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def fetch_data(self, start_date: str, end_date: str, max_retries: int = 3) -> pd.DataFrame:
        """
        获取黄金期货数据，带重试机制
        优先从CSV文件加载，如果没有CSV则从网络获取
        
        Args:
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            max_retries: 最大重试次数
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        import time
        
        # 优先尝试从CSV文件加载
        if self.csv_file:
            print(f"检测到CSV文件配置，尝试从本地加载数据...")
            data = self.load_from_csv(self.csv_file)
            if not data.empty:
                # 如果指定了日期范围，进行过滤
                if start_date and end_date:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    data = data[(data.index >= start_dt) & (data.index <= end_dt)]
                    print(f"已按日期范围过滤: {start_date} 至 {end_date}")
                    print(f"过滤后数据: {len(data)} 条")
                return data
            else:
                print("⚠️ CSV加载失败，尝试从网络获取数据...")
        else:
            # 尝试查找默认的CSV文件
            import os
            default_csv = 'XAU_15m_data.csv'
            if os.path.exists(default_csv):
                print(f"发现本地CSV文件: {default_csv}，将使用本地数据...")
                return self.load_from_csv(default_csv)
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 指数退避：2秒、4秒、8秒
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                
                print(f"正在获取 {self.symbol} 数据... (尝试 {attempt + 1}/{max_retries})")
                
                # 使用 download 方法获取数据
                data = yf.download(
                    self.symbol,
                    start=start_date,
                    end=end_date,
                    progress=False
                )
                
                if data.empty:
                    if attempt < max_retries - 1:
                        print(f"数据为空，准备重试...")
                        continue
                    else:
                        raise ValueError(f"无法获取 {self.symbol} 的数据")
                
                # 处理多层列索引的情况
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.droplevel(1)
                
                # 确保列名正确
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                if not all(col in data.columns for col in required_columns):
                    # 尝试重命名列
                    column_mapping = {}
                    for col in data.columns:
                        col_lower = col.lower()
                        if 'open' in col_lower:
                            column_mapping[col] = 'Open'
                        elif 'high' in col_lower:
                            column_mapping[col] = 'High'
                        elif 'low' in col_lower:
                            column_mapping[col] = 'Low'
                        elif 'close' in col_lower:
                            column_mapping[col] = 'Close'
                        elif 'volume' in col_lower:
                            column_mapping[col] = 'Volume'
                    
                    if column_mapping:
                        data = data.rename(columns=column_mapping)
                
                # 只保留需要的列
                data = data[required_columns]
                
                # 删除缺失值
                data = data.dropna()
                
                # 确保索引为datetime类型
                data.index = pd.to_datetime(data.index)
                
                self.data = data
                print(f"✅ 成功获取 {len(data)} 条 {self.symbol} 数据")
                return data
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    if "Too Many Requests" in error_msg or "Rate limit" in error_msg:
                        print(f"⚠️  遇到速率限制，准备重试...")
                    else:
                        print(f"⚠️  获取数据失败: {error_msg}，准备重试...")
                else:
                    print(f"❌ 获取数据失败: {error_msg}")
                    print("提示：如果持续遇到速率限制，可以：")
                    print("  1. 稍等几分钟后再试")
                    print("  2. 使用本地保存的历史数据")
                    print("  3. 考虑使用其他数据源")
                    return pd.DataFrame()
        
        return pd.DataFrame()
    
    def calculate_moving_averages(self, fast_period: int = 10, slow_period: int = 30) -> pd.DataFrame:
        """
        计算移动平均线
        
        Args:
            fast_period: 快速MA周期
            slow_period: 慢速MA周期
            
        Returns:
            包含MA指标的数据
        """
        if self.data is None or self.data.empty:
            raise ValueError("请先获取数据")
        
        data = self.data.copy()
        data[f'MA_{fast_period}'] = data['Close'].rolling(window=fast_period).mean()
        data[f'MA_{slow_period}'] = data['Close'].rolling(window=slow_period).mean()
        
        return data
    
    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """
        计算相对强弱指标 RSI
        
        Args:
            period: RSI计算周期
            
        Returns:
            RSI指标序列
        """
        if self.data is None or self.data.empty:
            raise ValueError("请先获取数据")
        
        close_prices = self.data['Close']
        
        # 计算价格变化
        delta = close_prices.diff()
        
        # 分离上涨和下跌
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # 计算RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标
        
        Args:
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            MACD线, 信号线, 柱状图
        """
        if self.data is None or self.data.empty:
            raise ValueError("请先获取数据")
        
        close_prices = self.data['Close']
        
        # 计算指数移动平均线
        ema_fast = close_prices.ewm(span=fast_period).mean()
        ema_slow = close_prices.ewm(span=slow_period).mean()
        
        # 计算MACD线
        macd_line = ema_fast - ema_slow
        
        # 计算信号线
        signal_line = macd_line.ewm(span=signal_period).mean()
        
        # 计算MACD柱状图
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算布林带
        
        Args:
            period: 移动平均线周期
            std_dev: 标准差倍数
            
        Returns:
            上轨, 中轨, 下轨
        """
        if self.data is None or self.data.empty:
            raise ValueError("请先获取数据")
        
        close_prices = self.data['Close']
        
        # 计算中轨（移动平均线）
        middle_band = close_prices.rolling(window=period).mean()
        
        # 计算标准差
        std = close_prices.rolling(window=period).std()
        
        # 计算上轨和下轨
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    def calculate_atr(self, period: int = 14) -> pd.Series:
        """
        计算平均真实波幅 ATR
        
        Args:
            period: ATR计算周期
            
        Returns:
            ATR指标序列
        """
        if self.data is None or self.data.empty:
            raise ValueError("请先获取数据")
        
        high = self.data['High']
        low = self.data['Low']
        close = self.data['Close']
        
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算ATR
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def prepare_data_for_strategy(self, config) -> pd.DataFrame:
        """
        为策略准备完整的技术指标数据
        
        Args:
            config: 配置对象
            
        Returns:
            包含所有技术指标的完整数据集
        """
        if self.data is None or self.data.empty:
            raise ValueError("请先获取数据")
        
        # 获取基础数据
        data = self.data.copy()
        
        # 计算移动平均线
        data[f'MA_{config.FAST_MA_PERIOD}'] = data['Close'].rolling(window=config.FAST_MA_PERIOD).mean()
        data[f'MA_{config.SLOW_MA_PERIOD}'] = data['Close'].rolling(window=config.SLOW_MA_PERIOD).mean()
        
        # 计算RSI
        data['RSI'] = self.calculate_rsi(config.RSI_PERIOD)
        
        # 计算MACD
        macd_line, signal_line, histogram = self.calculate_macd(
            config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL
        )
        data['MACD'] = macd_line
        data['MACD_Signal'] = signal_line
        data['MACD_Histogram'] = histogram
        
        # 计算布林带
        upper_bb, middle_bb, lower_bb = self.calculate_bollinger_bands()
        data['BB_Upper'] = upper_bb
        data['BB_Middle'] = middle_bb
        data['BB_Lower'] = lower_bb
        
        # 计算ATR
        data['ATR'] = self.calculate_atr()
        
        # 计算价格变化率
        data['Price_Change'] = data['Close'].pct_change()
        data['Price_Change_5d'] = data['Close'].pct_change(periods=5)
        
        # 计算成交量移动平均
        data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
        data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']
        
        # 删除包含NaN的行
        data = data.dropna()
        
        print(f"技术指标计算完成，可用数据: {len(data)} 条")
        return data
    
    def get_latest_data(self, days: int = 1) -> pd.DataFrame:
        """
        获取最新N天的数据
        
        Args:
            days: 获取最近几天的数据
            
        Returns:
            最新数据
        """
        if self.data is None or self.data.empty:
            raise ValueError("请先获取数据")
        
        return self.data.tail(days)
    
    def validate_data(self) -> bool:
        """
        验证数据质量
        
        Returns:
            数据是否有效
        """
        if self.data is None or self.data.empty:
            print("数据为空")
            return False
        
        # 检查必要的列是否存在
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            print(f"缺少必要的列: {missing_columns}")
            return False
        
        # 检查数据完整性
        null_counts = self.data.isnull().sum()
        if null_counts.sum() > 0:
            print(f"存在缺失值: {null_counts}")
            return False
        
        # 检查价格逻辑性
        invalid_data = (
            (self.data['High'] < self.data['Low']) |
            (self.data['High'] < self.data['Open']) |
            (self.data['High'] < self.data['Close']) |
            (self.data['Low'] > self.data['Open']) |
            (self.data['Low'] > self.data['Close'])
        )
        
        if invalid_data.sum() > 0:
            print(f"存在不合理的价格数据: {invalid_data.sum()} 条")
            return False
        
        print("数据验证通过")
        return True

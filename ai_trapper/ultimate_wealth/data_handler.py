"""
数据获取和处理模块
负责获取黄金期货数据并计算技术指标
"""

import pandas as pd
import numpy as np
import yfinance as yf
import os
from typing import Tuple, Optional
import warnings
import time
import random
from config import Config
warnings.filterwarnings('ignore')

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️  提示：未安装 akshare，将使用 yfinance 作为备选方案")

class DataHandler:
    """
    数据处理类，负责数据获取、清洗和技术指标计算
    """
    
    def __init__(
        self,
        symbol: str = "GC=F",
        fallback_symbol: Optional[str] = None,
        local_data_path: Optional[str] = None,
        use_local_on_fail: bool = True,
        retry_backoff_base: int = 2,
        data_provider: str = "yfinance",
        ak_symbol: Optional[str] = None
    ):
        self.symbol = symbol
        self.ak_symbol = ak_symbol
        self.fallback_symbol = fallback_symbol
        self.local_data_path = local_data_path
        self.use_local_on_fail = use_local_on_fail
        self.retry_backoff_base = retry_backoff_base
        self.data_provider = data_provider.lower()
        self.data = None
        
    def _normalize_price_dataframe(self, data: pd.DataFrame) -> pd.DataFrame:
        """标准化行情数据列名并做基础清洗"""
        if data is None or data.empty:
            return pd.DataFrame()
        
        # 处理多层列索引的情况
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        
        # 确保列名正确
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            column_mapping = {}
            rename_rules = {
                'Open': ['open', '开', '开盘', '开盘价'],
                'High': ['high', '高', '最高'],
                'Low': ['low', '低', '最低'],
                'Close': ['close', '收', '收盘', '收盘价', 'price'],
                'Volume': ['volume', 'vol', '成交量', '交易量']
            }
            for col in data.columns:
                col_lower = col.lower()
                for target, keywords in rename_rules.items():
                    if any(keyword in col_lower for keyword in keywords):
                        column_mapping[col] = target
                        break
            
            if column_mapping:
                data = data.rename(columns=column_mapping)
        
        # 只保留需要的列
        missing = [c for c in required_columns if c not in data.columns]
        if missing:
            print(f"当前数据列名: {list(data.columns)}，缺少: {missing}")
            return pd.DataFrame()
        
        data = data[required_columns]
        data = data.dropna()
        data.index = pd.to_datetime(data.index)
        return data
    
    def _download_symbol(self, symbol: str, start_date: str, end_date: str, max_retries: int) -> pd.DataFrame:
        """带指数退避的 yfinance 下载封装，便于主/备用代码共用"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # 增加延迟时间，特别是对于Yahoo Finance的速率限制
                    base_wait = (self.retry_backoff_base ** attempt) * 2
                    # 添加随机延迟避免同步重试
                    wait_time = base_wait + random.uniform(0, base_wait * 0.5)
                    print(f"等待 {wait_time:.1f} 秒后重试...")
                    time.sleep(wait_time)
                
                print(f"正在获取 {symbol} 数据... (尝试 {attempt + 1}/{max_retries})")
                
                data = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    timeout=30  # 添加超时设置
                )
                
                data = self._normalize_price_dataframe(data)
                if data.empty:
                    if attempt < max_retries - 1:
                        print("数据为空，准备重试...")
                        continue
                    else:
                        raise Exception("下载的数据为空")
                        
                return data
                
            except Exception as e:
                error_msg = str(e)
                # 特殊处理Yahoo Finance的速率限制错误
                if "Too Many Requests" in error_msg or "Rate limited" in error_msg:
                    if attempt < max_retries - 1:
                        extended_wait = (self.retry_backoff_base ** attempt) * 5
                        # 添加随机延迟避免同步重试
                        extended_wait += random.uniform(0, extended_wait * 0.5)
                        print(f"遇到速率限制，等待 {extended_wait:.1f} 秒后重试...")
                        time.sleep(extended_wait)
                        continue
                
                if attempt < max_retries - 1:
                    print(f"获取失败，准备重试...")
                    continue
                else:
                    print(f"❌ 获取 {symbol} 数据失败: {str(e)}")
                    raise e
        
        return pd.DataFrame()
    
    def _download_akshare_futures(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用 AkShare 获取期货数据"""
        if not AKSHARE_AVAILABLE:
            raise Exception("AkShare 不可用")
            
        try:
            # 使用 AkShare 获取期货连续合约数据
            print(f"正在使用 AkShare 获取 {symbol} 数据...")
            data = ak.futures_main_sina(symbol=symbol, start_date=start_date, end_date=end_date)
            
            if data is None or data.empty:
                raise Exception("AkShare 返回空数据")
            
            # 将日期列设为索引（有些版本返回的日期列名为date或日期）
            date_cols = [c for c in data.columns if 'date' in c.lower() or '日期' in c]
            if date_cols:
                data[date_cols[0]] = pd.to_datetime(data[date_cols[0]])
                data = data.set_index(date_cols[0])
            
            data = self._normalize_price_dataframe(data)
            if data.empty:
                raise Exception(f"AkShare 数据格式不符合预期，列: {data.columns.tolist()}")
            
            return data
            
        except Exception as e:
            print(f"AkShare 获取数据失败: {str(e)}")
            raise e
    
    def _download_wgc_gold_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        使用AkShare从世界黄金协会获取全球黄金ETF数据作为备选数据源
        """
        try:
            print("正在尝试从世界黄金协会获取黄金ETF数据...")
            # 获取全球黄金ETF数据（美元计价）
            data = ak.index_global_gold(symbol="全球黄金ETF")
            
            if data is None or data.empty:
                raise Exception("世界黄金协会返回空数据")
            
            print(f"WGC原始数据列名: {data.columns.tolist()}")
            
            # 格式化日期列为datetime类型
            date_column = [col for col in data.columns if 'date' in col.lower()][0]
            data[date_column] = pd.to_datetime(data[date_column])
            data = data.sort_values(date_column)
            
            # 筛选指定日期范围内的数据
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            data = data[(data[date_column] >= start_dt) & (data[date_column] <= end_dt)]
            
            if data.empty:
                raise Exception("筛选日期范围后数据为空")
            
            # 重命名列
            column_mapping = {}
            for col in data.columns:
                col_lower = col.lower()
                if 'open' in col_lower:
                    column_mapping[col] = 'Open'
                elif 'high' in col_lower:
                    column_mapping[col] = 'High'
                elif 'low' in col_lower:
                    column_mapping[col] = 'Low'
                elif 'close' in col_lower or 'price' in col_lower:
                    column_mapping[col] = 'Close'
                elif 'volume' in col_lower:
                    column_mapping[col] = 'Volume'
                    
            if column_mapping:
                data = data.rename(columns=column_mapping)
            
            # 设置日期为索引
            data[date_column] = pd.to_datetime(data[date_column])
            data.set_index(date_column, inplace=True)
            
            # 统一格式
            data = self._normalize_price_dataframe(data)
            if data.empty:
                raise Exception(f"世界黄金协会数据缺少必要列: {data.columns.tolist()}")
            
            return data
            
        except Exception as e:
            print(f"WGC数据获取失败: {str(e)}")
            raise e
    
    def fetch_data(self, start_date: str, end_date: str, max_retries: int = 4) -> pd.DataFrame:
        """
        获取行情数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            max_retries: 最大重试次数
            
        Returns:
            行情数据DataFrame
        """
        print("🔄 步骤 1/4: 数据获取和预处理")
        print("-" * 50)
        local_attempted = False

        # 直接使用本地CSV（适合5分钟/15分钟等已下载数据）
        if self.data_provider == "local":
            if not self.local_data_path:
                raise Exception("本地数据模式需要设置 LOCAL_DATA_PATH")
            data = self._load_local_data(self.local_data_path)
            # 按日期区间过滤（如果索引是Datetime）
            try:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                data = data[(data.index >= start_dt) & (data.index <= end_dt)]
            except Exception:
                pass
            if data.empty:
                raise Exception("本地数据为空或未覆盖所选时间范围")
            print(f"✅ 成功从本地文件加载 {len(data)} 条数据")
            return data
        
        # 尝试首选数据源
        if self.data_provider == "akshare" and AKSHARE_AVAILABLE:
            try:
                ak_symbol = self.ak_symbol or self.symbol
                data = self._download_akshare_futures(ak_symbol, start_date, end_date)
                print(f"✅ 成功使用 AkShare 获取到 {len(data)} 条数据")
                return data
            except Exception as e:
                print(f"⚠️  AkShare 获取数据失败: {str(e)}")
                if self.fallback_symbol:
                    print("尝试使用备用数据源...")
                else:
                    # 直接尝试 Yahoo Finance
                    pass
        
        # 尝试 Yahoo Finance (主符号)
        try:
            data = self._download_symbol(self.symbol, start_date, end_date, max_retries)
            print(f"✅ 成功使用 Yahoo Finance 获取到 {len(data)} 条数据")
            return data
        except Exception as e:
            print(f"⚠️  Yahoo Finance 获取 {self.symbol} 数据失败: {str(e)}")
        
        # 如果允许，优先尝试本地数据以避免进一步的外部请求
        if self.use_local_on_fail and self.local_data_path and os.path.exists(self.local_data_path):
            local_attempted = True
            try:
                data = self._load_local_data(self.local_data_path)
                print(f"✅ 成功从本地文件加载 {len(data)} 条数据")
                return data
            except Exception as e:
                print(f"⚠️  本地文件加载失败: {str(e)}")
        
        # 尝试备用符号
        if self.fallback_symbol:
            try:
                print(f"尝试使用备用符号 {self.fallback_symbol}...")
                data = self._download_symbol(self.fallback_symbol, start_date, end_date, max_retries)
                print(f"✅ 成功使用备用符号获取到 {len(data)} 条数据")
                return data
            except Exception as e:
                print(f"⚠️  备用符号 {self.fallback_symbol} 获取失败: {str(e)}")
        
        # 尝试世界黄金协会数据作为最后备选
        try:
            data = self._download_wgc_gold_data(start_date, end_date)
            print(f"✅ 成功使用世界黄金协会数据获取到 {len(data)} 条数据")
            return data
        except Exception as e:
            print(f"⚠️  世界黄金协会数据获取失败: {str(e)}")
        
        # 尝试本地文件（若之前未尝试或文件更新）
        if self.use_local_on_fail and self.local_data_path and not local_attempted:
            try:
                data = self._load_local_data(self.local_data_path)
                print(f"✅ 成功从本地文件加载 {len(data)} 条数据")
                return data
            except Exception as e:
                print(f"⚠️  本地文件加载失败: {str(e)}")
        
        # 最终回退：生成模拟数据，保证流程可继续
        try:
            data = self._generate_synthetic_data(start_date, end_date)
            return data
        except Exception as e:
            print(f"❌ 模拟数据生成失败: {str(e)}")
        
        # 所有方法都失败
        raise Exception("所有数据源都不可用，请检查网络连接或配置")
    
    def _load_local_data(self, filepath: str) -> pd.DataFrame:
        """加载本地CSV数据"""
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"本地文件不存在: {filepath}")
            
            print(f"正在加载本地数据: {filepath}")
            # 优先按分号分隔读取（适配示例文件）
            try:
                data = pd.read_csv(filepath, sep=';', header=0)
            except Exception:
                data = pd.read_csv(filepath)
            
            # 如果没有列名，尝试赋予标准列
            if not all(isinstance(c, str) for c in data.columns):
                data.columns = ['datetime', 'Open', 'High', 'Low', 'Close', 'Volume'][: data.shape[1]]
            
            # 检查是否有日期列
            date_columns = [col for col in data.columns if 'date' in str(col).lower() or 'time' in str(col).lower()]
            if date_columns:
                # 针对形如 2004.06.11 07:15 的格式
                try:
                    data[date_columns[0]] = pd.to_datetime(data[date_columns[0]], format="%Y.%m.%d %H:%M")
                except Exception:
                    data[date_columns[0]] = pd.to_datetime(data[date_columns[0]], dayfirst=True, errors='coerce')
                data.set_index(date_columns[0], inplace=True)
            
            data = self._normalize_price_dataframe(data)
            if data.empty:
                raise Exception("本地数据格式不正确")
                
            return data
            
        except Exception as e:
            print(f"❌ 加载本地数据失败: {str(e)}")
            raise e
        
    def _generate_synthetic_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        当所有外部数据源不可用时，生成一份稳定的模拟数据，保证策略流程可运行。
        """
        print("⚠️ 所有在线数据源不可用，生成模拟数据以继续流程...")
        date_index = pd.date_range(start=start_date, end=end_date, freq="B")
        if date_index.empty:
            raise Exception("无法生成模拟数据：日期范围为空")
        
        rng = np.random.default_rng(42)
        base_price = 1850
        drift = rng.normal(0, 1.2, size=len(date_index)).cumsum()
        close = base_price + drift
        open_price = close + rng.normal(0, 1, size=len(date_index))
        high = np.maximum(open_price, close) + rng.random(len(date_index)) * 5
        low = np.minimum(open_price, close) - rng.random(len(date_index)) * 5
        volume = rng.integers(1500, 4500, size=len(date_index))
        
        data = pd.DataFrame({
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close,
            'Volume': volume
        }, index=date_index)
        
        data = self._normalize_price_dataframe(data)
        if data.empty:
            raise Exception("模拟数据生成失败")
        
        print(f"✅ 已生成 {len(data)} 条模拟数据记录")
        return data
        
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
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            data: 原始行情数据
            
        Returns:
            添加了技术指标的DataFrame
        """
        print("🔄 步骤 2/4: 计算技术指标")
        print("-" * 50)
        
        df = data.copy()
        
        fast_ma = Config.FAST_MA_PERIOD
        slow_ma = Config.SLOW_MA_PERIOD
        rsi_period = Config.RSI_PERIOD
        
        # 移动平均线
        df[f'MA_{fast_ma}'] = df['Close'].rolling(window=fast_ma).mean()
        df[f'MA_{slow_ma}'] = df['Close'].rolling(window=slow_ma).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        
        # 布林带
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # 成交量均线
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # 价格涨跌幅（用于量价信号）
        df['Price_Change'] = df['Close'].pct_change()
        
        # ATR (Average True Range)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = pd.Series(true_range).rolling(14).mean()
        
        # 删除包含NaN的行
        df.dropna(inplace=True)
        
        print(f"✅ 技术指标计算完成，共 {len(df)} 条有效数据")
        return df
    
    def prepare_data(self, start_date: str, end_date: str, max_retries: int = 4) -> pd.DataFrame:
        """
        准备完整的训练数据（包括获取数据和计算指标）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            max_retries: 最大重试次数
            
        Returns:
            包含行情数据和技术指标的DataFrame
        """
        # 获取数据
        raw_data = self.fetch_data(start_date, end_date, max_retries)
        
        if raw_data.empty:
            raise Exception("获取的数据为空")
        
        # 计算技术指标
        processed_data = self.calculate_technical_indicators(raw_data)
        
        self.data = processed_data
        return processed_data
    
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

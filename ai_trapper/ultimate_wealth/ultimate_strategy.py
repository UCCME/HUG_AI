#!/usr/bin/env python3
"""
Ultimate strategy generated from ai_trapper modules.
"""


# --- config.py ---
"""
黄金合约策略配置文件
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    # 数据源配置
    DATA_PROVIDER = "local"            # 可选: "local", "akshare", "yfinance"
    SYMBOL = "GC=F"                    # 策略标的标识（逻辑用）
    AK_SYMBOL = "AU0"                  # AkShare 使用的合约代码（示例：AU0 主力连续）
    FALLBACK_SYMBOL = "GLD"            # yfinance 备用代码，主代码被限速时使用
    LOCAL_DATA_PATH = os.path.join(BASE_DIR, "..", "XAU_5m_data.csv")   # 本地5分钟CSV路径
    USE_LOCAL_ON_FAIL = True           # 下载失败时是否尝试本地文件
    MAX_FETCH_RETRIES = 6              # 主数据下载最大重试次数（增加重试次数）
    RETRY_BACKOFF_BASE = 2             # 指数退避基数（秒）
    
    # 数据区间
    START_DATE = "2016-01-01"
    END_DATE = "2024-12-12"
    
    # 策略参数
    FAST_MA_PERIOD = 72   # 约6小时窗口（5m数据）
    SLOW_MA_PERIOD = 216  # 约18小时窗口（5m数据）
    RSI_PERIOD = 14       # RSI周期
    RSI_OVERSOLD = 30     # RSI超卖阈值
    RSI_OVERBOUGHT = 70   # RSI超买阈值
    
    # MACD参数
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # 回测参数
    INITIAL_CAPITAL = 100000.0  # 初始资金
    COMMISSION_RATE = 0.002     # 手续费率 0.2%
    SLIPPAGE = 0.001            # 滑点 0.1%
    POSITION_SIZE = 0.95        # 仓位大小 (95%的资金参与交易)
    
    # 风控参数
    MAX_DRAWDOWN = 0.20         # 最大回撤限制 20%
    STOP_LOSS_PCT = 0.05        # 止损百分比 5%
    TAKE_PROFIT_PCT = 0.10      # 止盈百分比 10%

# --- data_handler.py ---
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

# --- gold_strategy.py ---
"""
黄金合约交易策略
基于多种技术指标的综合趋势跟踪策略
"""

import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

class SignalType(Enum):
    """信号类型枚举"""
    BUY = 1
    SELL = -1
    HOLD = 0

@dataclass
class TradingSignal:
    """交易信号类"""
    timestamp: datetime
    signal_type: SignalType
    price: float
    confidence: float  # 信号置信度 0-1
    indicators: Dict[str, float]  # 各指标的值
    reason: str  # 信号产生原因

class GoldTradingStrategy:
    """
    黄金合约交易策略类
    使用移动平均线交叉、RSI和MACD的综合信号
    """
    
    def __init__(self, config):
        self.config = config
        self.position = 0  # 当前持仓：1=多头，-1=空头，0=空仓
        self.entry_price = 0.0
        self.signals_history = []
        self.trades_history = []
        
        # 策略状态
        self.last_ma_cross_signal = None
        self.consecutive_signals = 0
        
    def calculate_ma_crossover_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算移动平均线交叉信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        if index < 1:
            return SignalType.HOLD, 0.0, "数据不足"
        
        fast_ma_col = f'MA_{self.config.FAST_MA_PERIOD}'
        slow_ma_col = f'MA_{self.config.SLOW_MA_PERIOD}'
        
        current_fast_ma = data.iloc[index][fast_ma_col]
        current_slow_ma = data.iloc[index][slow_ma_col]
        prev_fast_ma = data.iloc[index-1][fast_ma_col]
        prev_slow_ma = data.iloc[index-1][slow_ma_col]
        
        # 检查交叉
        if prev_fast_ma <= prev_slow_ma and current_fast_ma > current_slow_ma:
            # 黄金交叉 - 买入信号
            confidence = min(0.8, abs(current_fast_ma - current_slow_ma) / current_slow_ma * 100)
            return SignalType.BUY, confidence, f"快线向上穿越慢线({current_fast_ma:.2f} > {current_slow_ma:.2f})"
            
        elif prev_fast_ma >= prev_slow_ma and current_fast_ma < current_slow_ma:
            # 死亡交叉 - 卖出信号
            confidence = min(0.8, abs(current_slow_ma - current_fast_ma) / current_slow_ma * 100)
            return SignalType.SELL, confidence, f"快线向下穿越慢线({current_fast_ma:.2f} < {current_slow_ma:.2f})"
        
        return SignalType.HOLD, 0.0, "无交叉信号"
    
    def calculate_rsi_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算RSI信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        rsi = data.iloc[index]['RSI']
        
        if pd.isna(rsi):
            return SignalType.HOLD, 0.0, "RSI数据缺失"
        
        if rsi < self.config.RSI_OVERSOLD:
            # 超卖，买入信号
            confidence = (self.config.RSI_OVERSOLD - rsi) / self.config.RSI_OVERSOLD
            return SignalType.BUY, confidence, f"RSI超卖({rsi:.2f} < {self.config.RSI_OVERSOLD})"
            
        elif rsi > self.config.RSI_OVERBOUGHT:
            # 超买，卖出信号
            confidence = (rsi - self.config.RSI_OVERBOUGHT) / (100 - self.config.RSI_OVERBOUGHT)
            return SignalType.SELL, confidence, f"RSI超买({rsi:.2f} > {self.config.RSI_OVERBOUGHT})"
        
        return SignalType.HOLD, 0.0, f"RSI正常区间({rsi:.2f})"
    
    def calculate_macd_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算MACD信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        if index < 1:
            return SignalType.HOLD, 0.0, "MACD数据不足"
        
        current_macd = data.iloc[index]['MACD']
        current_signal = data.iloc[index]['MACD_Signal']
        prev_macd = data.iloc[index-1]['MACD']
        prev_signal = data.iloc[index-1]['MACD_Signal']
        
        if pd.isna(current_macd) or pd.isna(current_signal):
            return SignalType.HOLD, 0.0, "MACD数据缺失"
        
        # MACD线穿越信号线
        if prev_macd <= prev_signal and current_macd > current_signal:
            # MACD向上穿越信号线
            confidence = min(0.7, abs(current_macd - current_signal) / abs(current_signal) if current_signal != 0 else 0.5)
            return SignalType.BUY, confidence, f"MACD向上穿越信号线({current_macd:.4f} > {current_signal:.4f})"
            
        elif prev_macd >= prev_signal and current_macd < current_signal:
            # MACD向下穿越信号线
            confidence = min(0.7, abs(current_signal - current_macd) / abs(current_signal) if current_signal != 0 else 0.5)
            return SignalType.SELL, confidence, f"MACD向下穿越信号线({current_macd:.4f} < {current_signal:.4f})"
        
        return SignalType.HOLD, 0.0, "MACD无穿越信号"
    
    def calculate_bollinger_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算布林带信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        current_price = data.iloc[index]['Close']
        bb_upper = data.iloc[index]['BB_Upper']
        bb_lower = data.iloc[index]['BB_Lower']
        bb_middle = data.iloc[index]['BB_Middle']
        
        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return SignalType.HOLD, 0.0, "布林带数据缺失"
        
        # 价格触及下轨，可能反弹
        if current_price <= bb_lower:
            confidence = min(0.6, (bb_lower - current_price) / bb_lower * 10)
            return SignalType.BUY, confidence, f"价格触及布林带下轨({current_price:.2f} <= {bb_lower:.2f})"
        
        # 价格触及上轨，可能回落
        elif current_price >= bb_upper:
            confidence = min(0.6, (current_price - bb_upper) / bb_upper * 10)
            return SignalType.SELL, confidence, f"价格触及布林带上轨({current_price:.2f} >= {bb_upper:.2f})"
        
        return SignalType.HOLD, 0.0, f"价格在布林带中轨附近({current_price:.2f})"
    
    def calculate_volume_signal(self, data: pd.DataFrame, index: int) -> Tuple[SignalType, float, str]:
        """
        计算成交量信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            信号类型, 置信度, 原因说明
        """
        volume_ratio = data.iloc[index]['Volume_Ratio']
        price_change = data.iloc[index]['Price_Change']
        
        if pd.isna(volume_ratio) or pd.isna(price_change):
            return SignalType.HOLD, 0.0, "成交量数据缺失"
        
        # 放量上涨
        if volume_ratio > 1.5 and price_change > 0.01:
            confidence = min(0.5, volume_ratio / 3 * abs(price_change) * 10)
            return SignalType.BUY, confidence, f"放量上涨(量比:{volume_ratio:.2f}, 涨幅:{price_change*100:.2f}%)"
        
        # 放量下跌
        elif volume_ratio > 1.5 and price_change < -0.01:
            confidence = min(0.5, volume_ratio / 3 * abs(price_change) * 10)
            return SignalType.SELL, confidence, f"放量下跌(量比:{volume_ratio:.2f}, 跌幅:{price_change*100:.2f}%)"
        
        return SignalType.HOLD, 0.0, f"成交量正常(量比:{volume_ratio:.2f})"
    
    def generate_composite_signal(self, data: pd.DataFrame, index: int) -> TradingSignal:
        """
        生成综合交易信号
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            综合交易信号
        """
        timestamp = data.index[index]
        current_price = data.iloc[index]['Close']
        
        # 计算各个指标信号
        ma_signal, ma_confidence, ma_reason = self.calculate_ma_crossover_signal(data, index)
        rsi_signal, rsi_confidence, rsi_reason = self.calculate_rsi_signal(data, index)
        macd_signal, macd_confidence, macd_reason = self.calculate_macd_signal(data, index)
        bb_signal, bb_confidence, bb_reason = self.calculate_bollinger_signal(data, index)
        vol_signal, vol_confidence, vol_reason = self.calculate_volume_signal(data, index)
        
        # 信号权重配置
        weights = {
            'ma': 0.35,     # 移动平均线权重最高
            'macd': 0.25,   # MACD次之
            'rsi': 0.20,    # RSI
            'bb': 0.15,     # 布林带
            'volume': 0.05  # 成交量权重最低
        }
        
        # 计算加权信号得分
        signals = [ma_signal, rsi_signal, macd_signal, bb_signal, vol_signal]
        confidences = [ma_confidence, rsi_confidence, macd_confidence, bb_confidence, vol_confidence]
        weight_list = list(weights.values())
        
        buy_score = 0
        sell_score = 0
        
        for signal, confidence, weight in zip(signals, confidences, weight_list):
            if signal == SignalType.BUY:
                buy_score += confidence * weight
            elif signal == SignalType.SELL:
                sell_score += confidence * weight
        
        # 决定最终信号
        signal_threshold = 0.18  # 略降阈值，增加进场但仍过滤噪声
        reasons = []
        
        if buy_score > sell_score and buy_score > signal_threshold:
            final_signal = SignalType.BUY
            final_confidence = buy_score
        elif sell_score > buy_score and sell_score > signal_threshold:
            final_signal = SignalType.SELL
            final_confidence = sell_score
        else:
            final_signal = SignalType.HOLD
            final_confidence = 0.0

        # 趋势过滤：多头需均线与MACD同向，空头反之，避免震荡噪声
        ma_fast_val = data.iloc[index][f'MA_{self.config.FAST_MA_PERIOD}']
        ma_slow_val = data.iloc[index][f'MA_{self.config.SLOW_MA_PERIOD}']
        macd_val = data.iloc[index]['MACD']
        # 趋势强度过滤，避免均线过近时进场
        price_now = data.iloc[index]['Close']
        ma_gap_pct = abs(ma_fast_val - ma_slow_val) / price_now if price_now != 0 else 0
        min_ma_gap = 0.001  # 0.1% 价差
        # 价位须站上/跌破布林中轨以过滤震荡
        bb_mid = data.iloc[index]['BB_Middle']
        if final_signal == SignalType.BUY and not (ma_fast_val > ma_slow_val and macd_val > 0 and ma_gap_pct >= min_ma_gap and price_now >= bb_mid):
            final_signal = SignalType.HOLD
            final_confidence = 0.0
            reasons.append("趋势过滤-多头不成立")
        elif final_signal == SignalType.SELL and not (ma_fast_val < ma_slow_val and macd_val < 0 and ma_gap_pct >= min_ma_gap and price_now <= bb_mid):
            final_signal = SignalType.HOLD
            final_confidence = 0.0
            reasons.append("趋势过滤-空头不成立")
        
        # 组合信号原因
        if ma_signal != SignalType.HOLD:
            reasons.append(f"MA:{ma_reason}")
        if rsi_signal != SignalType.HOLD:
            reasons.append(f"RSI:{rsi_reason}")
        if macd_signal != SignalType.HOLD:
            reasons.append(f"MACD:{macd_reason}")
        if bb_signal != SignalType.HOLD:
            reasons.append(f"BB:{bb_reason}")
        if vol_signal != SignalType.HOLD:
            reasons.append(f"VOL:{vol_reason}")
        
        combined_reason = "; ".join(reasons) if reasons else "所有指标无明确信号"
        
        # 创建指标值字典
        indicators = {
            'MA_fast': data.iloc[index][f'MA_{self.config.FAST_MA_PERIOD}'],
            'MA_slow': data.iloc[index][f'MA_{self.config.SLOW_MA_PERIOD}'],
            'RSI': data.iloc[index]['RSI'],
            'MACD': data.iloc[index]['MACD'],
            'MACD_Signal': data.iloc[index]['MACD_Signal'],
            'BB_Upper': data.iloc[index]['BB_Upper'],
            'BB_Lower': data.iloc[index]['BB_Lower'],
            'Volume_Ratio': data.iloc[index]['Volume_Ratio'],
            'ATR': data.iloc[index]['ATR']
        }
        
        trading_signal = TradingSignal(
            timestamp=timestamp,
            signal_type=final_signal,
            price=current_price,
            confidence=final_confidence,
            indicators=indicators,
            reason=combined_reason
        )
        
        return trading_signal
    
    def calculate_atr_stop_loss(self, data: pd.DataFrame, index: int, position_type: SignalType) -> Tuple[float, float]:
        """
        计算ATR动态止损和止盈点位
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            position_type: 持仓方向
            
        Returns:
            止损价位, 止盈价位
        """
        if index < 14:  # ATR需要至少14个数据点
            # 默认止损止盈
            current_price = data.iloc[index]['Close']
            if position_type == SignalType.BUY:
                stop_loss = current_price * (1 - self.config.STOP_LOSS_PCT)
                take_profit = current_price * (1 + self.config.TAKE_PROFIT_PCT)
            else:
                stop_loss = current_price * (1 + self.config.STOP_LOSS_PCT)
                take_profit = current_price * (1 - self.config.TAKE_PROFIT_PCT)
            return stop_loss, take_profit
        
        atr = data.iloc[index]['ATR']
        current_price = data.iloc[index]['Close']
        
        if pd.isna(atr) or atr == 0:
            # 如果ATR不可用，使用默认百分比
            if position_type == SignalType.BUY:
                stop_loss = current_price * (1 - self.config.STOP_LOSS_PCT)
                take_profit = current_price * (1 + self.config.TAKE_PROFIT_PCT)
            else:
                stop_loss = current_price * (1 + self.config.STOP_LOSS_PCT)
                take_profit = current_price * (1 - self.config.TAKE_PROFIT_PCT)
        else:
            # 使用ATR计算动态止损止盈
            if position_type == SignalType.BUY:
                stop_loss = current_price - (atr * 1.5)  # 更紧的ATR止损
                take_profit = current_price + (atr * 2.5)  # 略收紧止盈
            else:
                stop_loss = current_price + (atr * 1.5)  # 更紧的ATR止损
                take_profit = current_price - (atr * 2.5)  # 略收紧止盈
                
        return stop_loss, take_profit
    
    def should_exit_position(self, data: pd.DataFrame, index: int, entry_price: float, 
                           position_type: SignalType) -> Tuple[bool, str]:
        """
        判断是否应该平仓
        
        Args:
            data: 行情数据
            index: 当前索引
            entry_price: 入场价格
            position_type: 持仓方向
            
        Returns:
            是否平仓, 平仓原因
        """
        current_price = data.iloc[index]['Close']
        
        # 计算止损和止盈点位
        stop_loss, take_profit = self.calculate_atr_stop_loss(data, index, position_type)
        
        # 止损判断
        if position_type == SignalType.BUY and current_price <= stop_loss:
            return True, f"多头止损: 当前价{current_price:.2f} <= 止损价{stop_loss:.2f}"
        elif position_type == SignalType.SELL and current_price >= stop_loss:
            return True, f"空头止损: 当前价{current_price:.2f} >= 止损价{stop_loss:.2f}"
            
        # 止盈判断
        if position_type == SignalType.BUY and current_price >= take_profit:
            return True, f"多头止盈: 当前价{current_price:.2f} >= 止盈价{take_profit:.2f}"
        elif position_type == SignalType.SELL and current_price <= take_profit:
            return True, f"空头止盈: 当前价{current_price:.2f} <= 止盈价{take_profit:.2f}"
            
        # 反向信号平仓
        signal = self.generate_composite_signal(data, index)
        if ((position_type == SignalType.BUY and signal.signal_type == SignalType.SELL) or 
            (position_type == SignalType.SELL and signal.signal_type == SignalType.BUY)):
            return True, f"反向信号平仓: {signal.reason}"
            
        return False, ""
    
    def calculate_position_size(self, capital: float, price: float, confidence: float, atr: float = None) -> int:
        """
        根据信号置信度动态计算仓位大小
        
        Args:
            capital: 可用资金
            price: 当前价格
            confidence: 信号置信度
            atr: ATR值，用于风险调整仓位
            
        Returns:
            仓位数量
        """
        # 基础仓位根据置信度调整
        base_position_ratio = self.config.POSITION_SIZE * confidence
        
        # 如果有ATR，则进一步调整仓位以控制风险
        if atr and atr > 0:
            # 使用ATR调整仓位，确保单笔损失不超过账户的一定比例
            risk_per_trade = 0.007  # 略提升每笔风险至0.7%资金
            dollar_per_point = 100  # 黄金期货每点价值(示例值，实际可能不同)
            
            # 计算基于ATR的合适仓位大小
            risk_amount = capital * risk_per_trade
            position_by_risk = risk_amount / (atr * dollar_per_point)
            
            # 取置信度仓位和风险仓位中的较小值
            position_ratio = min(base_position_ratio, position_by_risk * price / capital)
        else:
            position_ratio = base_position_ratio
            
        # 计算实际仓位数量
        position_value = capital * position_ratio
        position_size = int(position_value / price)
        
        return max(1, position_size)  # 至少返回1手
    
    def execute_signal(self, signal: TradingSignal, capital: float = 100000) -> Dict:
        """
        执行交易信号（支持智能仓位管理）
        
        Args:
            signal: 交易信号
            capital: 账户资金，默认10万
            
        Returns:
            交易执行结果
        """
        trade_result = {
            'timestamp': signal.timestamp,
            'action': 'hold',
            'price': signal.price,
            'position_before': self.position,
            'position_after': self.position,
            'reason': signal.reason,
            'confidence': signal.confidence,
            'position_size': 0
        }
        
        # 记录信号历史
        self.signals_history.append(signal)
        
        # 获取ATR用于仓位计算和风险控制
        atr = signal.indicators.get('ATR', None)
        
        # 执行交易逻辑
        if signal.signal_type == SignalType.BUY and self.position != 1:
            if self.position == -1:
                # 平空仓
                trade_result['action'] = 'close_short'
                self.trades_history.append({
                    'timestamp': signal.timestamp,
                    'action': 'close_short',
                    'price': signal.price,
                    'entry_price': self.entry_price,
                    'pnl': (self.entry_price - signal.price) / self.entry_price,
                    'position_size': abs(self.position)
                })
            
            # 计算智能仓位
            position_size = self.calculate_position_size(capital, signal.price, signal.confidence, atr)
            
            # 开多仓
            action_name = 'buy' if self.position == 0 else 'close_short_and_buy'
            trade_result.update({
                'action': action_name,
                'position_after': 1,
                'position_size': position_size
            })
            
            self.position = 1
            self.entry_price = signal.price
            
        elif signal.signal_type == SignalType.SELL:
            if self.position == 1:
                # 平多仓，仅平仓不再开空
                trade_result['action'] = 'close_long'
                self.trades_history.append({
                    'timestamp': signal.timestamp,
                    'action': 'close_long',
                    'price': signal.price,
                    'entry_price': self.entry_price,
                    'pnl': (signal.price - self.entry_price) / self.entry_price,
                    'position_size': abs(self.position)
                })
                self.position = 0
                self.entry_price = 0.0
            else:
                # 空仓或已空头，不开新空
                trade_result['action'] = 'hold'
        
        return trade_result
    
    def get_strategy_stats(self) -> Dict:
        """
        获取策略统计信息
        
        Returns:
            策略统计信息
        """
        if not self.trades_history:
            return {
                'total_trades': 0, 
                'win_rate': 0, 
                'avg_return': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'avg_position_size': 0,
                'current_position': self.position
            }
        
        total_trades = len(self.trades_history)
        profitable_trades = [t for t in self.trades_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trades_history if t['pnl'] <= 0]
        
        win_rate = len(profitable_trades) / total_trades if total_trades > 0 else 0
        avg_return = np.mean([t['pnl'] for t in self.trades_history]) if self.trades_history else 0
        total_pnl = sum(t['pnl'] for t in self.trades_history)
        
        # 计算最大回撤
        cumulative_returns = np.cumsum([t['pnl'] for t in self.trades_history])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = running_max - cumulative_returns
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
        
        # 计算盈利因子
        gross_profit = sum(t['pnl'] for t in profitable_trades) if profitable_trades else 0
        gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss
        
        # 平均仓位大小
        avg_position_size = np.mean([t.get('position_size', 1) for t in self.trades_history])
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'avg_position_size': avg_position_size,
            'current_position': self.position
        }
        
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Tuple[List[TradingSignal], List[Dict]]:
        """
        执行回测
        
        Args:
            data: 包含技术指标的行情数据
            initial_capital: 初始资金
            
        Returns:
            交易信号列表, 交易记录列表
        """
        signals = []
        trades = []
        current_capital = initial_capital
        
        for i in range(len(data)):
            # 生成交易信号
            signal = self.generate_composite_signal(data, i)
            signals.append(signal)
            
            # 检查是否需要止损止盈或反向平仓
            if self.position != 0:
                should_exit, exit_reason = self.should_exit_position(
                    data, i, self.entry_price, 
                    SignalType.BUY if self.position > 0 else SignalType.SELL
                )
                
                if should_exit:
                    # 执行平仓
                    exit_signal = TradingSignal(
                        timestamp=signal.timestamp,
                        signal_type=SignalType.HOLD,
                        price=signal.price,
                        confidence=signal.confidence,
                        indicators=signal.indicators,
                        reason=exit_reason
                    )
                    trade_result = self.execute_signal(exit_signal, current_capital)
                    if trade_result['action'] != 'hold':
                        trades.append(trade_result)
                    
            # 根据信号和当前持仓情况决定交易行为
            if signal.signal_type == SignalType.BUY and self.position != 1:
                trade_result = self.execute_signal(signal, current_capital)
                if trade_result['action'] != 'hold':
                    trades.append(trade_result)
                    
            elif signal.signal_type == SignalType.SELL and self.position != -1:
                trade_result = self.execute_signal(signal, current_capital)
                if trade_result['action'] != 'hold':
                    trades.append(trade_result)
        
        return signals, trades

# --- backtest_engine.py ---
"""
回测引擎
用于执行策略回测并计算各项性能指标
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')


@dataclass
class BacktestResult:
    """回测结果类"""
    # 基础信息
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # 性能指标
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    
    # 交易统计
    total_trades: int
    profitable_trades: int
    losing_trades: int
    avg_trade_return: float
    avg_winning_trade: float
    avg_losing_trade: float
    max_winning_trade: float
    max_losing_trade: float
    
    # 持仓统计
    avg_holding_period: float
    max_holding_period: float
    
    # 详细数据
    equity_curve: pd.DataFrame
    trades_details: pd.DataFrame
    daily_returns: pd.Series

class BacktestEngine:
    """
    回测引擎类
    执行策略回测并计算性能指标
    """
    
    def __init__(self, config):
        self.config = config
        self.initial_capital = config.INITIAL_CAPITAL
        self.commission_rate = config.COMMISSION_RATE
        self.slippage = config.SLIPPAGE
        self.position_size = config.POSITION_SIZE
        self.trade_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades_log.txt")
        
        # 回测状态
        self.current_capital = self.initial_capital
        self.available_cash = self.initial_capital
        self.current_position = 0  # 当前持仓数量（股数/合约数）
        self.position_value = 0    # 持仓市值
        self.entry_price = 0       # 入场价格
        self.entry_time = None     # 入场时间
        
        # 记录数据
        self.equity_history = []
        self.trades_history = []
        self.position_history = []
        self.signal_history = []
        
        # 初始化交易日志文件
        with open(self.trade_log_path, "w", encoding="utf-8") as f:
            f.write("timestamp\taction\tprice\tquantity\tcash_after\tposition_after\treason\n")
    
    def _log_trade(self, trade_record: Dict):
        """追加写入单笔交易到本地txt"""
        try:
            with open(self.trade_log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"{trade_record.get('timestamp')}\t"
                    f"{trade_record.get('action')}\t"
                    f"{trade_record.get('price')}\t"
                    f"{trade_record.get('quantity', 0)}\t"
                    f"{self.available_cash:.2f}\t"
                    f"{self.current_position}\t"
                    f"{trade_record.get('reason', '')}\n"
                )
        except Exception:
            pass
        
    def calculate_position_size(self, price: float, signal_confidence: float, atr: float = None) -> int:
        """
        计算开仓数量（支持动态仓位和风险控制）
        
        Args:
            price: 当前价格
            signal_confidence: 信号置信度
            atr: ATR值，用于风险调整仓位
            
        Returns:
            开仓数量
        """
        # 根据信号置信度调整仓位大小
        adjusted_position_size = self.position_size * signal_confidence
        
        # 如果有ATR，则进一步调整仓位以控制风险
        if atr and atr > 0:
            # 使用ATR调整仓位，确保单笔损失不超过账户的一定比例
            risk_per_trade = 0.01  # 每笔交易最多承担1%账户资金的风险
            
            # 计算基于ATR的风险金额
            risk_amount = self.current_capital * risk_per_trade
            # 假设止损距离为1.5倍ATR
            stop_distance = 1.5 * atr
            # 计算合理的仓位大小
            position_by_risk = risk_amount / (stop_distance * price)
            
            # 综合考虑信号强度和风险控制
            max_position_ratio = min(adjusted_position_size, position_by_risk * price / self.available_cash)
        else:
            max_position_ratio = adjusted_position_size
            
        # 可用资金计算持仓数量
        available_for_position = self.available_cash * max_position_ratio
        
        # 考虑手续费的实际可买数量
        position_count = int(available_for_position / (price * (1 + self.commission_rate + self.slippage)))
        
        return max(1, position_count)  # 至少1手
    
    def calculate_commission(self, trade_value: float) -> float:
        """
        计算交易手续费
        
        Args:
            trade_value: 交易金额
            
        Returns:
            手续费
        """
        return trade_value * self.commission_rate
    
    def calculate_slippage_cost(self, trade_value: float) -> float:
        """
        计算滑点成本
        
        Args:
            trade_value: 交易金额
            
        Returns:
            滑点成本
        """
        return trade_value * self.slippage
    
    def execute_trade(self, trade: Dict, data: pd.DataFrame, index: int):
        """
        执行交易（增强版，支持动态仓位和风险管理）
        
        Args:
            trade: 交易指令
            data: 行情数据
            index: 当前索引
        """
        action = trade['action']
        price = trade['price']
        confidence = trade.get('confidence', 0.5)
        
        # 获取ATR值用于仓位计算
        atr = data.iloc[index]['ATR'] if 'ATR' in data.columns and not pd.isna(data.iloc[index]['ATR']) else None
        
        if action == 'BUY':
            # 计算开仓数量
            quantity = self.calculate_position_size(price, confidence, atr)
            
            # 计算交易成本
            cost = quantity * price * (1 + self.commission_rate + self.slippage)
            
            # 检查资金是否足够
            if cost <= self.available_cash:
                # 更新持仓
                new_position = self.current_position + quantity
                avg_price = (self.entry_price * self.current_position + price * quantity) / new_position if new_position > 0 else price
                
                self.current_position = new_position
                self.entry_price = avg_price
                self.entry_time = trade['timestamp']
                
                # 更新资金
                self.available_cash -= cost
                self.position_value = self.current_position * price
                
                # 记录交易
                trade_record = trade.copy()
                trade_record['quantity'] = quantity
                trade_record['cost'] = cost
                self.trades_history.append(trade_record)
                self._log_trade(trade_record)
                
        elif action == 'SELL':
            quantity = min(trade['quantity'], self.current_position)  # 不能卖出超过持有的数量
            
            if quantity > 0:
                # 计算交易收入
                revenue = quantity * price * (1 - self.commission_rate - self.slippage)
                
                # 更新持仓
                self.current_position -= quantity
                
                # 更新资金
                self.available_cash += revenue
                self.position_value = self.current_position * price
                
                # 如果清仓，重置入场价格和时间
                if self.current_position == 0:
                    self.entry_price = 0
                    self.entry_time = None
                    
                # 记录交易
                trade_record = trade.copy()
                trade_record['quantity'] = quantity
                trade_record['revenue'] = revenue
                self.trades_history.append(trade_record)
                self._log_trade(trade_record)
                
        elif action == 'SELL_SHORT':
            # 计算开仓数量
            quantity = self.calculate_position_size(price, confidence, atr)
            
            # 计算交易收入（假设可以卖空）
            revenue = quantity * price * (1 - self.commission_rate - self.slippage)
            
            # 更新持仓（负数表示空头）
            new_position = self.current_position - quantity
            avg_price = (abs(self.entry_price * self.current_position) + price * quantity) / abs(new_position) if new_position < 0 else price
            
            self.current_position = new_position
            self.entry_price = avg_price
            self.entry_time = trade['timestamp']
            
            # 更新资金
            self.available_cash += revenue
            self.position_value = abs(self.current_position) * price
            
            # 记录交易
            trade_record = trade.copy()
            trade_record['quantity'] = quantity
            trade_record['revenue'] = revenue
            self.trades_history.append(trade_record)
            self._log_trade(trade_record)
            
        elif action == 'BUY_TO_COVER':
            quantity = min(trade['quantity'], abs(self.current_position))  # 不能平仓超过空头数量
            
            if quantity > 0:
                # 计算交易成本
                cost = quantity * price * (1 + self.commission_rate + self.slippage)
                
                # 更新持仓
                self.current_position += quantity
                
                # 更新资金
                self.available_cash -= cost
                self.position_value = abs(self.current_position) * price
                
                # 如果平仓完成，重置入场价格和时间
                if self.current_position == 0:
                    self.entry_price = 0
                    self.entry_time = None
                    
                # 记录交易
                trade_record = trade.copy()
                trade_record['quantity'] = quantity
                trade_record['cost'] = cost
                self.trades_history.append(trade_record)
                self._log_trade(trade_record)
    
    
    def update_equity(self, timestamp: datetime, price: float):
        """
        更新权益记录
        
        Args:
            timestamp: 时间戳
            price: 当前价格
        """
        # 计算当前持仓市值
        self.position_value = self.current_position * price
        
        # 计算总资产
        total_equity = self.available_cash + self.position_value
        
        # 记录权益
        self.equity_history.append({
            'timestamp': timestamp,
            'equity': total_equity,
            'cash': self.available_cash,
            'position_value': self.position_value,
            'position_size': self.current_position,
            'price': price
        })
    
    def run_backtest(self, data: pd.DataFrame, strategy: GoldTradingStrategy) -> BacktestResult:
        """
        运行回测
        
        Args:
            data: 行情数据
            strategy: 交易策略
            
        Returns:
            BacktestResult: 回测结果
        """
        print("🔄 正在执行回测...")
        
        # 重置回测状态
        self.current_capital = self.initial_capital
        self.available_cash = self.initial_capital
        self.current_position = 0
        self.position_value = 0
        self.equity_history = []
        self.trades_history = []
        self.signal_history = []
        
        # 为每个数据点执行回测
        for i in range(len(data)):
            timestamp = data.index[i]
            price = data.iloc[i]['Close']
            
            # 生成交易信号
            signal = strategy.generate_composite_signal(data, i)
            self.signal_history.append(signal)
            
            # 根据信号和当前持仓情况决定交易行为
            if signal.signal_type == SignalType.BUY and self.current_position <= 0:
                # 平掉空头仓位
                if self.current_position < 0:
                    trade = {
                        'timestamp': signal.timestamp,
                        'action': 'BUY_TO_COVER',
                        'price': signal.price,
                        'quantity': abs(self.current_position),
                        'reason': f"平空头仓位; {signal.reason}",
                        'confidence': signal.confidence
                    }
                    self.execute_trade(trade, data, i)
                    
                # 开多头仓位
                trade = {
                    'timestamp': signal.timestamp,
                    'action': 'BUY',
                    'price': signal.price,
                    'quantity': 1,  # 实际数量在execute_trade中计算
                    'reason': signal.reason,
                    'confidence': signal.confidence
                }
                self.execute_trade(trade, data, i)
                
            elif signal.signal_type == SignalType.SELL and self.current_position >= 0:
                # 平掉多头仓位
                if self.current_position > 0:
                    trade = {
                        'timestamp': signal.timestamp,
                        'action': 'SELL',
                        'price': signal.price,
                        'quantity': self.current_position,
                        'reason': f"平多头仓位; {signal.reason}",
                        'confidence': signal.confidence
                    }
                    self.execute_trade(trade, data, i)
                    
                # 开空头仓位
                trade = {
                    'timestamp': signal.timestamp,
                    'action': 'SELL_SHORT',
                    'price': signal.price,
                    'quantity': 1,  # 实际数量在execute_trade中计算
                    'reason': signal.reason,
                    'confidence': signal.confidence
                }
                self.execute_trade(trade, data, i)
                
            # 检查是否需要止损止盈
            elif self.current_position != 0:
                should_exit, exit_reason = strategy.should_exit_position(
                    data, i, self.entry_price, 
                    SignalType.BUY if self.current_position > 0 else SignalType.SELL
                )
                
                if should_exit:
                    action = 'SELL' if self.current_position > 0 else 'BUY_TO_COVER'
                    trade = {
                        'timestamp': signal.timestamp,
                        'action': action,
                        'price': signal.price,
                        'quantity': abs(self.current_position),
                        'reason': exit_reason,
                        'confidence': signal.confidence
                    }
                    self.execute_trade(trade, data, i)
            
            # 更新权益记录
            self.update_equity(timestamp, price)
        
        # 构建结果
        return self._generate_result(data)
    
    def _generate_result(self, data: pd.DataFrame) -> BacktestResult:
        """
        生成回测结果
        
        Args:
            data: 行情数据
            
        Returns:
            BacktestResult: 回测结果
        """
        # 转换记录为DataFrame
        equity_df = pd.DataFrame(self.equity_history)
        if not equity_df.empty:
            equity_df.set_index('timestamp', inplace=True)
        
        trades_df = pd.DataFrame(self.trades_history)
        if not trades_df.empty:
            trades_df.set_index('timestamp', inplace=True)
        
        # 计算每日收益
        daily_returns = equity_df['equity'].pct_change().dropna() if not equity_df.empty else pd.Series()
        
        # 基本信息
        start_date = data.index[0] if not data.empty else datetime.now()
        end_date = data.index[-1] if not data.empty else datetime.now()
        
        # 性能指标
        initial_capital = self.initial_capital
        final_capital = equity_df['equity'].iloc[-1] if not equity_df.empty else initial_capital
        total_return = (final_capital - initial_capital) / initial_capital if initial_capital > 0 else 0
        
        # 计算年化收益率
        total_days = (end_date - start_date).days
        annual_return = (1 + total_return) ** (365 / total_days) - 1 if total_days > 0 else 0
        
        # 计算夏普比率 (假设无风险利率为0)
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if len(daily_returns) > 1 and daily_returns.std() > 0 else 0
        
        # 计算最大回撤
        peak = equity_df['equity'].expanding(min_periods=1).max() if not equity_df.empty else pd.Series()
        drawdown = (equity_df['equity'] - peak) / peak if not peak.empty else pd.Series()
        max_drawdown = drawdown.min() if not drawdown.empty else 0
        
        # 交易统计
        total_trades = len(trades_df[trades_df['action'].isin(['BUY', 'SELL_SHORT'])]) if not trades_df.empty else 0
        
        # 计算每笔交易的收益（考虑数量与交易成本）
        trade_returns = []
        winning_trades = 0
        losing_trades = 0
        winning_amount = 0.0
        losing_amount = 0.0
        max_winning_trade = 0.0
        max_losing_trade = 0.0
        
        # 使用开平仓配对计算真实收益
        for i, trade in enumerate(self.trades_history):
            if trade['action'] in ['SELL', 'BUY_TO_COVER']:  # 平仓交易
                open_action = 'BUY' if trade['action'] == 'SELL' else 'SELL_SHORT'
                # 找到最近未处理的对应开仓
                open_trades = [t for t in self.trades_history[:i] 
                               if t['action'] == open_action and 'processed' not in t]
                
                if not open_trades:
                    continue
                
                open_trade = open_trades[-1]
                open_trade['processed'] = True
                
                qty = min(trade.get('quantity', 0), open_trade.get('quantity', 0))
                if qty <= 0:
                    continue
                
                open_cost = open_trade.get('cost') or open_trade['price'] * qty
                close_value = trade.get('revenue') or trade['price'] * qty
                
                pnl_amount = close_value - open_cost if trade['action'] == 'SELL' else open_cost - close_value
                pnl_ratio = pnl_amount / open_cost if open_cost else 0
                
                trade_returns.append(pnl_ratio)
                
                if pnl_ratio > 0:
                    winning_trades += 1
                    winning_amount += pnl_amount
                    max_winning_trade = max(max_winning_trade, pnl_ratio)
                else:
                    losing_trades += 1
                    losing_amount += pnl_amount
                    max_losing_trade = min(max_losing_trade, pnl_ratio)
        
        profitable_trades = winning_trades
        losing_trades = losing_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0
        avg_winning_trade = winning_amount / winning_trades if winning_trades > 0 else 0
        avg_losing_trade = losing_amount / losing_trades if losing_trades > 0 else 0
        
        # 计算盈利因子
        profit_factor = abs(winning_amount / losing_amount) if losing_amount < 0 else float('inf')
        
        # 持仓统计 (简化)
        avg_holding_period = 5.0  # 示例值
        max_holding_period = 20.0  # 示例值
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            losing_trades=losing_trades,
            avg_trade_return=avg_trade_return,
            avg_winning_trade=avg_winning_trade,
            avg_losing_trade=avg_losing_trade,
            max_winning_trade=max_winning_trade,
            max_losing_trade=max_losing_trade,
            avg_holding_period=avg_holding_period,
            max_holding_period=max_holding_period,
            equity_curve=equity_df,
            trades_details=trades_df,
            daily_returns=daily_returns
        )

# --- performance_analyzer.py ---
"""
性能分析和可视化模块
用于分析回测结果并生成图表
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.dates as mdates
import seaborn as sns
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


# 设置中文字体和样式，自动选择可用的中文字体，避免乱码
_preferred_fonts = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'Sarasa Gothic SC', 'Noto Sans CJK SC', 'DejaVu Sans']
available_font_names = {f.name for f in font_manager.fontManager.ttflist}
for font_name in _preferred_fonts:
    # 一些字体名字在列表里带后缀，使用包含匹配
    if any(font_name in name for name in available_font_names):
        plt.rcParams['font.sans-serif'] = [font_name]
        break
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8')

class PerformanceAnalyzer:
    """
    性能分析器类
    分析回测结果并生成各种图表和报告
    """
    
    def __init__(self, backtest_result: BacktestResult):
        self.result = backtest_result
        self.equity_curve = backtest_result.equity_curve
        self.trades_details = backtest_result.trades_details
        self.daily_returns = backtest_result.daily_returns
    
    def print_performance_summary(self):
        """打印性能摘要报告"""
        print("=" * 60)
        print("                  回测性能报告")
        print("=" * 60)
        
        # 基础信息
        print(f"回测期间: {self.result.start_date.strftime('%Y-%m-%d')} 到 {self.result.end_date.strftime('%Y-%m-%d')}")
        total_days = (self.result.end_date - self.result.start_date).days
        print(f"回测天数: {total_days} 天")
        
        print("\n" + "-" * 30 + " 资金表现 " + "-" * 30)
        print(f"初始资金: ${self.result.initial_capital:,.2f}")
        print(f"最终资金: ${self.result.final_capital:,.2f}")
        print(f"绝对收益: ${self.result.final_capital - self.result.initial_capital:,.2f}")
        print(f"总收益率: {self.result.total_return:.2%}")
        print(f"年化收益率: {self.result.annual_return:.2%}")
        
        print("\n" + "-" * 30 + " 风险指标 " + "-" * 30)
        print(f"夏普比率: {self.result.sharpe_ratio:.3f}")
        print(f"最大回撤: {self.result.max_drawdown:.2%}")
        
        # 计算波动率
        if len(self.daily_returns) > 1:
            volatility = self.daily_returns.std() * np.sqrt(252)
            print(f"年化波动率: {volatility:.2%}")
            
            # 计算卡尔玛比率 (年化收益率 / 最大回撤)
            calmar_ratio = self.result.annual_return / abs(self.result.max_drawdown) if self.result.max_drawdown != 0 else 0
            print(f"卡尔玛比率: {calmar_ratio:.3f}")
        
        print("\n" + "-" * 30 + " 交易统计 " + "-" * 30)
        print(f"总交易次数: {self.result.total_trades}")
        print(f"盈利交易: {self.result.profitable_trades}")
        print(f"亏损交易: {self.result.losing_trades}")
        print(f"胜率: {self.result.win_rate:.2%}")
        
        if self.result.profit_factor != float('inf'):
            print(f"盈利因子: {self.result.profit_factor:.2f}")
        else:
            print(f"盈利因子: 无限大 (无亏损交易)")
        
        if self.result.total_trades > 0:
            print(f"平均单笔收益率: {self.result.avg_trade_return:.2%}")
            print(f"平均盈利交易: ${self.result.avg_winning_trade:,.2f}")
            if self.result.avg_losing_trade < 0:
                print(f"平均亏损交易: ${self.result.avg_losing_trade:,.2f}")
            print(f"最大盈利交易: ${self.result.max_winning_trade:,.2f}")
            if self.result.max_losing_trade < 0:
                print(f"最大亏损交易: ${self.result.max_losing_trade:,.2f}")
            print(f"平均持仓天数: {self.result.avg_holding_period:.1f} 天")
            print(f"最长持仓天数: {self.result.max_holding_period} 天")
        
        print("\n" + "=" * 60)
    
    def plot_equity_curve(self, figsize=(12, 8)):
        """
        绘制权益曲线图
        
        Args:
            figsize: 图表尺寸
        """
        if self.equity_curve.empty:
            print("⚠️  无权益数据可供绘制")
            return
            
        fig, axes = plt.subplots(2, 1, figsize=figsize, gridspec_kw={'height_ratios': [3, 1]})
        
        # 权益曲线
        axes[0].plot(self.equity_curve.index, self.equity_curve['equity'], 
                    linewidth=2, color='blue', label='投资组合价值')
        axes[0].set_title('投资组合权益曲线', fontsize=16, fontweight='bold')
        axes[0].set_ylabel('资产价值 (USD)', fontsize=12)
        axes[0].legend(loc='upper left')
        axes[0].grid(True, alpha=0.3)
        
        # 添加回撤曲线
        peak = self.equity_curve['equity'].expanding(min_periods=1).max()
        drawdown = (self.equity_curve['equity'] - peak) / peak * 100
        axes[1].fill_between(self.equity_curve.index, drawdown, 0, 
                            alpha=0.3, color='red', label='回撤 (%)')
        axes[1].set_title('回撤曲线', fontsize=14, fontweight='bold')
        axes[1].set_ylabel('回撤 (%)', fontsize=12)
        axes[1].set_xlabel('日期', fontsize=12)
        axes[1].legend(loc='lower left')
        axes[1].grid(True, alpha=0.3)
        
        # 格式化日期轴
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def plot_return_distribution(self, figsize=(10, 6)):
        """
        绘制收益分布图
        
        Args:
            figsize: 图表尺寸
        """
        if self.daily_returns.empty:
            print("⚠️  无收益数据可供绘制")
            return
            
        fig, ax = plt.subplots(figsize=figsize)
        
        # 绘制直方图
        ax.hist(self.daily_returns, bins=50, alpha=0.7, color='skyblue', edgecolor='black', linewidth=0.5)
        
        # 添加均值线
        mean_return = self.daily_returns.mean()
        ax.axvline(mean_return, color='red', linestyle='--', linewidth=2, 
                  label=f'平均日收益: {mean_return:.2%}')
        
        # 添加正态分布拟合曲线
        x = np.linspace(self.daily_returns.min(), self.daily_returns.max(), 100)
        std = self.daily_returns.std()
        y = (1/(std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean_return) / std) ** 2)
        y_scaled = y * len(self.daily_returns) * (self.daily_returns.max() - self.daily_returns.min()) / 50
        ax.plot(x, y_scaled, 'r-', linewidth=2, label='正态分布拟合')
        
        ax.set_title('日收益率分布', fontsize=16, fontweight='bold')
        ax.set_xlabel('日收益率', fontsize=12)
        ax.set_ylabel('频次', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_trade_analysis(self, figsize=(12, 10)):
        """
        绘制交易分析图
        
        Args:
            figsize: 图表尺寸
        """
        # 创建子图
        fig = plt.figure(figsize=figsize)
        
        # 1. 月度收益热力图
        ax1 = plt.subplot(2, 2, 1)
        if not self.equity_curve.empty:
            monthly_returns = self.equity_curve['equity'].resample('M').last().pct_change()
            monthly_returns.index = monthly_returns.index.strftime('%Y-%m')
            
            # 转换为年度-月份矩阵
            monthly_df = pd.DataFrame(monthly_returns)
            monthly_df['year'] = pd.to_datetime(monthly_df.index).year
            monthly_df['month'] = pd.to_datetime(monthly_df.index).month
            pivot_table = monthly_df.pivot(index='year', columns='month', values='equity')
            
            # 绘制热力图
            sns.heatmap(pivot_table, annot=True, fmt='.2%', cmap='RdYlGn', center=0,
                       cbar_kws={'label': '月度收益率'}, ax=ax1)
            ax1.set_title('月度收益率热力图', fontsize=14, fontweight='bold')
        
        # 2. 累计收益曲线
        ax2 = plt.subplot(2, 2, 2)
        if not self.equity_curve.empty:
            cumulative_returns = (self.equity_curve['equity'] / self.result.initial_capital) - 1
            ax2.plot(cumulative_returns.index, cumulative_returns, linewidth=2, color='purple')
            ax2.set_title('累计收益率曲线', fontsize=14, fontweight='bold')
            ax2.set_ylabel('累计收益率', fontsize=12)
            ax2.grid(True, alpha=0.3)
        
        # 3. 胜率和盈亏比分析
        ax3 = plt.subplot(2, 2, 3)
        if self.result.total_trades > 0:
            metrics = ['胜率', '盈亏比', '夏普比率']
            values = [self.result.win_rate, 
                     self.result.profit_factor if self.result.profit_factor != float('inf') else 2.0,
                     max(0, self.result.sharpe_ratio)]  # 处理负夏普比率
            
            bars = ax3.bar(metrics, values, color=['green', 'blue', 'orange'])
            ax3.set_title('关键绩效指标', fontsize=14, fontweight='bold')
            ax3.set_ylabel('数值', fontsize=12)
            
            # 在柱状图上添加数值标签
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:.2f}' if value < 10 else f'{value:.1f}',
                        ha='center', va='bottom', fontsize=10)
        
        # 4. 持仓时间分布
        ax4 = plt.subplot(2, 2, 4)
        # 简化的持仓时间分布（使用平均值）
        holding_periods = [self.result.avg_holding_period, self.result.max_holding_period]
        labels = ['平均持仓', '最大持仓']
        ax4.bar(labels, holding_periods, color=['lightcoral', 'lightsalmon'])
        ax4.set_title('持仓时间分析', fontsize=14, fontweight='bold')
        ax4.set_ylabel('天数', fontsize=12)
        
        plt.tight_layout()
        plt.show()
    
    def plot_trades_analysis(self, figsize=(15, 10)):
        """
        绘制交易分析图
        
        Args:
            figsize: 图表尺寸
        """
        if self.trades_details.empty:
            print("无交易记录，无法绘制交易分析图")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # 盈亏分布
        profits = self.trades_details['pnl']
        colors = ['green' if x > 0 else 'red' for x in profits]
        
        axes[0, 0].bar(range(len(profits)), profits, color=colors, alpha=0.7)
        axes[0, 0].axhline(y=0, color='black', linestyle='-', linewidth=1)
        axes[0, 0].set_title('每笔交易盈亏', fontsize=12, fontweight='bold')
        axes[0, 0].set_xlabel('交易序号')
        axes[0, 0].set_ylabel('盈亏 ($)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 累积盈亏
        cumulative_pnl = profits.cumsum()
        axes[0, 1].plot(cumulative_pnl, linewidth=2, color='blue')
        axes[0, 1].fill_between(range(len(cumulative_pnl)), cumulative_pnl, 0, 
                               alpha=0.3, color='blue')
        axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=1)
        axes[0, 1].set_title('累积盈亏曲线', fontsize=12, fontweight='bold')
        axes[0, 1].set_xlabel('交易序号')
        axes[0, 1].set_ylabel('累积盈亏 ($)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 持仓天数分布
        holding_days = self.trades_details['holding_days']
        axes[1, 0].hist(holding_days, bins=20, alpha=0.7, color='orange', edgecolor='black')
        axes[1, 0].axvline(holding_days.mean(), color='red', linestyle='--', 
                          label=f'平均: {holding_days.mean():.1f}天')
        axes[1, 0].set_title('持仓天数分布', fontsize=12, fontweight='bold')
        axes[1, 0].set_xlabel('持仓天数')
        axes[1, 0].set_ylabel('频数')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 收益率分布
        return_pct = self.trades_details['return_pct'] * 100  # 转换为百分比
        axes[1, 1].hist(return_pct, bins=20, alpha=0.7, color='purple', edgecolor='black')
        axes[1, 1].axvline(return_pct.mean(), color='red', linestyle='--', 
                          label=f'平均: {return_pct.mean():.1f}%')
        axes[1, 1].axvline(0, color='black', linestyle='-', linewidth=1)
        axes[1, 1].set_title('单笔交易收益率分布', fontsize=12, fontweight='bold')
        axes[1, 1].set_xlabel('收益率 (%)')
        axes[1, 1].set_ylabel('频数')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_rolling_metrics(self, window=60, figsize=(12, 10)):
        """
        绘制滚动性能指标
        
        Args:
            window: 滚动窗口大小（天）
            figsize: 图表尺寸
        """
        if len(self.daily_returns) < window:
            print(f"数据不足，需要至少{window}天的数据")
            return
        
        fig, axes = plt.subplots(3, 1, figsize=figsize)
        
        # 滚动收益率
        rolling_returns = self.daily_returns.rolling(window=window).mean() * 252  # 年化
        axes[0].plot(rolling_returns.index, rolling_returns, linewidth=2, color='blue')
        axes[0].axhline(y=0, color='red', linestyle='--', alpha=0.7)
        axes[0].set_title(f'{window}日滚动年化收益率', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('年化收益率')
        axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        axes[0].grid(True, alpha=0.3)
        
        # 滚动波动率
        rolling_volatility = self.daily_returns.rolling(window=window).std() * np.sqrt(252)
        axes[1].plot(rolling_volatility.index, rolling_volatility, linewidth=2, color='orange')
        axes[1].set_title(f'{window}日滚动年化波动率', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('年化波动率')
        axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        axes[1].grid(True, alpha=0.3)
        
        # 滚动夏普比率
        rolling_sharpe = rolling_returns / rolling_volatility
        axes[2].plot(rolling_sharpe.index, rolling_sharpe, linewidth=2, color='green')
        axes[2].axhline(y=0, color='red', linestyle='--', alpha=0.7)
        axes[2].axhline(y=1, color='gray', linestyle=':', alpha=0.7, label='1.0')
        axes[2].set_title(f'{window}日滚动夏普比率', fontsize=12, fontweight='bold')
        axes[2].set_ylabel('夏普比率')
        axes[2].set_xlabel('日期')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        # 格式化日期轴
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def compare_with_benchmark(self, benchmark_returns: pd.Series, figsize=(12, 8)):
        """
        与基准对比分析
        
        Args:
            benchmark_returns: 基准收益率序列
            figsize: 图表尺寸
        """
        if len(self.daily_returns) <= 1:
            print("策略数据不足，无法进行基准对比")
            return
        
        # 对齐数据
        common_dates = self.daily_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) < 2:
            print("与基准没有足够的共同交易日")
            return
        
        strategy_aligned = self.daily_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # 计算累积收益
        strategy_cumulative = (1 + strategy_aligned).cumprod() - 1
        benchmark_cumulative = (1 + benchmark_aligned).cumprod() - 1
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # 累积收益对比
        axes[0, 0].plot(strategy_cumulative.index, strategy_cumulative, 
                       linewidth=2, label='策略', color='blue')
        axes[0, 0].plot(benchmark_cumulative.index, benchmark_cumulative, 
                       linewidth=2, label='基准', color='red')
        axes[0, 0].set_title('累积收益对比', fontsize=12, fontweight='bold')
        axes[0, 0].set_ylabel('累积收益率')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        # 超额收益
        excess_returns = strategy_aligned - benchmark_aligned
        excess_cumulative = (1 + excess_returns).cumprod() - 1
        axes[0, 1].plot(excess_cumulative.index, excess_cumulative, 
                       linewidth=2, color='green')
        axes[0, 1].axhline(y=0, color='black', linestyle='--', alpha=0.7)
        axes[0, 1].set_title('超额收益', fontsize=12, fontweight='bold')
        axes[0, 1].set_ylabel('超额收益率')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        # 收益散点图
        axes[1, 0].scatter(benchmark_aligned, strategy_aligned, alpha=0.6)
        
        # 拟合线性回归
        from scipy import stats
        slope, intercept, r_value, p_value, std_err = stats.linregress(benchmark_aligned, strategy_aligned)
        line_x = np.array([benchmark_aligned.min(), benchmark_aligned.max()])
        line_y = slope * line_x + intercept
        axes[1, 0].plot(line_x, line_y, 'r-', alpha=0.8, 
                       label=f'Beta: {slope:.2f}, R²: {r_value**2:.3f}')
        
        axes[1, 0].set_title('收益散点图', fontsize=12, fontweight='bold')
        axes[1, 0].set_xlabel('基准日收益率')
        axes[1, 0].set_ylabel('策略日收益率')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 统计对比
        stats_comparison = pd.DataFrame({
            '策略': [
                strategy_aligned.mean() * 252,  # 年化收益
                strategy_aligned.std() * np.sqrt(252),  # 年化波动率
                (strategy_aligned.mean() / strategy_aligned.std()) * np.sqrt(252),  # 夏普比率
                strategy_cumulative.iloc[-1]  # 总收益
            ],
            '基准': [
                benchmark_aligned.mean() * 252,
                benchmark_aligned.std() * np.sqrt(252),
                (benchmark_aligned.mean() / benchmark_aligned.std()) * np.sqrt(252),
                benchmark_cumulative.iloc[-1]
            ]
        }, index=['年化收益率', '年化波动率', '夏普比率', '总收益率'])
        
        # 绘制对比柱状图
        stats_comparison.plot(kind='bar', ax=axes[1, 1])
        axes[1, 1].set_title('关键指标对比', fontsize=12, fontweight='bold')
        axes[1, 1].tick_params(axis='x', rotation=45)
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        # 打印详细统计
        print("\n" + "="*50)
        print("与基准对比统计")
        print("="*50)
        print(f"Beta: {slope:.3f}")
        print(f"Alpha (年化): {(intercept * 252):.2%}")
        print(f"相关性: {r_value:.3f}")
        print(f"信息比率: {excess_returns.mean() / excess_returns.std() * np.sqrt(252):.3f}")
        print(f"跟踪误差: {excess_returns.std() * np.sqrt(252):.2%}")
    
    def plot_performance_dashboard(self, figsize=(15, 12)):
        """
        绘制综合性能仪表板
        
        Args:
            figsize: 图表尺寸
        """
        fig = plt.figure(figsize=figsize)
        
        # 1. 权益曲线和基准比较
        ax1 = plt.subplot(2, 3, 1)
        if not self.equity_curve.empty:
            # 投资组合权益曲线
            portfolio_cumulative = (self.equity_curve['equity'] / self.result.initial_capital) - 1
            ax1.plot(portfolio_cumulative.index, portfolio_cumulative, 
                    linewidth=2, color='blue', label='策略收益')
            
            # 添加一些关键水平线
            ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax1.axhline(y=self.result.total_return, color='green', linestyle='--', 
                       label=f'总收益: {self.result.total_return:.2%}')
            
            ax1.set_title('策略累计收益', fontsize=14, fontweight='bold')
            ax1.set_ylabel('累计收益率', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # 2. 最大回撤分析
        ax2 = plt.subplot(2, 3, 2)
        if not self.equity_curve.empty:
            peak = self.equity_curve['equity'].expanding(min_periods=1).max()
            drawdown = (self.equity_curve['equity'] - peak) / peak
            running_max_dd = drawdown.expanding(min_periods=1).min()
            
            ax2.plot(drawdown.index, drawdown, linewidth=2, color='red', label='回撤')
            ax2.plot(running_max_dd.index, running_max_dd, linewidth=2, color='darkred', 
                    linestyle='--', label='最大回撤')
            ax2.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red')
            
            ax2.set_title('回撤分析', fontsize=14, fontweight='bold')
            ax2.set_ylabel('回撤比例', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # 3. 收益风险散点图
        ax3 = plt.subplot(2, 3, 3)
        if len(self.daily_returns) > 1:
            annual_return_pct = self.result.annual_return * 100
            annual_volatility = self.daily_returns.std() * np.sqrt(252) * 100
            
            scatter = ax3.scatter(annual_volatility, annual_return_pct, 
                                s=100, c=self.result.sharpe_ratio, cmap='viridis',
                                edgecolors='black', linewidth=1)
            
            ax3.set_xlabel('年化波动率 (%)', fontsize=12)
            ax3.set_ylabel('年化收益率 (%)', fontsize=12)
            ax3.set_title('收益-风险散点图', fontsize=14, fontweight='bold')
            plt.colorbar(scatter, ax=ax3, label='夏普比率')
            
            # 添加数据点标注
            ax3.annotate(f'策略\nSR: {self.result.sharpe_ratio:.2f}', 
                        (annual_volatility, annual_return_pct),
                        xytext=(10, 0), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 4. 交易盈亏分布
        ax4 = plt.subplot(2, 3, 4)
        # 简化的盈亏分布（示例数据）
        if self.result.total_trades > 0:
            profits = [self.result.avg_winning_trade] * self.result.profitable_trades
            losses = [self.result.avg_losing_trade] * self.result.losing_trades
            all_trades = profits + losses
            
            if all_trades:
                ax4.hist(all_trades, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
                ax4.axvline(np.mean(all_trades), color='red', linestyle='--', 
                           label=f'平均收益: ${np.mean(all_trades):.2f}')
                ax4.set_xlabel('每笔交易收益 ($)', fontsize=12)
                ax4.set_ylabel('频次', fontsize=12)
                ax4.set_title('交易收益分布', fontsize=14, fontweight='bold')
                ax4.legend()
                ax4.grid(True, alpha=0.3)
        
        # 5. 关键指标雷达图
        ax5 = plt.subplot(2, 3, 5, projection='polar')
        if self.result.total_trades > 0:
            # 标准化指标（0-1之间）
            metrics = ['年化收益', '夏普比率', '胜率', '盈利因子', '回撤控制']
            values = [
                min(1, max(0, self.result.annual_return / 0.5)),  # 假设50%为高收益
                min(1, max(0, self.result.sharpe_ratio / 3)),     # 假设3为高夏普比率
                self.result.win_rate,
                min(1, max(0, self.result.profit_factor / 5)),    # 假设5为高盈利因子
                1 - min(1, max(0, abs(self.result.max_drawdown) / 0.3))  # 假设30%回撤容忍度
            ]
            
            # 闭合图形
            values += values[:1]
            metrics += metrics[:1]
            
            # 计算角度
            angles = [n / float(len(metrics) - 1) * 2 * np.pi for n in range(len(metrics))]
            
            # 绘制雷达图
            ax5.plot(angles, values, linewidth=2, linestyle='solid', label='策略表现')
            ax5.fill(angles, values, alpha=0.4)
            
            # 添加标签
            ax5.set_xticks(angles[:-1])
            ax5.set_xticklabels(metrics[:-1], fontsize=10)
            ax5.set_title('策略综合表现雷达图', fontsize=14, fontweight='bold', pad=20)
        
        # 6. 滚动夏普比率
        ax6 = plt.subplot(2, 3, 6)
        if len(self.daily_returns) > 30:
            rolling_sharpe = self.daily_returns.rolling(window=30).apply(
                lambda x: (x.mean() / x.std()) * np.sqrt(252) if x.std() > 0 else 0
            )
            
            ax6.plot(rolling_sharpe.index, rolling_sharpe, linewidth=2, color='purple')
            ax6.axhline(y=self.result.sharpe_ratio, color='red', linestyle='--', 
                       label=f'整体夏普比率: {self.result.sharpe_ratio:.2f}')
            
            ax6.set_title('滚动夏普比率 (30天)', fontsize=14, fontweight='bold')
            ax6.set_ylabel('夏普比率', fontsize=12)
            ax6.legend()
            ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

    def generate_full_report(self, save_plots=True, plots_dir='plots'):
        """
        生成完整的分析报告
        
        Args:
            save_plots: 是否保存图表
            plots_dir: 图表保存目录
        """
        import os
        
        if save_plots:
            os.makedirs(plots_dir, exist_ok=True)
            plt.ioff()  # 关闭交互模式
        
        # 打印性能摘要
        self.print_performance_summary()
        
        # 生成所有图表
        print("\n正在生成权益曲线图...")
        self.plot_equity_curve()
        if save_plots:
            plt.savefig(f'{plots_dir}/equity_curve.png', dpi=300, bbox_inches='tight')
        
        print("正在生成收益分布图...")
        self.plot_return_distribution()
        if save_plots:
            plt.savefig(f'{plots_dir}/returns_distribution.png', dpi=300, bbox_inches='tight')
        
        print("正在生成交易分析图...")
        self.plot_trade_analysis()
        if save_plots:
            plt.savefig(f'{plots_dir}/trade_analysis.png', dpi=300, bbox_inches='tight')
        
        print("正在生成综合性能仪表板...")
        self.plot_performance_dashboard()
        if save_plots:
            plt.savefig(f'{plots_dir}/performance_dashboard.png', dpi=300, bbox_inches='tight')
        
        if save_plots:
            plt.ion()  # 重新开启交互模式
            print(f"\n所有图表已保存到 {plots_dir}/ 目录")
        
        print("\n分析报告生成完成！")

# --- main.py ---
"""
黄金合约交易策略主程序
整合所有模块，执行完整的策略回测流程
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入自定义模块

def install_dependencies():
    """
    检查并安装必要的依赖包
    """
    import subprocess
    
    required_packages = {
        'pandas': 'pandas>=1.5.0',
        'numpy': 'numpy>=1.21.0',
        'yfinance': 'yfinance>=0.2.18',
        'matplotlib': 'matplotlib>=3.5.0',
        'seaborn': 'seaborn>=0.11.0',
        'scipy': 'scipy>=1.9.0'
    }
    
    missing_packages = []
    
    # 尝试导入每个包来检查是否已安装
    for package_name, package_spec in required_packages.items():
        try:
            __import__(package_name)
        except ImportError:
            missing_packages.append(package_spec)
    
    if missing_packages:
        print("正在安装缺失的依赖包...")
        for package in missing_packages:
            try:
                print(f"安装 {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"✅ {package} 安装成功")
            except subprocess.CalledProcessError:
                print(f"❌ {package} 安装失败，请手动安装")
                return False
        print("依赖包安装完成！\n")
    else:
        print("所有依赖包已安装 ✅\n")
    
    return True

def print_welcome_message():
    """打印欢迎信息"""
    print("=" * 80)
    print("                        黄金合约交易策略回测系统")
    print("=" * 80)
    print("策略特点:")
    print("• 多技术指标综合信号：移动平均线交叉 + RSI + MACD + 布林带 + 成交量")
    print("• 智能仓位管理：基于信号置信度动态调整仓位大小")
    print("• 完善风控体系：止损止盈 + ATR动态止损")
    print("• 详细性能分析：夏普比率、最大回撤、胜率等多维度评估")
    print("• 可视化报告：权益曲线、收益分布、交易分析等专业图表")
    print("=" * 80)
    print()

def validate_config(config):
    """
    验证配置参数的合理性
    
    Args:
        config: 配置对象
        
    Returns:
        bool: 配置是否有效
    """
    print("正在验证配置参数...")
    
    # 检查日期范围
    try:
        start_date = datetime.strptime(config.START_DATE, '%Y-%m-%d')
        end_date = datetime.strptime(config.END_DATE, '%Y-%m-%d')
        
        if start_date >= end_date:
            print("❌ 错误：开始日期必须早于结束日期")
            return False
        
        if end_date > datetime.now():
            print("⚠️  警告：结束日期晚于当前日期，将使用最新可用数据")
        
        if (end_date - start_date).days < 365:
            print("⚠️  警告：回测周期小于一年，可能影响统计可靠性")
            
    except ValueError:
        print("❌ 错误：日期格式不正确，应为 YYYY-MM-DD")
        return False
    
    # 检查资金参数
    if config.INITIAL_CAPITAL <= 0:
        print("❌ 错误：初始资金必须大于0")
        return False
    
    if config.POSITION_SIZE <= 0 or config.POSITION_SIZE > 1:
        print("❌ 错误：仓位大小应在 (0, 1] 范围内")
        return False
    
    # 检查策略参数
    if config.FAST_MA_PERIOD >= config.SLOW_MA_PERIOD:
        print("❌ 错误：快速均线周期应小于慢速均线周期")
        return False
    
    if config.RSI_OVERSOLD >= config.RSI_OVERBOUGHT:
        print("❌ 错误：RSI超卖阈值应小于超买阈值")
        return False
        
    if not (0 <= config.RSI_OVERSOLD <= 100) or not (0 <= config.RSI_OVERBOUGHT <= 100):
        print("❌ 错误：RSI阈值应在 0-100 范围内")
        return False
    
    print("✅ 配置参数验证通过")
    return True

def run_gold_strategy():
    """运行黄金交易策略"""
    print("=" * 50)
    print("           黄金合约交易策略系统")
    print("=" * 50)
    
    # 验证配置
    if not validate_config(Config):
        return False
    
    try:
        # 初始化数据处理器
        data_handler = DataHandler(
            symbol=Config.SYMBOL,
            fallback_symbol=Config.FALLBACK_SYMBOL,
            local_data_path=Config.LOCAL_DATA_PATH,
            use_local_on_fail=Config.USE_LOCAL_ON_FAIL,
            retry_backoff_base=Config.RETRY_BACKOFF_BASE,
            data_provider=Config.DATA_PROVIDER,
            ak_symbol=Config.AK_SYMBOL
        )
        
        # 准备数据
        data = data_handler.prepare_data(
            start_date=Config.START_DATE,
            end_date=Config.END_DATE,
            max_retries=Config.MAX_FETCH_RETRIES
        )
        
        if data.empty:
            print("❌ 错误：获取的数据为空")
            return False
            
        print(f"\n✅ 数据准备完成，共 {len(data)} 条记录")
        
        # 初始化策略和回测引擎
        strategy = GoldTradingStrategy(Config)
        backtest_engine = BacktestEngine(Config)
        
        # 运行回测
        backtest_result = backtest_engine.run_backtest(data, strategy)
        
        # 分析结果
        analyzer = PerformanceAnalyzer(backtest_result)
        analyzer.print_performance_summary()
        
        # 显示可视化图表
        print("\n📊 正在生成可视化报告...")
        try:
            analyzer.plot_performance_dashboard()
            print("✅ 可视化报告生成完成")
        except Exception as e:
            print(f"⚠️  图表生成过程中出现警告: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 策略执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def manual_data_download():
    """手动下载并保存数据"""
    print("🔄 手动数据下载模式")
    
    try:
        # 获取用户输入
        symbol = input(f"请输入标的代码 (默认: {Config.SYMBOL}): ").strip() or Config.SYMBOL
        start_date = input(f"请输入开始日期 (YYYY-MM-DD, 默认: {Config.START_DATE}): ").strip() or Config.START_DATE
        end_date = input(f"请输入结束日期 (YYYY-MM-DD, 默认: {Config.END_DATE}): ").strip() or Config.END_DATE
        
        # 验证日期
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
        
        # 创建数据处理器
        data_handler = DataHandler(
            symbol=symbol,
            fallback_symbol=Config.FALLBACK_SYMBOL,
            local_data_path=Config.LOCAL_DATA_PATH,
            use_local_on_fail=Config.USE_LOCAL_ON_FAIL,
            retry_backoff_base=Config.RETRY_BACKOFF_BASE,
            data_provider=Config.DATA_PROVIDER,
            ak_symbol=Config.AK_SYMBOL
        )
        
        # 获取数据
        data = data_handler.fetch_data(start_date, end_date, Config.MAX_FETCH_RETRIES)
        
        if data.empty:
            print("❌ 获取的数据为空")
            return False
        
        # 保存到本地
        os.makedirs(os.path.dirname(Config.LOCAL_DATA_PATH), exist_ok=True)
        data.to_csv(Config.LOCAL_DATA_PATH)
        print(f"✅ 数据已保存至: {Config.LOCAL_DATA_PATH}")
        print(f"📈 共计 {len(data)} 条记录")
        return True
        
    except Exception as e:
        print(f"❌ 数据下载失败: {str(e)}")
        return False

def view_strategy_parameters():
    """查看策略参数"""
    print("\n⚙️  当前策略参数设置:")
    print("-" * 40)
    
    # 数据源配置
    print("数据源配置:")
    print(f"  数据提供商: {Config.DATA_PROVIDER}")
    print(f"  标的代码: {Config.SYMBOL}")
    print(f"  AkShare代码: {Config.AK_SYMBOL}")
    print(f"  备用代码: {Config.FALLBACK_SYMBOL}")
    print(f"  本地数据路径: {Config.LOCAL_DATA_PATH}")
    print(f"  下载失败时使用本地数据: {'是' if Config.USE_LOCAL_ON_FAIL else '否'}")
    print()
    
    # 时间范围
    print("时间范围:")
    print(f"  开始日期: {Config.START_DATE}")
    print(f"  结束日期: {Config.END_DATE}")
    print()
    
    # 策略参数
    print("策略参数:")
    print(f"  快速均线周期: {Config.FAST_MA_PERIOD}")
    print(f"  慢速均线周期: {Config.SLOW_MA_PERIOD}")
    print(f"  RSI周期: {Config.RSI_PERIOD}")
    print(f"  RSI超卖阈值: {Config.RSI_OVERSOLD}")
    print(f"  RSI超买阈值: {Config.RSI_OVERBOUGHT}")
    print(f"  MACD快线: {Config.MACD_FAST}")
    print(f"  MACD慢线: {Config.MACD_SLOW}")
    print(f"  MACD信号线: {Config.MACD_SIGNAL}")
    print()
    
    # 回测参数
    print("回测参数:")
    print(f"  初始资金: ${Config.INITIAL_CAPITAL:,.2f}")
    print(f"  手续费率: {Config.COMMISSION_RATE:.3f}")
    print(f"  滑点: {Config.SLIPPAGE:.3f}")
    print(f"  仓位大小: {Config.POSITION_SIZE:.2f}")
    print()
    
    # 风控参数
    print("风控参数:")
    print(f"  最大回撤限制: {Config.MAX_DRAWDOWN:.2f}")
    print(f"  止损百分比: {Config.STOP_LOSS_PCT:.2f}")
    print(f"  止盈百分比: {Config.TAKE_PROFIT_PCT:.2f}")
    print()

def main():
    """主函数"""
    print_welcome_message()
    
    # 检查依赖
    if not install_dependencies():
        print("❌ 依赖包安装失败，程序退出")
        return
    
    while True:
        print("\n" + "=" * 50)
        print("           黄金合约交易策略系统")
        print("=" * 50)
        print("请选择要执行的功能:")
        print("1. 📊 运行黄金交易策略回测")
        print("2. 💾 手动下载并保存数据")
        print("3. ⚙️  查看策略参数")
        print("4. 📤 退出程序")
        print("=" * 50)
        
        try:
            choice = input("\n请输入选项编号 (1-4): ").strip()
            
            if choice == '1':
                run_gold_strategy()
            elif choice == '2':
                manual_data_download()
            elif choice == '3':
                view_strategy_parameters()
            elif choice == '4':
                print("👋 感谢使用黄金合约交易策略系统！")
                break
            else:
                print("❌ 无效选项，请重新选择")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序已被用户中断，再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生未预期的错误: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

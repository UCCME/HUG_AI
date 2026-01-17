"""
市场数据加载器
支持加载价格数据、期权链数据、恐慌贪婪指数等
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import requests


class MarketDataLoader:
    """市场数据加载器"""
    
    def __init__(self, config: Dict):
        """
        初始化数据加载器
        
        Args:
            config: 策略配置字典
        """
        self.config = config
        self.price_source = config.get('price_data_source', 'binance')
        self.options_source = config.get('options_data_source', 'deribit')
        
    def load_price_data(self, symbol: str, start_date: str, end_date: str, 
                       interval: str = '1h') -> pd.DataFrame:
        """
        加载价格数据
        
        Args:
            symbol: 交易对（如 'BTCUSDT'）
            start_date: 开始日期
            end_date: 结束日期
            interval: K线间隔
            
        Returns:
            价格数据DataFrame
        """
        if self.price_source == 'binance':
            return self._load_from_binance(symbol, start_date, end_date, interval)
        else:
            raise ValueError(f"不支持的价格数据源: {self.price_source}")
    
    def _load_from_binance(self, symbol: str, start_date: str, 
                          end_date: str, interval: str) -> pd.DataFrame:
        """从Binance加载数据（示例实现）"""
        # 实际应用中需要调用Binance API
        # 这里提供模拟数据结构
        dates = pd.date_range(start=start_date, end=end_date, freq='1H')
        
        # 模拟数据
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.randn(len(dates)).cumsum() + 50000,
            'high': np.random.randn(len(dates)).cumsum() + 50200,
            'low': np.random.randn(len(dates)).cumsum() + 49800,
            'close': np.random.randn(len(dates)).cumsum() + 50000,
            'volume': np.random.rand(len(dates)) * 1000
        })
        
        data.set_index('timestamp', inplace=True)
        return data
    
    def load_options_chain(self, symbol: str, expiry_date: str) -> pd.DataFrame:
        """
        加载期权链数据
        
        Args:
            symbol: 标的资产（如 'BTC'）
            expiry_date: 到期日
            
        Returns:
            期权链DataFrame
        """
        if self.options_source == 'deribit':
            return self._load_options_from_deribit(symbol, expiry_date)
        else:
            raise ValueError(f"不支持的期权数据源: {self.options_source}")
    
    def _load_options_from_deribit(self, symbol: str, expiry_date: str) -> pd.DataFrame:
        """从Deribit加载期权链（示例实现）"""
        # 实际应用中需要调用Deribit API
        # 这里提供模拟数据结构
        strikes = np.arange(45000, 55000, 1000)
        
        options_data = []
        for strike in strikes:
            # Call期权
            options_data.append({
                'strike': strike,
                'type': 'call',
                'expiry': expiry_date,
                'bid': max(0, 50000 - strike) * 0.9,
                'ask': max(0, 50000 - strike) * 1.1,
                'iv': 0.6 + np.random.rand() * 0.2,
                'delta': 0.5,
                'gamma': 0.001,
                'theta': -10,
                'vega': 20
            })
            
            # Put期权
            options_data.append({
                'strike': strike,
                'type': 'put',
                'expiry': expiry_date,
                'bid': max(0, strike - 50000) * 0.9,
                'ask': max(0, strike - 50000) * 1.1,
                'iv': 0.6 + np.random.rand() * 0.2,
                'delta': -0.5,
                'gamma': 0.001,
                'theta': -10,
                'vega': 20
            })
        
        return pd.DataFrame(options_data)
    
    def load_fear_greed_index(self) -> Dict:
        """
        加载恐慌贪婪指数
        
        Returns:
            恐慌贪婪指数数据
        """
        try:
            # 调用 alternative.me API
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'value': int(data['data'][0]['value']),
                    'classification': data['data'][0]['value_classification'],
                    'timestamp': data['data'][0]['timestamp']
                }
        except Exception as e:
            print(f"加载恐慌贪婪指数失败: {str(e)}")
        
        # 返回默认值
        return {'value': 50, 'classification': 'Neutral', 'timestamp': str(int(datetime.now().timestamp()))}
    
    def calculate_realized_volatility(self, price_data: pd.DataFrame, window: int = 30) -> float:
        """
        计算已实现波动率（RV）
        
        Args:
            price_data: 价格数据
            window: 计算窗口
            
        Returns:
            年化已实现波动率
        """
        returns = np.log(price_data['close'] / price_data['close'].shift(1))
        rv = returns.rolling(window=window).std() * np.sqrt(365 * 24)  # 年化
        return rv.iloc[-1]
    
    def get_iv_percentile(self, current_iv: float, iv_history: pd.Series) -> float:
        """
        计算IV分位数
        
        Args:
            current_iv: 当前IV
            iv_history: 历史IV序列
            
        Returns:
            IV分位数（0-100）
        """
        percentile = (iv_history < current_iv).sum() / len(iv_history) * 100
        return percentile
    
    def find_support_resistance(self, price_data: pd.DataFrame, 
                               lookback: int = 60) -> Tuple[float, float]:
        """
        识别支撑位和阻力位
        
        Args:
            price_data: 价格数据
            lookback: 回溯周期
            
        Returns:
            (支撑位, 阻力位)
        """
        recent_data = price_data.iloc[-lookback:]
        
        # 简单实现：使用最近的高低点
        support = recent_data['low'].min()
        resistance = recent_data['high'].max()
        
        return support, resistance

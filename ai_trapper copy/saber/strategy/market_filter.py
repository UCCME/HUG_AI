"""
市场状态过滤器
判断是否处于"慢牛"行情
"""

import pandas as pd
from typing import Dict, Tuple
from saber.utils.indicators import TechnicalIndicators
from saber.utils.market_data import MarketDataLoader


class MarketFilter:
    """市场状态过滤器"""
    
    def __init__(self, config: Dict):
        """
        初始化过滤器
        
        Args:
            config: 策略配置
        """
        self.config = config
        self.data_loader = MarketDataLoader(config)
    
    def check_slow_bull(self, price_data: pd.DataFrame, 
                       current_iv: float, iv_history: pd.Series) -> Tuple[bool, str]:
        """
        检查是否处于慢牛状态
        
        Args:
            price_data: 价格数据
            current_iv: 当前隐含波动率
            iv_history: 历史IV数据
            
        Returns:
            (是否慢牛, 原因说明)
        """
        # 1. 技术趋势检查
        trend_ok, trend_reason = self._check_trend(price_data)
        if not trend_ok:
            return False, f"趋势不符: {trend_reason}"
        
        # 2. 情绪指标检查
        sentiment_ok, sentiment_reason = self._check_sentiment()
        if not sentiment_ok:
            return False, f"情绪不符: {sentiment_reason}"
        
        # 3. 波动率状态检查
        vol_ok, vol_reason = self._check_volatility(price_data, current_iv, iv_history)
        if not vol_ok:
            return False, f"波动率不符: {vol_reason}"
        
        # 4. 流动性检查
        liquidity_ok, liquidity_reason = self._check_liquidity(price_data)
        if not liquidity_ok:
            return False, f"流动性不符: {liquidity_reason}"
        
        return True, "市场处于慢牛状态"
    
    def _check_trend(self, price_data: pd.DataFrame) -> Tuple[bool, str]:
        """
        检查技术趋势
        
        Returns:
            (是否通过, 原因)
        """
        # 1. 均线多头排列
        ma_periods = self.config['ma_periods']
        is_bullish = TechnicalIndicators.check_ma_bullish_alignment(price_data, ma_periods)
        
        if not is_bullish:
            return False, "均线未呈多头排列"
        
        # 2. 价格在布林带合理区间
        price_data = TechnicalIndicators.calculate_bollinger_bands(
            price_data,
            period=self.config['bollinger_period'],
            std=self.config['bollinger_std']
        )
        
        in_range = TechnicalIndicators.check_price_in_bollinger_range(price_data)
        
        if not in_range:
            return False, "价格不在布林带中轨至上轨区间"
        
        return True, "技术趋势良好"
    
    def _check_sentiment(self) -> Tuple[bool, str]:
        """
        检查市场情绪
        
        Returns:
            (是否通过, 原因)
        """
        fear_greed = self.data_loader.load_fear_greed_index()
        value = fear_greed['value']
        
        min_val = self.config['fear_greed_min']
        max_val = self.config['fear_greed_max']
        
        if value < min_val:
            return False, f"恐慌贪婪指数过低({value} < {min_val})，市场过度恐慌"
        
        if value > max_val:
            return False, f"恐慌贪婪指数过高({value} > {max_val})，市场过度贪婪"
        
        return True, f"情绪适中({value})"
    
    def _check_volatility(self, price_data: pd.DataFrame, 
                         current_iv: float, iv_history: pd.Series) -> Tuple[bool, str]:
        """
        检查波动率状态
        
        Returns:
            (是否通过, 原因)
        """
        # 1. 计算已实现波动率
        rv = self.data_loader.calculate_realized_volatility(
            price_data,
            window=30
        )
        
        # 2. RV与IV收敛检查
        convergence_ratio = abs(rv - current_iv) / current_iv
        
        if convergence_ratio > 0.3:  # 差异超过30%
            return False, f"RV({rv:.2f})与IV({current_iv:.2f})差异过大"
        
        # 3. IV分位数检查（应处于中位数附近）
        iv_percentile = self.data_loader.get_iv_percentile(current_iv, iv_history)
        
        # 慢牛环境下，IV不应处于极端值
        if iv_percentile < 20 or iv_percentile > 80:
            return False, f"IV分位数({iv_percentile:.1f}%)处于极端位置"
        
        return True, f"波动率状态正常(IV分位数: {iv_percentile:.1f}%)"
    
    def _check_liquidity(self, price_data: pd.DataFrame) -> Tuple[bool, str]:
        """
        检查流动性
        
        Returns:
            (是否通过, 原因)
        """
        # 检查是否剧烈放量
        is_surge = TechnicalIndicators.calculate_volume_surge(
            price_data,
            ma_period=self.config['volume_ma_period'],
            threshold=self.config['volume_surge_threshold']
        )
        
        if is_surge:
            return False, "成交量剧烈放量，可能进入快牛或暴跌"
        
        return True, "成交量温和"
    
    def get_iv_regime(self, current_iv: float, iv_history: pd.Series) -> str:
        """
        判断IV状态
        
        Args:
            current_iv: 当前IV
            iv_history: 历史IV
            
        Returns:
            IV状态：'low', 'medium', 'high'
        """
        iv_percentile = self.data_loader.get_iv_percentile(current_iv, iv_history)
        
        if iv_percentile < self.config['iv_low_percentile']:
            return 'low'
        elif iv_percentile > self.config['iv_high_percentile']:
            return 'high'
        else:
            return 'medium'

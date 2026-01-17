"""
买卖信号生成模块
实现松松的交易信号：竞价弱转强、早盘快速板、龙头回封板、止损信号
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from ..utils.indicators import TechnicalIndicators


class SignalGenerator:
    """交易信号生成器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化信号生成器
        
        Args:
            config: 信号配置参数
        """
        self.config = config or self._default_config()
        self.indicators = TechnicalIndicators()
        
    def _default_config(self) -> Dict:
        """默认信号配置"""
        return {
            'limit_up_threshold': 9.9,         # 涨停阈值
            'early_limit_time': '10:00:00',    # 早盘快速板时间界限
            'weak_to_strong_threshold': 0.0,   # 竞价弱转强阈值
            'reseal_min_volume': 1.5,          # 回封板最小量比
            'stop_loss_pct': 0.01,             # 止损比例1%
            'macd_divergence_window': 5         # MACD背离检测窗口
        }
    
    def generate_buy_signal(self, 
                           symbol: str, 
                           current_data: pd.Series,
                           hist_data: pd.DataFrame,
                           market_status: Dict) -> Tuple[bool, str, float]:
        """
        生成买入信号
        
        Args:
            symbol: 股票代码
            current_data: 当前数据
            hist_data: 历史数据
            market_status: 市场状态信息
            
        Returns:
            (是否买入, 买入原因, 建议买入价格)
        """
        # 1. 竞价弱转强信号
        if self._is_weak_to_strong(current_data, market_status):
            return True, "竞价弱转强", current_data.get('open', current_data['close'])
        
        # 2. 早盘快速板信号
        if self._is_early_limit_up(current_data, market_status):
            return True, "早盘快速板", current_data['close']
        
        # 3. 龙头回封板信号
        if self._is_reseal_limit_up(current_data, hist_data, market_status):
            return True, "龙头回封板", current_data['close']
        
        # 4. 半路追涨信号（需要强势确认）
        if self._is_halfway_chase(current_data, hist_data, market_status):
            return True, "半路追涨", current_data['close']
        
        return False, "", 0.0
    
    def generate_sell_signal(self, 
                            symbol: str,
                            entry_price: float,
                            current_data: pd.Series,
                            hist_data: pd.DataFrame,
                            market_status: Dict) -> Tuple[bool, str, float]:
        """
        生成卖出信号
        
        Args:
            symbol: 股票代码
            entry_price: 买入价格
            current_data: 当前数据
            hist_data: 历史数据
            market_status: 市场状态信息
            
        Returns:
            (是否卖出, 卖出原因, 建议卖出价格)
        """
        current_price = current_data['close']
        
        # 1. 止损信号（单笔亏损超过1%）
        loss_pct = (current_price - entry_price) / entry_price
        if loss_pct <= -self.config['stop_loss_pct']:
            return True, "止损", current_price
        
        # 2. 次日竞价不及预期
        if self._is_auction_weak(current_data, market_status):
            return True, "竞价不及预期", market_status.get('auction_price', current_price)
        
        # 3. 炸板次日必须止损
        if self._is_limit_broken_yesterday(hist_data):
            return True, "炸板次日止损", current_price
        
        # 4. 技术指标背离
        if self._detect_top_divergence(hist_data):
            return True, "顶背离", current_price
        
        # 5. 获利目标达成（可选）
        if 'target_profit_pct' in self.config:
            profit_pct = (current_price - entry_price) / entry_price
            if profit_pct >= self.config['target_profit_pct']:
                return True, "获利目标达成", current_price
        
        return False, "", 0.0
    
    def _is_weak_to_strong(self, 
                          current_data: pd.Series,
                          market_status: Dict) -> bool:
        """
        判断竞价弱转强
        "竞价弱转强后直接买入"
        
        竞价阶段低开但随后快速拉升
        """
        if 'auction_change' not in market_status:
            return False
        
        # 竞价阶段从负转正
        auction_change = market_status['auction_change']
        prev_auction_change = market_status.get('prev_auction_change', 0)
        
        return (
            prev_auction_change < self.config['weak_to_strong_threshold'] and
            auction_change >= self.config['weak_to_strong_threshold']
        )
    
    def _is_early_limit_up(self, 
                          current_data: pd.Series,
                          market_status: Dict) -> bool:
        """
        判断早盘快速板（9:30-10:00封死）
        "早盘快速板体现主力做多决心强，次日高开概率大"
        """
        if 'limit_up_time' not in market_status:
            return False
        
        limit_up_time = market_status['limit_up_time']
        
        if pd.isna(limit_up_time):
            return False
        
        # 涨停时间在10:00之前
        time = pd.to_datetime(limit_up_time).time()
        early_time = pd.to_datetime(self.config['early_limit_time']).time()
        
        # 封死涨停（没有炸板或炸板次数很少）
        is_sealed = market_status.get('is_sealed', False)
        open_count = market_status.get('open_count', 0)
        
        return time <= early_time and (is_sealed or open_count <= 1)
    
    def _is_reseal_limit_up(self, 
                           current_data: pd.Series,
                           hist_data: pd.DataFrame,
                           market_status: Dict) -> bool:
        """
        判断龙头回封板
        "炸板后二次回封，观察回封时的买单力度"
        """
        if 'open_count' not in market_status or 'is_sealed' not in market_status:
            return False
        
        open_count = market_status['open_count']
        is_sealed = market_status['is_sealed']
        
        # 有过炸板但最终封住
        if open_count > 0 and is_sealed:
            # 检查回封时的量能
            volume_ratio = market_status.get('volume_ratio', 1.0)
            
            # 量能充足（相对于历史平均放大）
            return volume_ratio >= self.config['reseal_min_volume']
        
        return False
    
    def _is_halfway_chase(self, 
                         current_data: pd.Series,
                         hist_data: pd.DataFrame,
                         market_status: Dict) -> bool:
        """
        判断半路追涨机会
        需要满足：强势拉升、量能配合、板块效应
        """
        change_pct = current_data.get('change_pct', 0)
        
        # 涨幅在5%-9%之间
        if not (5.0 <= change_pct < 9.0):
            return False
        
        # OBV指标向上
        if len(hist_data) >= 2:
            obv = self.indicators.calculate_obv(hist_data)
            if obv.iloc[-1] <= obv.iloc[-2]:
                return False
        
        # 板块效应强
        sector_strength = market_status.get('sector_strength', 0)
        if sector_strength < 5.0:  # 板块平均涨幅低于5%
            return False
        
        return True
    
    def _is_auction_weak(self, 
                        current_data: pd.Series,
                        market_status: Dict) -> bool:
        """
        判断次日竞价是否不及预期
        "第二天竞价不及预期就止盈"
        """
        if 'auction_change' not in market_status:
            return False
        
        auction_change = market_status['auction_change']
        
        # 竞价低开超过2%
        return auction_change < -2.0
    
    def _is_limit_broken_yesterday(self, hist_data: pd.DataFrame) -> bool:
        """
        判断昨日是否炸板
        "炸板次日必须止损"
        """
        if len(hist_data) < 2:
            return False
        
        yesterday = hist_data.iloc[-2]
        
        # 判断昨日是否有涨停后炸板
        if 'high' in yesterday and 'close' in yesterday:
            # 最高价接近涨停但收盘未涨停
            prev_close = hist_data.iloc[-3]['close'] if len(hist_data) >= 3 else yesterday['open']
            limit_price = prev_close * 1.1
            
            is_touched_limit = abs(yesterday['high'] - limit_price) / limit_price < 0.01
            is_not_closed_limit = abs(yesterday['close'] - limit_price) / limit_price > 0.01
            
            return is_touched_limit and is_not_closed_limit
        
        return False
    
    def _detect_top_divergence(self, hist_data: pd.DataFrame) -> bool:
        """
        检测顶背离信号
        价格创新高但MACD未创新高
        """
        if len(hist_data) < self.config['macd_divergence_window'] + 26:
            return False
        
        # 计算MACD
        dif, dea, macd = self.indicators.calculate_macd(hist_data)
        
        # 检测背离
        divergence = self.indicators.detect_divergence(
            hist_data['close'],
            dif,
            self.config['macd_divergence_window']
        )
        
        # 最近出现顶背离
        return divergence.iloc[-1] == -1
    
    def calculate_position_score(self, 
                                symbol: str,
                                current_data: pd.Series,
                                hist_data: pd.DataFrame,
                                market_status: Dict) -> float:
        """
        计算持仓评分
        用于动态调整仓位
        
        Returns:
            评分 0-100，分数越高越值得持有
        """
        score = 50.0  # 基础分
        
        # 涨幅加分
        if 'change_pct' in current_data:
            score += current_data['change_pct'] * 2
        
        # 资金流入加分
        if 'money_flow' in current_data and current_data['money_flow'] > 0:
            score += 10
        
        # 板块效应加分
        sector_strength = market_status.get('sector_strength', 0)
        score += sector_strength
        
        # OBV向上加分
        if len(hist_data) >= 2:
            obv = self.indicators.calculate_obv(hist_data)
            if obv.iloc[-1] > obv.iloc[-2]:
                score += 10
        
        # 涨停封死加分
        if market_status.get('is_sealed', False):
            score += 15
        
        return np.clip(score, 0, 100)

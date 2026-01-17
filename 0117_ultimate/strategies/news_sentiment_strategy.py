"""
消息面情绪策略
基于新闻、公告、社交媒体等消息面数据进行交易决策
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .base_strategy import BaseStrategy, SignalType, StrategySignal


class NewsSentimentStrategy(BaseStrategy):
    """
    消息面情绪策略
    
    核心逻辑：
    1. 收集多源消息数据（新闻、公告、社交媒体）
    2. 情绪分析（正面/负面/中性）
    3. 热度分析（提及频率、传播速度）
    4. 生成交易信号
    """
    
    def __init__(self, weight: float = 0.15, enabled: bool = True,
                 sentiment_threshold: float = 0.6,  # 情绪阈值
                 heat_threshold: float = 2.0,  # 热度阈值（相对平均值）
                 lookback_hours: int = 24,  # 回溯时间（小时）
                 **kwargs):
        """
        初始化消息面情绪策略
        
        Args:
            weight: 策略权重
            enabled: 是否启用
            sentiment_threshold: 情绪得分阈值（0-1）
            heat_threshold: 热度倍数阈值
            lookback_hours: 消息回溯时间窗口
        """
        super().__init__(
            name="NewsSentiment_Strategy",
            weight=weight,
            enabled=enabled,
            sentiment_threshold=sentiment_threshold,
            heat_threshold=heat_threshold,
            lookback_hours=lookback_hours,
            **kwargs
        )
    
    def get_required_indicators(self) -> List[str]:
        """获取所需指标"""
        return [
            'close',
            'volume',
            'news_sentiment',  # 新闻情绪得分
            'news_count',  # 新闻数量
            'social_sentiment',  # 社交媒体情绪
            'announcement_type'  # 公告类型
        ]
    
    def calculate_sentiment_score(self, data: pd.DataFrame, index: int) -> Dict:
        """
        计算综合情绪得分
        
        Returns:
            Dict: 包含情绪得分和详细信息
        """
        result = {
            'overall_sentiment': 0.0,
            'news_sentiment': 0.0,
            'social_sentiment': 0.0,
            'heat_score': 0.0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0
        }
        
        # 新闻情绪
        if 'news_sentiment' in data.columns:
            news_sentiment = data.iloc[index].get('news_sentiment', 0.0)
            if not pd.isna(news_sentiment):
                result['news_sentiment'] = news_sentiment
        
        # 社交媒体情绪
        if 'social_sentiment' in data.columns:
            social_sentiment = data.iloc[index].get('social_sentiment', 0.0)
            if not pd.isna(social_sentiment):
                result['social_sentiment'] = social_sentiment
        
        # 综合情绪（加权平均）
        result['overall_sentiment'] = (
            result['news_sentiment'] * 0.6 +  # 新闻权重60%
            result['social_sentiment'] * 0.4  # 社交媒体权重40%
        )
        
        # 热度得分
        if 'news_count' in data.columns:
            lookback = min(index, 20)
            if lookback > 0:
                avg_count = data.iloc[max(0, index-lookback):index]['news_count'].mean()
                current_count = data.iloc[index].get('news_count', 0)
                if avg_count > 0:
                    result['heat_score'] = current_count / avg_count
        
        return result
    
    def analyze_announcement_impact(self, data: pd.DataFrame, index: int) -> Dict:
        """
        分析公告影响
        
        重大公告类型：
        - 业绩预告（正面/负面）
        - 重大合同/订单
        - 股权变动
        - 重组并购
        - 政策利好
        """
        impact = {
            'has_major_announcement': False,
            'announcement_type': None,
            'expected_impact': 0.0  # -1到1
        }
        
        if 'announcement_type' not in data.columns:
            return impact
        
        announcement = data.iloc[index].get('announcement_type', None)
        
        if pd.isna(announcement) or announcement is None:
            return impact
        
        # 重大利好公告
        positive_announcements = [
            '业绩大幅预增', '重大合同', '政策利好',
            '股权激励', '战略合作', '订单获取'
        ]
        
        # 重大利空公告
        negative_announcements = [
            '业绩预亏', '违规处罚', '诉讼仲裁',
            '股东减持', '业绩下滑', '风险提示'
        ]
        
        announcement_str = str(announcement)
        
        for positive in positive_announcements:
            if positive in announcement_str:
                impact['has_major_announcement'] = True
                impact['announcement_type'] = positive
                impact['expected_impact'] = 0.7
                return impact
        
        for negative in negative_announcements:
            if negative in announcement_str:
                impact['has_major_announcement'] = True
                impact['announcement_type'] = negative
                impact['expected_impact'] = -0.7
                return impact
        
        return impact
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """
        计算消息面信号
        
        Args:
            data: 包含消息面数据的DataFrame
            index: 当前索引
            
        Returns:
            StrategySignal: 交易信号
        """
        current_price = data.iloc[index]['close']
        
        # 计算情绪得分
        sentiment = self.calculate_sentiment_score(data, index)
        
        # 分析公告影响
        announcement = self.analyze_announcement_impact(data, index)
        
        # 综合评分
        overall_score = sentiment['overall_sentiment']
        
        # 公告影响加权
        if announcement['has_major_announcement']:
            overall_score = (overall_score * 0.5 + 
                           (announcement['expected_impact'] + 1) / 2 * 0.5)
        
        # 热度加成
        heat_multiplier = min(sentiment['heat_score'] / self.params['heat_threshold'], 1.5)
        
        # 生成信号
        reasons = []
        
        # 强烈正面信号
        if (overall_score > self.params['sentiment_threshold'] and 
            sentiment['heat_score'] > self.params['heat_threshold']):
            
            confidence = min(0.8, overall_score * heat_multiplier)
            
            if sentiment['news_sentiment'] > 0.6:
                reasons.append(f"新闻正面(得分{sentiment['news_sentiment']:.2f})")
            if sentiment['social_sentiment'] > 0.6:
                reasons.append(f"社交媒体正面(得分{sentiment['social_sentiment']:.2f})")
            if sentiment['heat_score'] > self.params['heat_threshold']:
                reasons.append(f"热度高涨({sentiment['heat_score']:.1f}倍)")
            if announcement['has_major_announcement']:
                reasons.append(f"重大利好({announcement['announcement_type']})")
            
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=current_price,
                reason=f"消息面强烈正面({', '.join(reasons)})",
                metadata={
                    'sentiment': sentiment,
                    'announcement': announcement,
                    'overall_score': overall_score
                }
            )
        
        # 强烈负面信号
        elif (overall_score < (1 - self.params['sentiment_threshold']) and
              sentiment['heat_score'] > self.params['heat_threshold']):
            
            confidence = min(0.7, (1 - overall_score) * heat_multiplier)
            
            if sentiment['news_sentiment'] < 0.4:
                reasons.append(f"新闻负面(得分{sentiment['news_sentiment']:.2f})")
            if sentiment['social_sentiment'] < 0.4:
                reasons.append(f"社交媒体负面(得分{sentiment['social_sentiment']:.2f})")
            if announcement['has_major_announcement'] and announcement['expected_impact'] < 0:
                reasons.append(f"重大利空({announcement['announcement_type']})")
            
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=current_price,
                reason=f"消息面强烈负面({', '.join(reasons)})",
                metadata={
                    'sentiment': sentiment,
                    'announcement': announcement,
                    'overall_score': overall_score
                }
            )
        
        # 中性或信号不足
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=current_price,
            reason=f"消息面中性(得分{overall_score:.2f})",
            metadata={
                'sentiment': sentiment,
                'announcement': announcement
            }
        )


class PolicyCatalystStrategy(BaseStrategy):
    """
    政策催化剂策略
    
    专注于政策驱动的投资机会
    """
    
    def __init__(self, weight: float = 0.20, enabled: bool = True,
                 policy_impact_threshold: float = 0.7,
                 **kwargs):
        super().__init__(
            name="PolicyCatalyst_Strategy",
            weight=weight,
            enabled=enabled,
            policy_impact_threshold=policy_impact_threshold,
            **kwargs
        )
    
    def get_required_indicators(self) -> List[str]:
        return ['close', 'policy_type', 'policy_impact_score']
    
    def calculate_signal(self, data: pd.DataFrame, index: int) -> StrategySignal:
        """
        计算政策催化剂信号
        
        重点关注：
        - 国防政策
        - 产业政策
        - 科技政策
        - 区域政策
        """
        current_price = data.iloc[index]['close']
        
        # 检查是否有政策数据
        if 'policy_type' not in data.columns:
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=current_price,
                reason="无政策数据",
                metadata={}
            )
        
        policy_type = data.iloc[index].get('policy_type', None)
        policy_impact = data.iloc[index].get('policy_impact_score', 0.0)
        
        if pd.isna(policy_type) or pd.isna(policy_impact):
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.HOLD,
                confidence=0.0,
                price=current_price,
                reason="无政策催化",
                metadata={}
            )
        
        # 重大政策利好
        if policy_impact > self.params['policy_impact_threshold']:
            confidence = min(0.8, policy_impact)
            
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=current_price,
                reason=f"重大政策利好({policy_type}, 影响度{policy_impact:.2f})",
                metadata={
                    'policy_type': policy_type,
                    'policy_impact': policy_impact
                }
            )
        
        # 政策利空
        elif policy_impact < -self.params['policy_impact_threshold']:
            confidence = min(0.7, abs(policy_impact))
            
            return StrategySignal(
                timestamp=data.index[index],
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=current_price,
                reason=f"政策利空({policy_type}, 影响度{policy_impact:.2f})",
                metadata={
                    'policy_type': policy_type,
                    'policy_impact': policy_impact
                }
            )
        
        return StrategySignal(
            timestamp=data.index[index],
            signal_type=SignalType.HOLD,
            confidence=0.0,
            price=current_price,
            reason="政策影响中性",
            metadata={}
        )

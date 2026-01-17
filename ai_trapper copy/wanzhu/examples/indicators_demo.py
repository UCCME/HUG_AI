"""
技术指标演示
展示如何使用策略中的技术指标
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wanzhu.utils.indicators import TechnicalIndicators
from wanzhu.utils.data_loader import DataLoader


def demo_indicators():
    """演示技术指标的使用"""
    
    print("=" * 60)
    print("松松策略 - 技术指标演示")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n1. 加载示例数据...")
    loader = DataLoader(data_source='local')
    df = loader.load_stock_data(
        symbol='600000',
        start_date='2024-01-01',
        end_date='2024-12-31'
    )
    
    print(f"   数据行数: {len(df)}")
    print(f"   数据列: {', '.join(df.columns)}")
    
    # 2. 计算 OBV 指标
    print("\n2. 计算 OBV（能量潮）指标...")
    indicators = TechnicalIndicators()
    obv = indicators.calculate_obv(df)
    
    print(f"   最新 OBV: {obv.iloc[-1]:,.0f}")
    print(f"   OBV 趋势: {'上升' if obv.iloc[-1] > obv.iloc[-5] else '下降'}")
    
    # 3. 计算均线
    print("\n3. 计算移动平均线...")
    ma5 = indicators.calculate_ma(df['close'], 5)
    ma10 = indicators.calculate_ma(df['close'], 10)
    ma20 = indicators.calculate_ma(df['close'], 20)
    
    current_price = df['close'].iloc[-1]
    print(f"   当前价格: {current_price:.2f}")
    print(f"   MA5: {ma5.iloc[-1]:.2f}")
    print(f"   MA10: {ma10.iloc[-1]:.2f}")
    print(f"   MA20: {ma20.iloc[-1]:.2f}")
    
    # 判断多头排列
    is_bullish = (current_price > ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1])
    print(f"   多头排列: {'是' if is_bullish else '否'}")
    
    # 4. 计算 MACD
    print("\n4. 计算 MACD 指标...")
    dif, dea, macd = indicators.calculate_macd(df)
    
    print(f"   DIF: {dif.iloc[-1]:.4f}")
    print(f"   DEA: {dea.iloc[-1]:.4f}")
    print(f"   MACD: {macd.iloc[-1]:.4f}")
    print(f"   金叉/死叉: {'金叉' if dif.iloc[-1] > dea.iloc[-1] else '死叉'}")
    
    # 5. 检测背离
    print("\n5. 检测 MACD 背离...")
    divergence = indicators.detect_divergence(df['close'], dif, window=5)
    
    recent_divergence = divergence.iloc[-5:]
    if (recent_divergence == -1).any():
        print("   ⚠️  检测到顶背离信号，注意风险")
    elif (recent_divergence == 1).any():
        print("   ✓  检测到底背离信号，可能反转")
    else:
        print("   -  未检测到背离信号")
    
    # 6. 计算资金流向
    print("\n6. 计算资金流向指标...")
    mfi = indicators.calculate_money_flow(df, period=5)
    
    print(f"   资金流向指标(MFI): {mfi.iloc[-1]:.2f}")
    if mfi.iloc[-1] > 80:
        print("   状态: 超买")
    elif mfi.iloc[-1] < 20:
        print("   状态: 超卖")
    else:
        print("   状态: 正常")
    
    # 7. 综合分析
    print("\n7. 综合分析...")
    score = 0
    reasons = []
    
    # OBV 上升
    if obv.iloc[-1] > obv.iloc[-5]:
        score += 20
        reasons.append("OBV上升")
    
    # 多头排列
    if is_bullish:
        score += 20
        reasons.append("多头排列")
    
    # MACD 金叉
    if dif.iloc[-1] > dea.iloc[-1]:
        score += 20
        reasons.append("MACD金叉")
    
    # 资金流入
    if mfi.iloc[-1] > 50:
        score += 20
        reasons.append("资金流入")
    
    # 无顶背离
    if (recent_divergence != -1).all():
        score += 20
        reasons.append("无顶背离")
    
    print(f"   综合评分: {score}/100")
    print(f"   买入理由: {', '.join(reasons) if reasons else '无'}")
    
    if score >= 60:
        print("   ✓  建议: 可以考虑买入")
    elif score >= 40:
        print("   -  建议: 观望")
    else:
        print("   ✗  建议: 不建议买入")
    
    print("\n" + "=" * 60)
    print("指标演示完成")
    print("=" * 60)


if __name__ == '__main__':
    demo_indicators()

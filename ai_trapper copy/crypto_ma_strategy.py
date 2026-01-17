#!/usr/bin/env python3
"""
加密货币日均线+MACD交易策略
基于技术指标的简单趋势跟踪策略
适合资金10万以内的散户投资者
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class CryptoMAStrategy:
    """
    加密货币日均线+MACD交易策略
    
    核心规则：
    1. 买入信号：MACD金叉（最好在0轴上方）
    2. 持仓判断：价格在日均线之上持有，跌破清仓
    3. 仓位管理：价格和成交量都站上均线时全仓
    4. 止盈规则：涨40%卖1/3，涨80%再卖1/3
    5. 止损规则：跌破日均线第二天清仓
    """
    
    def __init__(
        self, 
        ma_period: int = 20,           # 日均线周期（默认20日）
        macd_fast: int = 12,           # MACD快线周期
        macd_slow: int = 26,           # MACD慢线周期
        macd_signal: int = 9,          # MACD信号线周期
        profit_target_1: float = 0.40, # 第一止盈位：40%
        profit_target_2: float = 0.80, # 第二止盈位：80%
        sell_ratio: float = 0.333      # 止盈卖出比例：1/3
    ):
        """
        初始化策略参数
        
        Args:
            ma_period: 日均线周期
            macd_fast: MACD快线周期
            macd_slow: MACD慢线周期
            macd_signal: MACD信号线周期
            profit_target_1: 第一止盈目标（40%）
            profit_target_2: 第二止盈目标（80%）
            sell_ratio: 每次止盈卖出比例（1/3）
        """
        self.ma_period = ma_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.profit_target_1 = profit_target_1
        self.profit_target_2 = profit_target_2
        self.sell_ratio = sell_ratio
        
        # 持仓信息
        self.position = 0.0           # 当前持仓量
        self.entry_price = 0.0        # 买入均价
        self.total_invested = 0.0     # 总投入资金
        self.cash = 0.0               # 当前现金
        self.profit_level = 0         # 止盈等级（0/1/2）
        
        # 交易记录
        self.trades = []
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            df: 包含OHLCV数据的DataFrame，需要有列：
                - close: 收盘价
                - volume: 成交量
                
        Returns:
            添加了指标的DataFrame，包含：
                - MA: 日均线
                - MACD: MACD值
                - MACD_Signal: MACD信号线
                - MACD_Hist: MACD柱状图
                - Volume_MA: 成交量均线
        """
        df = df.copy()
        
        # 计算日均线
        df['MA'] = df['close'].rolling(window=self.ma_period).mean()
        
        # 计算MACD
        exp1 = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=self.macd_signal, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # 计算成交量均线
        df['Volume_MA'] = df['volume'].rolling(window=self.ma_period).mean()
        
        return df
    
    def check_macd_golden_cross(self, df: pd.DataFrame, idx: int) -> bool:
        """
        检查MACD金叉信号
        
        Args:
            df: 数据DataFrame
            idx: 当前索引
            
        Returns:
            True表示出现MACD金叉
        """
        if idx < 1:
            return False
        
        # 当前MACD > 信号线 且 前一天MACD <= 信号线
        current_macd = df.iloc[idx]['MACD']
        current_signal = df.iloc[idx]['MACD_Signal']
        prev_macd = df.iloc[idx-1]['MACD']
        prev_signal = df.iloc[idx-1]['MACD_Signal']
        
        golden_cross = (current_macd > current_signal) and (prev_macd <= prev_signal)
        
        # 判断是否在0轴上方（更佳信号）
        above_zero = current_macd > 0
        
        return golden_cross, above_zero
    
    def check_buy_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        检查买入信号
        
        买入条件：
        1. MACD金叉（最好在0轴上方）
        2. 价格站上日均线
        3. 成交量站上成交量均线
        
        Args:
            df: 数据DataFrame
            idx: 当前索引
            
        Returns:
            (是否买入, 买入原因)
        """
        if idx < self.ma_period:
            return False, ""
        
        row = df.iloc[idx]
        
        # 检查MACD金叉
        golden_cross, above_zero = self.check_macd_golden_cross(df, idx)
        
        if not golden_cross:
            return False, ""
        
        # 检查价格是否站上日均线
        price_above_ma = row['close'] > row['MA']
        
        # 检查成交量是否站上均线
        volume_above_ma = row['volume'] > row['Volume_MA']
        
        # 只有同时满足三个条件才买入
        if golden_cross and price_above_ma and volume_above_ma:
            signal_quality = "强势" if above_zero else "普通"
            reason = f"MACD金叉({signal_quality})，价格和成交量均站上均线"
            return True, reason
        
        return False, ""
    
    def check_sell_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str, float]:
        """
        检查卖出信号
        
        卖出条件：
        1. 止盈：涨40%卖1/3，涨80%再卖1/3
        2. 止损：跌破日均线
        
        Args:
            df: 数据DataFrame
            idx: 当前索引
            
        Returns:
            (是否卖出, 卖出原因, 卖出比例)
        """
        if self.position == 0:
            return False, "", 0.0
        
        row = df.iloc[idx]
        current_price = row['close']
        
        # 计算当前收益率
        profit_rate = (current_price - self.entry_price) / self.entry_price
        
        # 止盈逻辑
        if profit_rate >= self.profit_target_2 and self.profit_level < 2:
            # 涨80%，卖出1/3
            return True, f"止盈80%（收益率：{profit_rate*100:.2f}%）", self.sell_ratio
        elif profit_rate >= self.profit_target_1 and self.profit_level < 1:
            # 涨40%，卖出1/3
            return True, f"止盈40%（收益率：{profit_rate*100:.2f}%）", self.sell_ratio
        
        # 止损逻辑：跌破日均线
        if current_price < row['MA']:
            return True, f"跌破日均线止损（收益率：{profit_rate*100:.2f}%）", 1.0
        
        return False, "", 0.0
    
    def execute_buy(self, price: float, volume: float, date: str, reason: str, capital: float):
        """
        执行买入操作
        
        Args:
            price: 买入价格
            volume: 成交量
            date: 日期
            reason: 买入原因
            capital: 可用资金
        """
        # 全仓买入
        buy_amount = capital / price
        cost = capital
        
        # 更新持仓
        if self.position > 0:
            # 如果已有持仓，计算新的平均成本
            total_amount = self.position + buy_amount
            self.entry_price = (self.position * self.entry_price + cost) / total_amount
            self.position = total_amount
        else:
            # 首次买入
            self.position = buy_amount
            self.entry_price = price
            self.profit_level = 0
        
        self.total_invested += cost
        self.cash -= cost
        
        # 记录交易
        trade = {
            'date': date,
            'type': 'BUY',
            'price': price,
            'amount': buy_amount,
            'value': cost,
            'position': self.position,
            'cash': self.cash,
            'reason': reason
        }
        self.trades.append(trade)
        
        print(f"📈 {date} 买入 | 价格: {price:.2f} | 数量: {buy_amount:.6f} | 总仓位: {self.position:.6f} | {reason}")
    
    def execute_sell(self, price: float, date: str, reason: str, sell_ratio: float):
        """
        执行卖出操作
        
        Args:
            price: 卖出价格
            date: 日期
            reason: 卖出原因
            sell_ratio: 卖出比例（0-1）
        """
        if self.position == 0:
            return
        
        # 计算卖出数量
        sell_amount = self.position * sell_ratio
        sell_value = sell_amount * price
        
        # 更新持仓
        self.position -= sell_amount
        self.cash += sell_value
        
        # 更新止盈等级
        if sell_ratio >= 1.0:
            # 全部卖出，重置
            self.profit_level = 0
            self.entry_price = 0.0
        else:
            # 部分卖出，更新止盈等级
            profit_rate = (price - self.entry_price) / self.entry_price
            if profit_rate >= self.profit_target_2:
                self.profit_level = 2
            elif profit_rate >= self.profit_target_1:
                self.profit_level = 1
        
        # 计算本次收益
        cost_basis = sell_amount * self.entry_price
        profit = sell_value - cost_basis
        profit_rate = profit / cost_basis * 100
        
        # 记录交易
        trade = {
            'date': date,
            'type': 'SELL',
            'price': price,
            'amount': sell_amount,
            'value': sell_value,
            'profit': profit,
            'profit_rate': profit_rate,
            'position': self.position,
            'cash': self.cash,
            'reason': reason
        }
        self.trades.append(trade)
        
        print(f"📉 {date} 卖出 | 价格: {price:.2f} | 数量: {sell_amount:.6f} | 收益: {profit:.2f}({profit_rate:.2f}%) | 剩余: {self.position:.6f} | {reason}")
    
    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """
        回测策略
        
        Args:
            df: 包含OHLCV数据的DataFrame
            initial_capital: 初始资金
            
        Returns:
            回测结果字典
        """
        print("="*80)
        print("🚀 开始策略回测")
        print(f"💰 初始资金: {initial_capital:,.2f}")
        print(f"📊 数据范围: {df.index[0]} 至 {df.index[-1]}")
        print(f"📈 数据条数: {len(df)}")
        print("="*80 + "\n")
        
        # 初始化
        self.cash = initial_capital
        self.position = 0.0
        self.entry_price = 0.0
        self.total_invested = 0.0
        self.profit_level = 0
        self.trades = []
        
        # 计算指标
        df = self.calculate_indicators(df)
        
        # 遍历每一天
        for idx in range(len(df)):
            date = df.index[idx]
            row = df.iloc[idx]
            
            # 检查卖出信号（优先于买入）
            should_sell, sell_reason, sell_ratio = self.check_sell_signal(df, idx)
            if should_sell:
                self.execute_sell(row['close'], str(date), sell_reason, sell_ratio)
            
            # 如果没有持仓，检查买入信号
            if self.position == 0 and self.cash > 0:
                should_buy, buy_reason = self.check_buy_signal(df, idx)
                if should_buy:
                    self.execute_buy(row['close'], row['volume'], str(date), buy_reason, self.cash)
        
        # 计算最终结果
        final_price = df.iloc[-1]['close']
        final_value = self.cash + self.position * final_price
        total_return = final_value - initial_capital
        return_rate = total_return / initial_capital * 100
        
        # 计算最大回撤
        equity_curve = []
        cash = initial_capital
        position = 0
        
        for idx in range(len(df)):
            price = df.iloc[idx]['close']
            # 根据交易记录更新持仓
            for trade in self.trades:
                if trade['date'] == str(df.index[idx]):
                    if trade['type'] == 'BUY':
                        cash -= trade['value']
                        position += trade['amount']
                    else:
                        cash += trade['value']
                        position -= trade['amount']
            
            equity = cash + position * price
            equity_curve.append(equity)
        
        max_drawdown = 0
        peak = equity_curve[0]
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 统计交易次数
        buy_count = len([t for t in self.trades if t['type'] == 'BUY'])
        sell_count = len([t for t in self.trades if t['type'] == 'SELL'])
        win_count = len([t for t in self.trades if t['type'] == 'SELL' and t['profit'] > 0])
        win_rate = win_count / sell_count * 100 if sell_count > 0 else 0
        
        print("\n" + "="*80)
        print("📊 回测结果")
        print("="*80)
        print(f"💰 初始资金: {initial_capital:,.2f}")
        print(f"💵 最终资金: {final_value:,.2f}")
        print(f"📈 总收益: {total_return:,.2f}")
        print(f"📊 收益率: {return_rate:.2f}%")
        print(f"📉 最大回撤: {max_drawdown*100:.2f}%")
        print(f"🔄 交易次数: {len(self.trades)} (买入{buy_count}次，卖出{sell_count}次)")
        print(f"🎯 胜率: {win_rate:.2f}%")
        print(f"💼 剩余持仓: {self.position:.6f} (价值: {self.position * final_price:,.2f})")
        print(f"💵 剩余现金: {self.cash:,.2f}")
        print("="*80)
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'return_rate': return_rate,
            'max_drawdown': max_drawdown,
            'trades': self.trades,
            'trade_count': len(self.trades),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'win_rate': win_rate,
            'equity_curve': equity_curve
        }
    
    def get_current_signal(self, df: pd.DataFrame) -> Dict:
        """
        获取当前最新的交易信号
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            信号字典
        """
        df = self.calculate_indicators(df)
        idx = len(df) - 1
        
        should_buy, buy_reason = self.check_buy_signal(df, idx)
        should_sell, sell_reason, sell_ratio = self.check_sell_signal(df, idx)
        
        row = df.iloc[idx]
        
        return {
            'date': df.index[idx],
            'price': row['close'],
            'ma': row['MA'],
            'macd': row['MACD'],
            'macd_signal': row['MACD_Signal'],
            'should_buy': should_buy,
            'buy_reason': buy_reason,
            'should_sell': should_sell,
            'sell_reason': sell_reason,
            'sell_ratio': sell_ratio,
            'position': self.position,
            'entry_price': self.entry_price
        }


def example_usage():
    """
    示例：如何使用策略
    """
    # 这里需要准备数据，格式示例：
    # df = pd.DataFrame({
    #     'close': [...],    # 收盘价
    #     'volume': [...],   # 成交量
    # }, index=pd.DatetimeIndex([...]))  # 日期索引
    
    print("="*80)
    print("📚 加密货币日均线+MACD交易策略")
    print("="*80)
    print("\n使用示例：\n")
    print("1. 准备数据（需要包含收盘价和成交量）")
    print("2. 创建策略实例")
    print("3. 运行回测")
    print("\n代码示例：")
    print("""
    import pandas as pd
    from crypto_ma_strategy import CryptoMAStrategy
    
    # 加载数据
    df = pd.read_csv('btc_daily.csv', index_col='date', parse_dates=True)
    
    # 创建策略
    strategy = CryptoMAStrategy(
        ma_period=20,           # 20日均线
        profit_target_1=0.40,   # 涨40%第一次止盈
        profit_target_2=0.80    # 涨80%第二次止盈
    )
    
    # 回测
    results = strategy.backtest(df, initial_capital=100000)
    
    # 获取当前信号
    signal = strategy.get_current_signal(df)
    print(f"当前信号: {signal}")
    """)
    print("\n" + "="*80)


if __name__ == "__main__":
    example_usage()

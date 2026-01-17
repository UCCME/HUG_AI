#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
底分型网格交易策略（优化版）
结合技术分析的底分型信号与网格交易的仓位管理

策略核心：
1. 开仓信号：日线底分型确认（近20根K线最低点）
2. 仓位管理：五档网格分批建仓（每次1/5仓位）
3. 止盈规则：单个仓位盈利8%止盈
4. 补仓规则：最新仓位浮亏5%时补仓
5. 风控：动态回撤控制 + ATR波动率过滤

优化内容：
- 修复多档位同时止盈的bug
- 添加ATR波动率过滤
- 优化资金管理
- 改进错误处理
- 添加参数验证
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class BottomFractalGridStrategy(bt.Strategy):
    """底分型网格交易策略（优化版）"""
    
    params = (
        ('initial_position_size', 0.2),   # 首次开仓比例（1/5）
        ('max_positions', 5),              # 最大持仓档位
        ('take_profit_pct', 0.08),         # 止盈比例 8%
        ('add_position_pct', -0.05),       # 补仓触发比例 -5%
        ('lookback_period', 20),           # 底分型判断周期
        ('atr_period', 14),                # ATR计算周期
        ('atr_threshold', 0),              # ATR阈值（0表示不启用）
        ('use_atr_filter', False),         # 是否启用ATR过滤
        ('printlog', True),                # 是否打印日志
    )
    
    def __init__(self):
        """初始化策略"""
        # 参数验证
        self._validate_params()
        
        # 数据引用
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # 计算ATR指标（用于波动率过滤）
        self.atr = bt.indicators.ATR(self.datas[0], period=self.params.atr_period)
        
        # 持仓信息
        self.positions_info = []  # 存储每个档位的买入价格和数量
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 统计信息
        self.trade_count = 0
        self.win_count = 0
        self.total_profit = 0
        self.max_drawdown = 0
        self.peak_value = self.broker.getvalue()
        self.initial_cash = self.broker.getvalue()  # 记录初始资金
    
    def _validate_params(self):
        """验证策略参数"""
        if self.params.initial_position_size <= 0 or self.params.initial_position_size > 1:
            raise ValueError("initial_position_size 必须在 (0, 1] 之间")
        if self.params.max_positions < 1:
            raise ValueError("max_positions 必须 >= 1")
        if self.params.take_profit_pct <= 0:
            raise ValueError("take_profit_pct 必须 > 0")
        if self.params.add_position_pct >= 0:
            raise ValueError("add_position_pct 必须 < 0")
        if self.params.lookback_period < 2:
            raise ValueError("lookback_period 必须 >= 2")
        
    def log(self, txt, dt=None):
        """日志输出"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'[{dt.isoformat()}] {txt}')
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入执行, 价格: {order.executed.price:.2f}, '
                    f'数量: {order.executed.size:.2f}, '
                    f'费用: {order.executed.comm:.2f}, '
                    f'总值: {order.executed.value:.2f}'
                )
                # 记录这个档位的买入信息
                self.positions_info.append({
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'datetime': self.datas[0].datetime.date(0)
                })
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                
            elif order.issell():
                self.log(
                    f'卖出执行, 价格: {order.executed.price:.2f}, '
                    f'数量: {order.executed.size:.2f}, '
                    f'费用: {order.executed.comm:.2f}, '
                    f'总值: {order.executed.value:.2f}'
                )
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')
        
        self.order = None
    
    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return
        
        self.trade_count += 1
        profit_pct = (trade.pnl / trade.value) * 100 if trade.value != 0 else 0
        
        if trade.pnl >= 0:
            self.win_count += 1
        
        self.total_profit += trade.pnl
        
        self.log(
            f'交易盈亏, 毛利: {trade.pnl:.2f}, 净利: {trade.pnlcomm:.2f}, '
            f'收益率: {profit_pct:.2f}%'
        )
    
    def is_bottom_fractal(self):
        """
        判断是否为底分型
        条件：当前K线最低点 < 前一日 且 < 后一日，且为近20根K线最低点
        注意：因为需要后一日确认，所以实际判断的是前一根K线
        """
        if len(self.datas[0]) < self.params.lookback_period + 2:
            return False
        
        # 获取前一根K线作为判断对象（需要后一根确认）
        current_low = self.datalow[-1]
        prev_low = self.datalow[-2]
        next_low = self.datalow[0]
        
        # 底分型条件：前一根K线的最低点 < 它前面的 且 < 它后面的
        is_fractal = (prev_low < current_low) and (prev_low < next_low)
        
        if not is_fractal:
            return False
        
        # 检查是否为近20根K线的最低点
        low_past20 = [self.datalow[i] for i in range(-self.params.lookback_period, 0)]
        is_lowest = prev_low <= min(low_past20)
        
        return is_lowest
    
    def get_position_size(self):
        """计算每次开仓的数量"""
        available_cash = self.broker.getcash()
        current_value = self.broker.getvalue()
        
        # 每次使用总资金的1/5
        target_value = current_value * self.params.initial_position_size
        
        # 考虑可用资金限制
        target_value = min(target_value, available_cash * 0.95)  # 保留5%作为缓冲
        
        # 计算股票数量（向下取整到100的整数倍）
        current_price = self.dataclose[0]
        shares = int(target_value / current_price / 100) * 100
        
        return shares
    
    def check_take_profit(self):
        """
        检查是否有档位达到止盈条件
        :return: 需要平仓的档位索引列表
        """
        if not self.positions_info:
            return []
        
        current_price = self.dataclose[0]
        positions_to_close = []
        
        for i, pos in enumerate(self.positions_info):
            profit_pct = (current_price - pos['price']) / pos['price']
            
            if profit_pct >= self.params.take_profit_pct:
                positions_to_close.append(i)
                self.log(
                    f'档位 {i+1} 达到止盈条件: '
                    f'买入价 {pos["price"]:.2f}, '
                    f'当前价 {current_price:.2f}, '
                    f'盈利 {profit_pct*100:.2f}%'
                )
        
        return positions_to_close
    
    def check_add_position(self):
        """检查是否需要补仓"""
        if not self.positions_info:
            return False
        
        # 已满仓
        if len(self.positions_info) >= self.params.max_positions:
            return False
        
        # 检查最后一个档位的浮亏
        last_position = self.positions_info[-1]
        current_price = self.dataclose[0]
        loss_pct = (current_price - last_position['price']) / last_position['price']
        
        if loss_pct <= self.params.add_position_pct:
            self.log(
                f'最新档位浮亏达到补仓条件: '
                f'买入价 {last_position["price"]:.2f}, '
                f'当前价 {current_price:.2f}, '
                f'浮亏 {loss_pct*100:.2f}%'
            )
            return True
        
        return False
    
    def update_drawdown(self):
        """更新最大回撤"""
        current_value = self.broker.getvalue()
        
        # 更新峰值
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # 计算当前回撤
        if self.peak_value > 0:
            current_drawdown = (self.peak_value - current_value) / self.peak_value
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
    
    def check_atr_filter(self):
        """
        检查ATR波动率过滤条件
        :return: True表示可以开仓，False表示波动率过高暂停开仓
        """
        if not self.params.use_atr_filter or self.params.atr_threshold <= 0:
            return True
        
        current_atr = self.atr[0]
        current_price = self.dataclose[0]
        
        # ATR相对价格的百分比
        atr_pct = (current_atr / current_price) * 100
        
        if atr_pct > self.params.atr_threshold:
            self.log(f'ATR过高 ({atr_pct:.2f}%)，暂停开仓')
            return False
        
        return True
    
    def next(self):
        """策略主逻辑（优化版）"""
        # 如果有未完成的订单，等待
        if self.order:
            return
        
        # 更新回撤
        self.update_drawdown()
        
        # 当前持仓数量
        current_position = self.position.size
        
        # 检查止盈（修复bug：一次性卖出所有达到止盈条件的档位）
        if current_position > 0:
            positions_to_close = self.check_take_profit()
            if positions_to_close:
                # 计算需要卖出的总数量
                total_size_to_sell = sum(self.positions_info[idx]['size'] for idx in positions_to_close)
                
                # 执行卖出
                self.log(f'执行止盈卖出 {len(positions_to_close)} 个档位，总数量: {total_size_to_sell}')
                self.order = self.sell(size=total_size_to_sell)
                
                # 从后往前删除已平仓的档位
                for idx in reversed(sorted(positions_to_close)):
                    self.positions_info.pop(idx)
                
                return
        
        # 检查补仓
        if current_position > 0:
            if self.check_add_position():
                size = self.get_position_size()
                if size > 0:
                    self.log(f'执行补仓，档位 {len(self.positions_info)+1}/{self.params.max_positions}')
                    self.order = self.buy(size=size)
                return
        
        # 检查开仓信号（无持仓时）
        if current_position == 0:
            # ATR波动率过滤
            if not self.check_atr_filter():
                return
            
            if self.is_bottom_fractal():
                size = self.get_position_size()
                if size > 0:
                    self.log(f'检测到底分型信号，开始首次建仓（1/{self.params.max_positions}仓位）')
                    self.order = self.buy(size=size)
    
    def stop(self):
        """策略结束（优化版）"""
        final_value = self.broker.getvalue()
        total_return = (final_value - self.initial_cash) / self.initial_cash * 100
        win_rate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        
        self.log('=' * 70)
        self.log('策略回测结束')
        self.log('=' * 70)
        self.log(f'初始资金: {self.initial_cash:,.2f}')
        self.log(f'最终资金: {final_value:,.2f}')
        self.log(f'总收益率: {total_return:.2f}%')
        self.log(f'总收益: {final_value - self.initial_cash:,.2f}')
        self.log(f'交易次数: {self.trade_count}')
        self.log(f'盈利次数: {self.win_count}')
        self.log(f'胜率: {win_rate:.2f}%')
        self.log(f'最大回撤: {self.max_drawdown*100:.2f}%')
        
        # 显示策略参数
        self.log(f'\n策略参数:')
        self.log(f'  - 首次开仓比例: {self.params.initial_position_size*100:.0f}%')
        self.log(f'  - 最大档位数: {self.params.max_positions}')
        self.log(f'  - 止盈比例: {self.params.take_profit_pct*100:.0f}%')
        self.log(f'  - 补仓触发: {abs(self.params.add_position_pct)*100:.0f}%')
        self.log(f'  - ATR过滤: {"启用" if self.params.use_atr_filter else "未启用"}')
        self.log('=' * 70)


def get_data_from_xtquant(symbol, start_date, end_date):
    """
    从XtQuant获取股票数据（优化版）
    :param symbol: 股票代码（如：'000001.SZ'）
    :param start_date: 开始日期（如：'20230101'）
    :param end_date: 结束日期（如：'20231231'）
    :return: pandas DataFrame
    """
    try:
        from xtquant import xtdata
        
        print(f"尝试从XtQuant获取 {symbol} 的数据...")
        
        # 下载历史数据
        xtdata.download_history_data(
            stock_list=[symbol],
            period='1d',
            start_time=start_date,
            end_time=end_date
        )
        
        # 获取数据
        data = xtdata.get_market_data(
            stock_list=[symbol],
            period='1d',
            start_time=start_date,
            end_time=end_date
        )
        
        if data is None or len(data) == 0:
            print("XtQuant返回空数据")
            return None
        
        # 处理数据格式（XtQuant可能返回字典格式）
        if isinstance(data, dict) and symbol in data:
            stock_data = data[symbol]
            df = pd.DataFrame(stock_data)
        else:
            df = pd.DataFrame(data)
        
        # 标准化列名
        column_mapping = {
            'time': 'datetime',
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        df = df.rename(columns=column_mapping)
        
        # 确保有必要的列
        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            print(f"数据列不完整，实际列: {df.columns.tolist()}")
            return None
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        print(f"成功从XtQuant获取 {len(df)} 条数据")
        return df
        
    except ImportError:
        print("警告：未安装xtquant库")
        return None
    except Exception as e:
        print(f"从XtQuant获取数据失败: {str(e)}")
        return None


def get_data_from_akshare(symbol, start_date, end_date):
    """
    从akshare获取股票数据（备用数据源）
    :param symbol: 股票代码（如：'000001'）
    :param start_date: 开始日期（如：'20230101'）
    :param end_date: 结束日期（如：'20231231'）
    :return: pandas DataFrame
    """
    try:
        import akshare as ak
        
        # 转换日期格式
        start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
        
        # 获取数据
        df = ak.stock_zh_a_hist(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
        
        if df is None or len(df) == 0:
            return None
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'datetime',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
        
        # 设置索引
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        # 只保留需要的列
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        return df
        
    except Exception as e:
        print(f"从akshare获取数据失败: {str(e)}")
        return None


def run_backtest(symbol, start_date, end_date, initial_cash=100000):
    """
    运行回测
    :param symbol: 股票代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param initial_cash: 初始资金
    """
    print("=" * 70)
    print("底分型网格交易策略回测")
    print("=" * 70)
    print(f"股票代码: {symbol}")
    print(f"回测区间: {start_date} ~ {end_date}")
    print(f"初始资金: {initial_cash:,.2f}")
    print("=" * 70)
    
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(BottomFractalGridStrategy)
    
    # 获取数据
    print("\n正在获取数据...")
    
    # 首先尝试从XtQuant获取
    df = get_data_from_xtquant(symbol, start_date, end_date)
    
    # 如果失败，尝试从akshare获取
    if df is None:
        print("尝试从akshare获取数据...")
        # 移除可能的后缀
        clean_symbol = symbol.split('.')[0]
        df = get_data_from_akshare(clean_symbol, start_date, end_date)
    
    if df is None or len(df) == 0:
        print("错误：无法获取数据")
        return
    
    print(f"成功获取 {len(df)} 条数据")
    
    # 将数据添加到Cerebro
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # 设置初始资金
    cerebro.broker.setcash(initial_cash)
    
    # 设置手续费（万分之三）
    cerebro.broker.setcommission(commission=0.0003)
    
    # 设置每笔交易的固定滑点（0.1%）
    cerebro.broker.set_slippage_perc(0.001)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # 运行回测
    print("\n开始回测...\n")
    results = cerebro.run()
    strat = results[0]
    
    # 输出分析结果
    print("\n" + "=" * 70)
    print("详细分析结果")
    print("=" * 70)
    
    # 夏普比率
    sharpe = strat.analyzers.sharpe.get_analysis()
    print(f"夏普比率: {sharpe.get('sharperatio', 0):.2f}")
    
    # 回撤分析
    drawdown = strat.analyzers.drawdown.get_analysis()
    print(f"最大回撤: {drawdown.get('max', {}).get('drawdown', 0):.2f}%")
    print(f"最长回撤期: {drawdown.get('max', {}).get('len', 0)} 天")
    
    # 收益分析
    returns = strat.analyzers.returns.get_analysis()
    print(f"总收益率: {returns.get('rtot', 0)*100:.2f}%")
    print(f"年化收益率: {returns.get('rnorm', 0)*100:.2f}%")
    
    # 交易分析
    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.get('total', {}).get('total', 0)
    won_trades = trades.get('won', {}).get('total', 0)
    lost_trades = trades.get('lost', {}).get('total', 0)
    
    print(f"\n交易统计:")
    print(f"总交易次数: {total_trades}")
    print(f"盈利次数: {won_trades}")
    print(f"亏损次数: {lost_trades}")
    if total_trades > 0:
        print(f"胜率: {won_trades/total_trades*100:.2f}%")
    
    print("=" * 70)
    
    # 绘制结果
    try:
        print("\n生成回测图表...")
        cerebro.plot(style='candlestick', barup='red', bardown='green')
    except Exception as e:
        print(f"绘图失败: {str(e)}")


def main():
    """主函数（优化版示例）"""
    # 回测参数
    symbol = '000001.SZ'  # 平安银行
    start_date = '20230101'
    end_date = '20231231'
    initial_cash = 100000
    
    print("\n" + "="*70)
    print("底分型网格交易策略 - 优化版")
    print("="*70)
    print("\n主要优化:")
    print("1. 修复多档位同时止盈的bug")
    print("2. 添加ATR波动率过滤功能")
    print("3. 优化资金管理和参数验证")
    print("4. 改进数据获取错误处理")
    print("5. 增强日志输出")
    print("="*70 + "\n")
    
    # 运行回测
    run_backtest(symbol, start_date, end_date, initial_cash)


if __name__ == '__main__':
    main()

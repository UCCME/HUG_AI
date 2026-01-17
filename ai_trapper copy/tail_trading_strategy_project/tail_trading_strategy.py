#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
尾盘选股策略实现
策略核心：每天14:30-15:00筛选符合条件的股票，次日开盘卖出

筛选条件：
1. 涨幅控制：2%~5%
2. 流通市值：50亿~200亿元
3. 换手率：4%~10%
4. 量比：>1
5. 量价关系：成交量与价格同步上升
6. 均线排列：MA5 > MA10 > MA20（多头排列）
7. 强于大盘
8. 分时均价线：股价全天在均价线上方（因数据限制可能无法完全实现）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class TailTradingStrategy:
    """尾盘选股策略类"""
    
    def __init__(self, data_source='akshare'):
        """
        初始化策略
        :param data_source: 数据源类型 (默认使用'akshare'，免费易用)
        """
        self.data_source = data_source
        self.selected_stocks = []
        
        try:
            import akshare as ak
            self.ak = ak
        except ImportError:
            print("警告：未安装akshare库，请运行: pip install akshare")
            self.ak = None
        
    def get_stock_data(self, symbol, start_date, end_date):
        """
        获取股票历史数据
        :param symbol: 股票代码（如：'000001'）
        :param start_date: 开始日期（格式：'20231201'）
        :param end_date: 结束日期（格式：'20231231'）
        :return: DataFrame包含OHLCV数据
        """
        if self.ak is None:
            return None
        
        try:
            # 转换日期格式 20231201 -> 2023-12-01
            start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
            
            # 使用akshare获取股票历史数据
            df = self.ak.stock_zh_a_hist(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
            
            if df is None or len(df) == 0:
                return None
            
            # 重命名列以统一格式
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '换手率': 'turnover_rate'
            })
            
            # 计算前收盘价
            df['pre_close'] = df['close'].shift(1)
            
            # 计算涨跌幅
            df = self.calculate_change_pct(df)
            
            # 计算量比
            df = self.calculate_volume_ratio(df)
            
            # 计算移动平均线
            df = self.calculate_ma(df)
            
            # 获取流通市值（需要单独获取）
            try:
                stock_info = self.ak.stock_individual_info_em(symbol=symbol)
                if stock_info is not None and len(stock_info) > 0:
                    # 查找流通市值
                    circ_mv_row = stock_info[stock_info['item'] == '流通市值']
                    if len(circ_mv_row) > 0:
                        circ_mv_str = circ_mv_row['value'].values[0]
                        # 移除单位和逗号，转换为数值
                        circ_mv = float(circ_mv_str.replace('亿', '').replace(',', '').strip()) * 100000000
                        df['float_market_cap'] = circ_mv
                    else:
                        df['float_market_cap'] = 0
            except:
                df['float_market_cap'] = 0
            
            return df
            
        except Exception as e:
            print(f"获取股票 {symbol} 数据失败: {str(e)}")
            return None
    
    def calculate_change_pct(self, df):
        """
        计算涨跌幅
        :param df: 包含收盘价的DataFrame
        :return: 添加了涨跌幅列的DataFrame
        """
        df['change_pct'] = (df['close'] - df['pre_close']) / df['pre_close'] * 100
        return df
    
    def calculate_turnover_rate(self, df, float_shares):
        """
        计算换手率
        :param df: 包含成交量的DataFrame
        :param float_shares: 流通股本（股）
        :return: 添加了换手率列的DataFrame
        """
        df['turnover_rate'] = (df['volume'] / float_shares) * 100
        return df
    
    def calculate_volume_ratio(self, df):
        """
        计算量比
        :param df: 包含成交量的DataFrame
        :return: 添加了量比列的DataFrame
        """
        # 标准量比 = 当日成交量 / 前5日平均成交量
        df['avg_volume_5d'] = df['volume'].rolling(window=5).mean().shift(1)
        df['volume_ratio'] = df['volume'] / df['avg_volume_5d']
        return df
    
    def calculate_ma(self, df, periods=[5, 10, 20]):
        """
        计算移动平均线
        :param df: 包含收盘价的DataFrame
        :param periods: 均线周期列表
        :return: 添加了均线列的DataFrame
        """
        for period in periods:
            df[f'ma_{period}'] = df['close'].rolling(window=period).mean()
        return df
    
    def check_ma_bullish_alignment(self, row):
        """
        检查均线多头排列
        :param row: 包含均线数据的行
        :return: True/False
        """
        return (row['ma_5'] > row['ma_10'] > row['ma_20'])
    
    def check_volume_price_sync(self, df, look_back=5):
        """
        检查量价同步上升
        :param df: 包含价格和成交量的DataFrame
        :param look_back: 回看周期
        :return: True/False
        """
        recent_data = df.tail(look_back)
        
        # 价格趋势
        price_trend = recent_data['close'].is_monotonic_increasing
        
        # 成交量趋势（相对宽松，允许个别波动）
        volume_increasing = recent_data['volume'].diff().mean() > 0
        
        return price_trend and volume_increasing
    
    def filter_by_market_cap(self, market_cap):
        """
        流通市值筛选：50亿~200亿元
        :param market_cap: 流通市值（亿元）
        :return: True/False
        """
        return 50 <= market_cap <= 200
    
    def filter_by_change_pct(self, change_pct):
        """
        涨幅筛选：2%~5%
        :param change_pct: 涨跌幅
        :return: True/False
        """
        return 2 <= change_pct <= 5
    
    def filter_by_turnover_rate(self, turnover_rate):
        """
        换手率筛选：4%~10%
        :param turnover_rate: 换手率
        :return: True/False
        """
        return 4 <= turnover_rate <= 10
    
    def filter_by_volume_ratio(self, volume_ratio):
        """
        量比筛选：>1
        :param volume_ratio: 量比
        :return: True/False
        """
        return volume_ratio > 1
    
    def screen_stocks(self, stock_list, trade_date, index_change_pct=0):
        """
        筛选符合条件的股票
        :param stock_list: 股票列表
        :param trade_date: 交易日期
        :param index_change_pct: 大盘指数涨跌幅
        :return: 符合条件的股票列表
        """
        selected_stocks = []
        
        for stock_code in stock_list:
            try:
                # 获取股票数据（需要至少30个交易日的数据用于计算均线）
                start_date = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=60)).strftime('%Y%m%d')
                df = self.get_stock_data(stock_code, start_date, trade_date)
                
                if df is None or len(df) < 20:
                    continue
                
                # 获取基本信息
                latest_data = df.iloc[-1]
                market_cap = latest_data.get('float_market_cap', 0) / 100000000  # 转换为亿元
                
                # 条件1：涨幅控制 2%~5%
                if not self.filter_by_change_pct(latest_data['change_pct']):
                    continue
                
                # 条件2：流通市值 50亿~200亿
                if not self.filter_by_market_cap(market_cap):
                    continue
                
                # 条件3：换手率 4%~10%
                if not self.filter_by_turnover_rate(latest_data['turnover_rate']):
                    continue
                
                # 条件4：量比 >1
                if not self.filter_by_volume_ratio(latest_data['volume_ratio']):
                    continue
                
                # 条件5：量价同步上升
                if not self.check_volume_price_sync(df):
                    continue
                
                # 条件6：均线多头排列
                if not self.check_ma_bullish_alignment(latest_data):
                    continue
                
                # 条件7：强于大盘（个股涨幅 > 大盘涨幅）
                if latest_data['change_pct'] <= index_change_pct:
                    continue
                
                # 通过所有条件
                selected_stocks.append({
                    'code': stock_code,
                    'name': latest_data.get('name', ''),
                    'change_pct': latest_data['change_pct'],
                    'turnover_rate': latest_data['turnover_rate'],
                    'volume_ratio': latest_data['volume_ratio'],
                    'market_cap': market_cap,
                    'price': latest_data['close']
                })
                
            except Exception as e:
                print(f"处理股票 {stock_code} 时出错: {str(e)}")
                continue
        
        return selected_stocks
    
    def run_strategy(self, trade_date, stock_list=None):
        """
        运行策略
        :param trade_date: 交易日期（格式：'20231218'）
        :param stock_list: 股票列表，如果为None则获取全市场股票
        :return: 筛选结果
        """
        print(f"\n{'='*60}")
        print(f"尾盘选股策略 - {trade_date}")
        print(f"{'='*60}")
        
        # 如果未提供股票列表，获取全市场A股
        if stock_list is None:
            stock_list = self.get_all_stocks()
        
        # 获取大盘指数涨跌幅（以上证指数为例）
        index_data = self.get_index_data('000001.SH', trade_date)
        index_change_pct = index_data['change_pct'] if index_data else 0
        
        print(f"\n大盘涨跌幅: {index_change_pct:.2f}%")
        print(f"开始筛选股票，共 {len(stock_list)} 只...")
        
        # 筛选股票
        self.selected_stocks = self.screen_stocks(stock_list, trade_date, index_change_pct)
        
        # 输出结果
        print(f"\n筛选完成！共找到 {len(self.selected_stocks)} 只符合条件的股票：")
        print(f"\n{'代码':<10} {'名称':<10} {'涨幅%':<8} {'换手率%':<10} {'量比':<8} {'市值(亿)':<10}")
        print(f"{'-'*70}")
        
        for stock in self.selected_stocks:
            print(f"{stock['code']:<10} {stock['name']:<10} "
                  f"{stock['change_pct']:<8.2f} {stock['turnover_rate']:<10.2f} "
                  f"{stock['volume_ratio']:<8.2f} {stock['market_cap']:<10.2f}")
        
        return self.selected_stocks
    
    def get_all_stocks(self):
        """
        获取所有A股股票代码
        :return: 股票代码列表
        """
        if self.ak is None:
            return []
        
        try:
            # 获取沪深A股实时行情数据
            df = self.ak.stock_zh_a_spot_em()
            
            if df is None or len(df) == 0:
                return []
            
            # 过滤掉ST、*ST等特殊股票
            df = df[~df['名称'].str.contains('ST|退', na=False)]
            
            # 提取股票代码
            stock_list = df['代码'].tolist()
            
            return stock_list
            
        except Exception as e:
            print(f"获取股票列表失败: {str(e)}")
            return []
    
    def get_index_data(self, index_code, trade_date):
        """
        获取指数数据
        :param index_code: 指数代码（如：'000001'代表上证指数）
        :param trade_date: 交易日期（格式：'20231218'）
        :return: 指数数据字典
        """
        if self.ak is None:
            return None
        
        try:
            # 转换日期格式
            end_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            start_date_obj = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=5)
            start_date = start_date_obj.strftime('%Y%m%d')
            start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            
            # 获取上证指数历史数据
            df = self.ak.stock_zh_index_daily(symbol="sh000001")
            
            if df is None or len(df) == 0:
                return None
            
            # 筛选指定日期的数据
            df['date'] = pd.to_datetime(df['date'])
            target_date = pd.to_datetime(end_date)
            df_target = df[df['date'] == target_date]
            
            if len(df_target) == 0:
                return None
            
            # 计算涨跌幅
            latest_close = df_target['close'].values[0]
            df_sorted = df.sort_values('date')
            prev_data = df_sorted[df_sorted['date'] < target_date]
            
            if len(prev_data) == 0:
                return None
            
            prev_close = prev_data.iloc[-1]['close']
            change_pct = (latest_close - prev_close) / prev_close * 100
            
            return {
                'close': latest_close,
                'change_pct': change_pct
            }
            
        except Exception as e:
            print(f"获取指数数据失败: {str(e)}")
            return None
    
    def backtest(self, start_date, end_date):
        """
        回测策略
        :param start_date: 回测开始日期
        :param end_date: 回测结束日期
        :return: 回测结果
        """
        print(f"\n{'='*60}")
        print(f"策略回测: {start_date} ~ {end_date}")
        print(f"{'='*60}")
        
        results = []
        trade_dates = self.get_trade_dates(start_date, end_date)
        
        for trade_date in trade_dates:
            # 尾盘选股
            selected = self.run_strategy(trade_date)
            
            if len(selected) > 0:
                # 模拟次日开盘卖出
                next_date = self.get_next_trade_date(trade_date)
                if next_date:
                    for stock in selected:
                        open_price = self.get_next_open_price(stock['code'], next_date)
                        if open_price:
                            profit = (open_price - stock['price']) / stock['price'] * 100
                            results.append({
                                'date': trade_date,
                                'code': stock['code'],
                                'buy_price': stock['price'],
                                'sell_price': open_price,
                                'profit_pct': profit
                            })
        
        # 统计回测结果
        self.analyze_backtest_results(results)
        
        return results
    
    def get_trade_dates(self, start_date, end_date):
        """
        获取交易日列表
        :param start_date: 开始日期（格式：'20230101'）
        :param end_date: 结束日期（格式：'20231231'）
        :return: 交易日列表
        """
        if self.ak is None:
            return []
        
        try:
            # 获取交易日历
            df = self.ak.tool_trade_date_hist_sina()
            
            if df is None or len(df) == 0:
                return []
            
            # 转换日期格式并筛选
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
            df_filtered = df[(df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)]
            
            return df_filtered['trade_date'].tolist()
            
        except Exception as e:
            print(f"获取交易日历失败: {str(e)}")
            # 备用方案：使用pandas生成工作日
            try:
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                dates = pd.bdate_range(start=start, end=end)
                return [d.strftime('%Y%m%d') for d in dates]
            except:
                return []
    
    def get_next_trade_date(self, trade_date):
        """
        获取下一个交易日
        :param trade_date: 当前交易日（格式：'20231218'）
        :return: 下一个交易日（格式：'20231218'）
        """
        if self.ak is None:
            return None
        
        try:
            # 获取交易日历
            df = self.ak.tool_trade_date_hist_sina()
            
            if df is None or len(df) == 0:
                return None
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
            df = df.sort_values('trade_date')
            
            # 查找下一个交易日
            next_dates = df[df['trade_date'] > trade_date]
            
            if len(next_dates) > 0:
                return next_dates.iloc[0]['trade_date']
            
            return None
            
        except Exception as e:
            print(f"获取下一交易日失败: {str(e)}")
            # 备用方案：简单加1天
            try:
                date_obj = datetime.strptime(trade_date, '%Y%m%d')
                next_date = date_obj + timedelta(days=1)
                return next_date.strftime('%Y%m%d')
            except:
                return None
    
    def get_next_open_price(self, stock_code, trade_date):
        """
        获取股票在指定日期的开盘价
        :param stock_code: 股票代码
        :param trade_date: 交易日期（格式：'20231218'）
        :return: 开盘价
        """
        if self.ak is None:
            return None
        
        try:
            # 获取当天和前一天的数据
            start_date_obj = datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=3)
            start_date = start_date_obj.strftime('%Y%m%d')
            
            df = self.get_stock_data(stock_code, start_date, trade_date)
            
            if df is None or len(df) == 0:
                return None
            
            # 筛选指定日期的数据
            df['date'] = pd.to_datetime(df['date'])
            target_date = pd.to_datetime(f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}")
            df_target = df[df['date'] == target_date]
            
            if len(df_target) > 0:
                return df_target.iloc[0]['open']
            
            return None
            
        except Exception as e:
            print(f"获取股票 {stock_code} 开盘价失败: {str(e)}")
            return None
    
    def analyze_backtest_results(self, results):
        """
        分析回测结果
        :param results: 回测结果列表
        """
        if not results:
            print("\n无回测数据")
            return
        
        df = pd.DataFrame(results)
        
        print(f"\n{'='*60}")
        print("回测结果统计")
        print(f"{'='*60}")
        print(f"总交易次数: {len(df)}")
        print(f"平均收益率: {df['profit_pct'].mean():.2f}%")
        print(f"胜率: {(df['profit_pct'] > 0).sum() / len(df) * 100:.2f}%")
        print(f"最大收益: {df['profit_pct'].max():.2f}%")
        print(f"最大亏损: {df['profit_pct'].min():.2f}%")
        print(f"累计收益: {df['profit_pct'].sum():.2f}%")


def main():
    """主函数示例"""
    print("=" * 70)
    print("尾盘选股策略 - 使用前请先安装依赖：pip install akshare pandas")
    print("=" * 70)
    
    # 创建策略实例
    strategy = TailTradingStrategy(data_source='akshare')
    
    # 示例1：运行单日策略（需要指定历史日期，因为实时数据可能不完整）
    print("\n示例1：单日选股")
    trade_date = '20231215'  # 指定一个历史交易日
    print(f"正在分析 {trade_date} 的选股结果...")
    
    # 为了演示，这里只测试少量股票
    test_stocks = ['000001', '600000', '000002', '600036', '000858']
    selected_stocks = strategy.screen_stocks(test_stocks, trade_date, index_change_pct=1.0)
    
    if len(selected_stocks) > 0:
        print(f"\n找到 {len(selected_stocks)} 只符合条件的股票：")
        for stock in selected_stocks:
            print(f"  {stock['code']} {stock['name']}: "
                  f"涨幅{stock['change_pct']:.2f}%, "
                  f"换手率{stock['turnover_rate']:.2f}%, "
                  f"量比{stock['volume_ratio']:.2f}")
    else:
        print("未找到符合条件的股票")
    
    print("\n" + "=" * 70)
    print("说明：")
    print("1. 实际使用时，可以调用 strategy.get_all_stocks() 获取全市场股票")
    print("2. 可以调用 strategy.run_strategy(trade_date) 运行完整策略")
    print("3. 可以调用 strategy.backtest(start_date, end_date) 进行回测")
    print("4. 尾盘选股建议在14:30-15:00之间运行，使用当日数据")
    print("=" * 70)


if __name__ == '__main__':
    main()

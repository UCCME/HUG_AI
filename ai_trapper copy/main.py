#!/usr/bin/env python3
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
from config import Config
from data_handler import DataHandler
from gold_strategy import GoldTradingStrategy
from backtest_engine import BacktestEngine
from performance_analyzer import PerformanceAnalyzer

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
            print("⚠️  警告：回测期间少于1年，结果可能不够稳定")
    
    except ValueError as e:
        print(f"❌ 错误：日期格式不正确 - {e}")
        return False
    
    # 检查技术指标参数
    if config.FAST_MA_PERIOD >= config.SLOW_MA_PERIOD:
        print("❌ 错误：快速移动平均周期必须小于慢速移动平均周期")
        return False
    
    if not (0 < config.RSI_OVERSOLD < config.RSI_OVERBOUGHT < 100):
        print("❌ 错误：RSI参数设置不合理")
        return False
    
    # 检查回测参数
    if config.INITIAL_CAPITAL <= 0:
        print("❌ 错误：初始资金必须大于0")
        return False
    
    if not (0 < config.POSITION_SIZE <= 1):
        print("❌ 错误：仓位比例必须在0和1之间")
        return False
    
    if config.COMMISSION_RATE < 0 or config.SLIPPAGE < 0:
        print("❌ 错误：手续费率和滑点不能为负数")
        return False
    
    print("✅ 配置参数验证通过")
    return True

def run_strategy_backtest():
    """
    执行完整的策略回测流程
    
    Returns:
        BacktestResult: 回测结果
    """
    # 检查依赖
    if not install_dependencies():
        print("依赖包安装失败，程序退出")
        return None
    
    # 打印欢迎信息
    print_welcome_message()
    
    # 初始化配置
    config = Config()
    
    # 验证配置
    if not validate_config(config):
        print("配置验证失败，程序退出")
        return None
    
    try:
        # 1. 数据获取和预处理
        print("🔄 步骤 1/4: 数据获取和预处理")
        print("-" * 50)
        
        # 使用本地CSV文件
        csv_file = 'XAU_15m_data.csv'
        data_handler = DataHandler(config.SYMBOL, csv_file=csv_file)
        
        # 获取原始数据
        raw_data = data_handler.fetch_data(config.START_DATE, config.END_DATE)
        if raw_data.empty:
            print("❌ 无法获取数据，请检查网络连接和股票代码")
            return None
        
        # 验证数据质量
        if not data_handler.validate_data():
            print("❌ 数据质量验证失败")
            return None
        
        # 计算技术指标
        processed_data = data_handler.prepare_data_for_strategy(config)
        if processed_data.empty:
            print("❌ 技术指标计算失败")
            return None
        
        print(f"✅ 数据处理完成，有效数据: {len(processed_data)} 条")
        print(f"数据期间: {processed_data.index[0].strftime('%Y-%m-%d')} 到 {processed_data.index[-1].strftime('%Y-%m-%d')}")
        print()
        
        # 2. 初始化策略
        print("🔄 步骤 2/4: 初始化交易策略")
        print("-" * 50)
        
        strategy = GoldTradingStrategy(config)
        print("✅ 黄金交易策略初始化完成")
        print(f"策略参数: MA({config.FAST_MA_PERIOD},{config.SLOW_MA_PERIOD}), RSI({config.RSI_PERIOD}), MACD({config.MACD_FAST},{config.MACD_SLOW},{config.MACD_SIGNAL})")
        print()
        
        # 3. 执行回测
        print("🔄 步骤 3/4: 执行策略回测")
        print("-" * 50)
        
        backtest_engine = BacktestEngine(config)
        backtest_result = backtest_engine.run_backtest(processed_data, strategy)
        
        if backtest_result is None:
            print("❌ 回测执行失败")
            return None
        
        print("✅ 回测执行完成")
        print()
        
        # 4. 性能分析和报告
        print("🔄 步骤 4/4: 性能分析和报告生成")
        print("-" * 50)
        
        analyzer = PerformanceAnalyzer(backtest_result)
        
        # 生成完整报告
        analyzer.generate_full_report(save_plots=True, plots_dir='backtest_plots')
        
        print("✅ 性能分析完成")
        print()
        
        return backtest_result
        
    except Exception as e:
        print(f"❌ 程序执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_parameter_sensitivity_analysis():
    """
    运行参数敏感性分析
    测试不同参数组合的策略表现
    """
    print("\n🔄 额外分析：参数敏感性测试")
    print("=" * 60)
    
    config = Config()
    
    # 参数组合
    ma_combinations = [(5, 20), (10, 30), (20, 50), (10, 50)]
    rsi_periods = [10, 14, 20]
    
    results = []
    
    try:
        # 获取数据（只需要获取一次）- 使用本地CSV文件
        csv_file = 'XAU_15m_data.csv'
        data_handler = DataHandler(config.SYMBOL, csv_file=csv_file)
        raw_data = data_handler.fetch_data(config.START_DATE, config.END_DATE)
        
        if raw_data.empty:
            print("无法获取数据进行敏感性分析")
            return
        
        print(f"正在测试 {len(ma_combinations) * len(rsi_periods)} 种参数组合...")
        
        for fast_ma, slow_ma in ma_combinations:
            for rsi_period in rsi_periods:
                print(f"测试参数: MA({fast_ma},{slow_ma}), RSI({rsi_period})")
                
                # 创建临时配置
                temp_config = Config()
                temp_config.FAST_MA_PERIOD = fast_ma
                temp_config.SLOW_MA_PERIOD = slow_ma
                temp_config.RSI_PERIOD = rsi_period
                
                # 处理数据
                data_handler_temp = DataHandler(config.SYMBOL)
                data_handler_temp.data = raw_data.copy()
                processed_data = data_handler_temp.prepare_data_for_strategy(temp_config)
                
                # 运行回测
                strategy = GoldTradingStrategy(temp_config)
                backtest_engine = BacktestEngine(temp_config)
                result = backtest_engine.run_backtest(processed_data, strategy)
                
                # 记录结果
                results.append({
                    'MA_Fast': fast_ma,
                    'MA_Slow': slow_ma,
                    'RSI_Period': rsi_period,
                    'Total_Return': result.total_return,
                    'Annual_Return': result.annual_return,
                    'Sharpe_Ratio': result.sharpe_ratio,
                    'Max_Drawdown': result.max_drawdown,
                    'Win_Rate': result.win_rate,
                    'Total_Trades': result.total_trades
                })
        
        # 创建结果DataFrame
        results_df = pd.DataFrame(results)
        
        # 排序并显示最佳参数
        results_df_sorted = results_df.sort_values('Sharpe_Ratio', ascending=False)
        
        print("\n📊 参数敏感性分析结果 (按夏普比率排序)")
        print("=" * 120)
        print(results_df_sorted.to_string(index=False, float_format='%.3f'))
        
        # 保存结果
        results_df_sorted.to_csv('parameter_sensitivity_results.csv', index=False)
        print(f"\n✅ 敏感性分析完成，结果已保存到 parameter_sensitivity_results.csv")
        
        # 推荐最佳参数
        best_params = results_df_sorted.iloc[0]
        print(f"\n🎯 推荐参数组合:")
        print(f"   MA周期: ({int(best_params['MA_Fast'])}, {int(best_params['MA_Slow'])})")
        print(f"   RSI周期: {int(best_params['RSI_Period'])}")
        print(f"   预期年化收益: {best_params['Annual_Return']:.2%}")
        print(f"   夏普比率: {best_params['Sharpe_Ratio']:.3f}")
        
    except Exception as e:
        print(f"参数敏感性分析失败: {e}")

def create_custom_strategy_template():
    """
    创建自定义策略模板
    """
    template_content = '''"""
自定义策略模板
基于黄金交易策略框架，您可以修改此模板来实现自己的交易逻辑
"""

from gold_strategy import GoldTradingStrategy, SignalType, TradingSignal
import pandas as pd
import numpy as np

class CustomGoldStrategy(GoldTradingStrategy):
    """
    自定义黄金交易策略
    继承基础策略类，重写信号生成逻辑
    """
    
    def __init__(self, config):
        super().__init__(config)
        # 在这里添加您的自定义参数
        self.custom_param1 = 0.8  # 示例参数
        self.custom_param2 = 1.2  # 示例参数
    
    def generate_composite_signal(self, data: pd.DataFrame, index: int) -> TradingSignal:
        """
        重写信号生成逻辑
        在这里实现您的自定义交易信号逻辑
        
        Args:
            data: 包含技术指标的数据
            index: 当前数据索引
            
        Returns:
            交易信号
        """
        # 示例：您可以在这里实现自己的逻辑
        # 1. 获取当前价格和技术指标
        current_price = data.iloc[index]['Close']
        rsi = data.iloc[index]['RSI']
        macd = data.iloc[index]['MACD']
        
        # 2. 实现您的交易逻辑
        # 这里只是一个简单的示例，您需要根据自己的策略思路来修改
        
        if rsi < 30 and macd > 0:
            # 自定义买入条件
            signal_type = SignalType.BUY
            confidence = 0.7
            reason = "RSI超卖且MACD向上"
        elif rsi > 70 and macd < 0:
            # 自定义卖出条件
            signal_type = SignalType.SELL
            confidence = 0.7
            reason = "RSI超买且MACD向下"
        else:
            signal_type = SignalType.HOLD
            confidence = 0.0
            reason = "无明确信号"
        
        # 3. 创建并返回交易信号
        trading_signal = TradingSignal(
            timestamp=data.index[index],
            signal_type=signal_type,
            price=current_price,
            confidence=confidence,
            indicators={
                'RSI': rsi,
                'MACD': macd,
                'Close': current_price
            },
            reason=reason
        )
        
        return trading_signal

# 使用示例：
# if __name__ == "__main__":
#     from config import Config
#     from data_handler import DataHandler
#     from backtest_engine import BacktestEngine
#     
#     config = Config()
#     
#     # 使用自定义策略
#     custom_strategy = CustomGoldStrategy(config)
#     
#     # 其余回测流程与main.py相同
#     # ...
'''
    
    with open('custom_strategy_template.py', 'w', encoding='utf-8') as f:
        f.write(template_content)
    
    print("✅ 自定义策略模板已创建: custom_strategy_template.py")
    print("您可以修改此模板来实现自己的交易策略逻辑")

def main():
    """
    主函数：提供菜单选项执行不同功能
    """
    while True:
        print("\n" + "=" * 50)
        print("           黄金合约交易策略系统")
        print("=" * 50)
        print("请选择要执行的功能:")
        print("1. 运行完整回测分析")
        print("2. 参数敏感性分析")
        print("3. 创建自定义策略模板")
        print("4. 查看当前配置")
        print("0. 退出程序")
        print("-" * 50)
        
        try:
            choice = input("请输入选项 (0-4): ").strip()
            
            if choice == '1':
                print("\n开始执行完整回测分析...")
                result = run_strategy_backtest()
                if result:
                    input("\n按回车键继续...")
                
            elif choice == '2':
                print("\n开始执行参数敏感性分析...")
                run_parameter_sensitivity_analysis()
                input("\n按回车键继续...")
                
            elif choice == '3':
                create_custom_strategy_template()
                input("\n按回车键继续...")
                
            elif choice == '4':
                config = Config()
                print("\n📋 当前配置参数:")
                print("-" * 30)
                print(f"交易标的: {config.SYMBOL}")
                print(f"回测期间: {config.START_DATE} 到 {config.END_DATE}")
                print(f"初始资金: ${config.INITIAL_CAPITAL:,.2f}")
                print(f"手续费率: {config.COMMISSION_RATE:.3%}")
                print(f"滑点: {config.SLIPPAGE:.3%}")
                print(f"仓位比例: {config.POSITION_SIZE:.1%}")
                print(f"移动平均线: ({config.FAST_MA_PERIOD}, {config.SLOW_MA_PERIOD})")
                print(f"RSI周期: {config.RSI_PERIOD}")
                print(f"MACD参数: ({config.MACD_FAST}, {config.MACD_SLOW}, {config.MACD_SIGNAL})")
                print(f"止损比例: {config.STOP_LOSS_PCT:.1%}")
                print(f"止盈比例: {config.TAKE_PROFIT_PCT:.1%}")
                input("\n按回车键继续...")
                
            elif choice == '0':
                print("\n感谢使用黄金合约交易策略系统！")
                print("祝您交易顺利！🚀")
                break
                
            else:
                print("❌ 无效选项，请重新选择")
                
        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            print("请重新选择")

if __name__ == "__main__":
    main()

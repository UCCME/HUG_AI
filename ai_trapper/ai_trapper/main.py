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

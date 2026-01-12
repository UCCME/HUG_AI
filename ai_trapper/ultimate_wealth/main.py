#!/usr/bin/env python3
"""
黄金合约交易策略主程序，整合模块并提供交互菜单。
"""

import os
import sys
from datetime import datetime
import warnings

from ultimate_wealth.ultimate_modular.config import Config
from ultimate_wealth.ultimate_modular.runner import run_modular_strategy
from ultimate_wealth.ultimate_modular.utils import ensure_repo_on_path

warnings.filterwarnings("ignore")


def install_dependencies():
    """检查并安装必要依赖。"""
    import subprocess

    required_packages = {
        "pandas": "pandas>=1.5.0",
        "numpy": "numpy>=1.21.0",
        "yfinance": "yfinance>=0.2.18",
        "matplotlib": "matplotlib>=3.5.0",
        "seaborn": "seaborn>=0.11.0",
        "scipy": "scipy>=1.9.0",
    }

    missing_packages = []

    for package_name, package_spec in required_packages.items():
        try:
            __import__(package_name)
        except ImportError:
            missing_packages.append(package_spec)

    if not missing_packages:
        print("所有依赖包已安装。\n")
        return True

    print("正在安装缺失的依赖包...")
    for package in missing_packages:
        try:
            print(f"安装 {package}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[OK] {package} 安装成功")
        except subprocess.CalledProcessError:
            print(f"[ERROR] {package} 安装失败，请手动安装")
            return False

    print("依赖包安装完成。\n")
    return True


def print_welcome_message():
    """打印欢迎信息。"""
    print("=" * 80)
    print("                        终极模块化策略回测系统")
    print("=" * 80)
    print("策略特点:")
    print("- 多指标综合信号: MA + RSI + MACD + Bollinger + Volume")
    print("- 智能仓位管理: 根据信号置信度动态调整仓位")
    print("- 风控体系: 止损止盈 + ATR 动态止损")
    print("- 性能分析: 夏普比率、最大回撤、胜率等")
    print("- 可视化报告: 权益曲线、收益分布、交易分析")
    print("=" * 80)
    print()


def validate_config(config):
    """验证配置参数的合理性。"""
    print("正在验证配置参数...")

    try:
        start_date = datetime.strptime(config.START_DATE, "%Y-%m-%d")
        end_date = datetime.strptime(config.END_DATE, "%Y-%m-%d")

        if start_date >= end_date:
            print("[ERROR] 开始日期必须早于结束日期")
            return False

        if end_date > datetime.now():
            print("[WARN] 结束日期晚于当前日期，将使用最新可用数据")

        if (end_date - start_date).days < 365:
            print("[WARN] 回测周期小于一年，统计可能不够稳健")
    except ValueError:
        print("[ERROR] 日期格式不正确，应为 YYYY-MM-DD")
        return False

    if config.INITIAL_CAPITAL <= 0:
        print("[ERROR] 初始资金必须大于 0")
        return False

    if config.POSITION_SIZE <= 0 or config.POSITION_SIZE > 1:
        print("[ERROR] 仓位大小应在 (0, 1] 范围内")
        return False

    if config.FAST_MA_PERIOD >= config.SLOW_MA_PERIOD:
        print("[ERROR] 快速均线周期应小于慢速均线周期")
        return False

    if config.RSI_OVERSOLD >= config.RSI_OVERBOUGHT:
        print("[ERROR] RSI 超卖阈值应小于超买阈值")
        return False

    if not (0 <= config.RSI_OVERSOLD <= 100) or not (0 <= config.RSI_OVERBOUGHT <= 100):
        print("[ERROR] RSI 阈值应在 0-100 范围内")
        return False

    print("[OK] 配置参数验证通过")
    return True


def run_ultimate_strategy():
    """运行终极模块化策略。"""
    print("=" * 50)
    print("           终极模块化策略系统")
    print("=" * 50)

    if not validate_config(Config):
        return False

    try:
        return run_modular_strategy(Config)
    except Exception as exc:
        print(f"\n[ERROR] 策略执行过程中发生错误: {exc}")
        import traceback

        traceback.print_exc()
        return False


def manual_data_download():
    """手动下载并保存数据。"""
    print("手动数据下载模式")

    try:
        ensure_repo_on_path()
        from ai_trapper.data_handler import DataHandler

        symbol = input(f"请输入标的代码(默认: {Config.SYMBOL}): ").strip() or Config.SYMBOL
        start_date = input(
            f"请输入开始日期(YYYY-MM-DD, 默认: {Config.START_DATE}): "
        ).strip() or Config.START_DATE
        end_date = input(
            f"请输入结束日期(YYYY-MM-DD, 默认: {Config.END_DATE}): "
        ).strip() or Config.END_DATE

        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")

        data_handler = DataHandler(
            symbol=symbol,
            fallback_symbol=Config.FALLBACK_SYMBOL,
            local_data_path=str(Config.LOCAL_DATA_PATH),
            use_local_on_fail=Config.USE_LOCAL_ON_FAIL,
            retry_backoff_base=Config.RETRY_BACKOFF_BASE,
            data_provider=Config.DATA_PROVIDER,
            ak_symbol=Config.AK_SYMBOL,
        )

        data = data_handler.fetch_data(start_date, end_date, Config.MAX_FETCH_RETRIES)

        if data.empty:
            print("[ERROR] 获取的数据为空")
            return False

        local_dir = os.path.dirname(str(Config.LOCAL_DATA_PATH))
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        data.to_csv(str(Config.LOCAL_DATA_PATH))
        print(f"[OK] 数据已保存至: {Config.LOCAL_DATA_PATH}")
        print(f"[INFO] 共计 {len(data)} 条记录")
        return True
    except Exception as exc:
        print(f"[ERROR] 数据下载失败: {exc}")
        return False


def view_strategy_parameters():
    """查看策略参数。"""
    print("\n当前策略参数设置:")
    print("-" * 40)

    print("数据源配置:")
    print(f"  数据提供方: {Config.DATA_PROVIDER}")
    print(f"  标的代码: {Config.SYMBOL}")
    print(f"  AkShare 代码: {Config.AK_SYMBOL}")
    print(f"  备用代码: {Config.FALLBACK_SYMBOL}")
    print(f"  本地数据路径: {Config.LOCAL_DATA_PATH}")
    print(f"  失败时使用本地数据: {'是' if Config.USE_LOCAL_ON_FAIL else '否'}")
    print()

    print("时间范围:")
    print(f"  开始日期: {Config.START_DATE}")
    print(f"  结束日期: {Config.END_DATE}")
    print()

    print("策略参数:")
    print(f"  快速均线周期: {Config.FAST_MA_PERIOD}")
    print(f"  慢速均线周期: {Config.SLOW_MA_PERIOD}")
    print(f"  RSI 周期: {Config.RSI_PERIOD}")
    print(f"  RSI 超卖阈值: {Config.RSI_OVERSOLD}")
    print(f"  RSI 超买阈值: {Config.RSI_OVERBOUGHT}")
    print(f"  MACD 快线: {Config.MACD_FAST}")
    print(f"  MACD 慢线: {Config.MACD_SLOW}")
    print(f"  MACD 信号线: {Config.MACD_SIGNAL}")
    print()

    print("回测参数:")
    print(f"  初始资金: ${Config.INITIAL_CAPITAL:,.2f}")
    print(f"  手续费率: {Config.COMMISSION_RATE:.3f}")
    print(f"  滑点: {Config.SLIPPAGE:.3f}")
    print(f"  仓位大小: {Config.POSITION_SIZE:.2f}")
    print()

    print("风控参数:")
    print(f"  最大回撤限制: {Config.MAX_DRAWDOWN:.2f}")
    print(f"  止损百分比: {Config.STOP_LOSS_PCT:.2f}")
    print(f"  止盈百分比: {Config.TAKE_PROFIT_PCT:.2f}")
    print()


def main():
    """主入口。"""
    print_welcome_message()

    if "--no-deps" not in sys.argv:
        if not install_dependencies():
            print("[ERROR] 依赖包安装失败，程序退出")
            return

    while True:
        print("\n" + "=" * 50)
        print("           终极模块化策略系统")
        print("=" * 50)
        print("请选择要执行的功能:")
        print("1. 运行模块化策略回测")
        print("2. 手动下载并保存数据")
        print("3. 查看策略参数")
        print("4. 退出程序")
        print("=" * 50)

        try:
            choice = input("\n请输入选项编号 (1-4): ").strip()

            if choice == "1":
                run_ultimate_strategy()
            elif choice == "2":
                manual_data_download()
            elif choice == "3":
                view_strategy_parameters()
            elif choice == "4":
                print("感谢使用，已退出。")
                break
            else:
                print("[WARN] 无效选项，请重新选择")
        except KeyboardInterrupt:
            print("\n程序已中断，再见！")
            break
        except Exception as exc:
            print(f"\n[ERROR] 发生未预期错误: {exc}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()

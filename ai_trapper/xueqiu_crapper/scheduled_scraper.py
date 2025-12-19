import subprocess
import sys
import time
import datetime
from pathlib import Path

# 导入配置
try:
    from scheduler_config import SchedulerConfig, ScraperConfig
except ImportError:
    # 如果配置文件不存在，使用默认配置
    class SchedulerConfig:
        INTERVAL_MINUTES = 30
        INCREMENTAL = True
        ONCE = False

    class ScraperConfig:
        USER_IDS = [
            1247347556,  # 大道无形我有型 (段永平)
            2347043226,  # 你提到的另一个用户
        ]
        PAGES = 2
        COUNT = 20
        DELAY = 3.0
        FORMAT = "jsonl"
        OUTDIR = "output"
        DOWNLOAD_IMAGES = True


def scrape_with_logging(incremental=False):
    """
    执行数据爬取并记录日志
    """
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 生成日志文件名（包含时间戳）
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"scrape_{timestamp}.log"
    
    print(f"开始执行定时爬取任务: {datetime.datetime.now()}")
    print(f"日志文件: {log_file}")
    
    # 构建命令
    cmd = [
        "python", "scrape_presets.py"
    ]
    
    if incremental or SchedulerConfig.INCREMENTAL:
        cmd.append("--incremental")
    
    try:
        # 执行命令并捕获输出
        print("正在执行数据爬取...")
        with open(log_file, "w", encoding="utf-8") as log_f:
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # 将输出写入日志文件
            log_f.write(result.stdout)
            print(result.stdout)
            
        print(f"定时爬取任务完成: {datetime.datetime.now()}")
        print(f"详细日志请查看: {log_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = f"执行失败:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
        print(error_msg)
        
        # 记录错误日志
        with open(log_file, "w", encoding="utf-8") as log_f:
            log_f.write(error_msg)
            
        return False
    except FileNotFoundError:
        error_msg = "错误：找不到 scrape_presets.py 文件，请确保在正确的目录下运行此脚本"
        print(error_msg)
        
        # 记录错误日志
        with open(log_file, "w", encoding="utf-8") as log_f:
            log_f.write(error_msg)
            
        sys.exit(1)


def run_scheduler(interval_minutes=None, incremental=None):
    """
    运行定时调度器
    :param interval_minutes: 间隔时间（分钟）
    :param incremental: 是否使用增量更新模式
    """
    # 使用配置文件中的设置或传入的参数
    interval = interval_minutes or SchedulerConfig.INTERVAL_MINUTES
    incr_mode = incremental if incremental is not None else SchedulerConfig.INCREMENTAL
    
    print(f"启动定时爬取任务，间隔: {interval} 分钟")
    print(f"增量更新模式: {'是' if incr_mode else '否'}")
    print("按 Ctrl+C 可以停止任务")
    
    while True:
        try:
            # 执行爬取任务
            success = scrape_with_logging(incremental=incr_mode)
            
            if success:
                print(f"爬取成功，等待 {interval} 分钟后进行下一次爬取...")
            else:
                print(f"爬取失败，仍将按计划等待 {interval} 分钟...")
            
            # 等待指定的时间间隔
            time.sleep(interval * 60)
            
        except KeyboardInterrupt:
            print("\n收到停止信号，正在退出...")
            break
        except Exception as e:
            print(f"发生未预期的错误: {e}")
            print(f"将继续执行下一次任务...")
            time.sleep(interval * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="定时爬取雪球数据")
    parser.add_argument(
        "--interval", 
        type=int, 
        default=SchedulerConfig.INTERVAL_MINUTES, 
        help="爬取间隔时间（分钟），默认30分钟"
    )
    parser.add_argument(
        "--once", 
        action="store_true", 
        default=SchedulerConfig.ONCE,
        help="只执行一次，不循环执行"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=SchedulerConfig.INCREMENTAL,
        help="使用增量更新模式，只获取新数据"
    )
    args = parser.parse_args()
    
    if args.once:
        # 只执行一次
        scrape_with_logging(incremental=args.incremental)
    else:
        # 按间隔时间循环执行
        run_scheduler(args.interval, args.incremental)


if __name__ == "__main__":
    main()
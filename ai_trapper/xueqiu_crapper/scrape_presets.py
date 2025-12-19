"""
爬虫配置文件
"""

class ScraperConfig:
    # 雪球大V ID 列表 (精选20个，涵盖价值、量化、宏观、科技)
    USER_IDS = [
        1247347556,  # 大道无形我有型 (段永平)
        8152922548,  # 梁宏 (私募大佬)
        8290096439,  # 唐朝 (财报分析)
        4776750571,  # ETF拯救世界 (指数定投)
        3029406972,  # 银行螺丝钉 (估值数据)
        8866762335,  # 月风_投资笔记 (宏观策略)
        9922501069,  # 进化论一平 (量化+基本面)
        1540320649,  # 但斌 (争议大V，茅台铁粉)
        6146070786,  # 持有封基 (低风险套利)
        1626966144,  # 释老毛 (深度逻辑)
        8226064047,  # 望京博格 (基金数据)
        1843652844,  # 省心省力 (大消费)
        1658392837,  # 疯狂的里海 (成长股)
        8602695282,  # 仓佑加错 (TMT/科技)
        6622605342,  # 即使是微弱的光 (医药/价值)
        4684984024,  # 饭统戴老板 (深度商业故事，适合做文案素材)
        6661853655,  # 闲来一坐s话投资 (长文逻辑)
        1636936458,  # 不明真相的群众 (方三文)
        8270588636,  # 朋克民族 (新能源/特斯拉)
        7650893043   # 股海小宁 (实盘交易/短线情绪)
    ]
    
    # 爬取参数
    PAGES = 2      # 每用户爬取页数
    COUNT = 20     # 每页条数
    DELAY = 3.0    # 请求间隔（秒）
    FORMAT = "jsonl"  # 输出格式
    OUTDIR = "output"  # 输出目录
    DOWNLOAD_IMAGES = True  # 是否下载图片
import subprocess
import sys
from pathlib import Path

# 导入配置
try:
    from scheduler_config import ScraperConfig
except ImportError:
    # 如果配置文件不存在，使用默认配置
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


def scrape_default_users(incremental=False):
    """
    使用预设参数爬取指定用户的数据
    """
    users = ScraperConfig.USER_IDS
    pages = ScraperConfig.PAGES
    count = ScraperConfig.COUNT
    delay = ScraperConfig.DELAY
    fmt = ScraperConfig.FORMAT
    outdir = ScraperConfig.OUTDIR
    download_images = ScraperConfig.DOWNLOAD_IMAGES
    
    print(f"开始批量爬取用户数据...")
    print(f"用户数量: {len(users)}")
    print(f"每用户页数: {pages}")
    print(f"每页条数: {count}")
    print(f"基础延迟: {delay}秒")
    print(f"输出格式: {fmt}")
    print(f"输出目录: {outdir}")
    print(f"下载图片: {'是' if download_images else '否'}")
    print(f"增量更新: {'是' if incremental else '否'}")
    print("=" * 50)
    
    failed_users = []
    
    for i, user_id in enumerate(users, 1):
        print(f"\n[{i}/{len(users)}] 正在处理用户 {user_id}...")
        
        # 构建命令
        cmd = [
            "python", "selenium_scrape.py",
            "--user", str(user_id),
            "--pages", str(pages),
            "--count", str(count),
            "--delay", str(delay),
            "--format", fmt,
            "--outdir", outdir
        ]
        
        if download_images:
            cmd.append("--download-images")
            
        if incremental:
            cmd.append("--incremental")
        
        # 执行命令
        try:
            print(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"用户 {user_id} 数据获取完成")
        except subprocess.CalledProcessError as e:
            print(f"获取用户 {user_id} 的数据时出错:")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            failed_users.append(user_id)
            print(f"继续处理下一个用户...")
        except FileNotFoundError:
            print("错误：找不到 selenium_scrape.py 文件，请确保在正确的目录下运行此脚本")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("所有用户数据获取完成!")
    if failed_users:
        print(f"失败用户: {failed_users}")
    print(f"请查看 {outdir} 目录下的输出文件")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="预设用户数据爬取")
    parser.add_argument("--incremental", action="store_true", help="增量更新模式")
    args = parser.parse_args()
    
    scrape_default_users(incremental=args.incremental)


if __name__ == "__main__":
    main()
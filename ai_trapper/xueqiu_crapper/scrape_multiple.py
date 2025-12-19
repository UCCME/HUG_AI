import argparse
import subprocess
import sys
from pathlib import Path

def scrape_users(users, pages, count, delay, fmt, outdir, download_images, keyword=None):
    """
    批量爬取多个用户的数据
    """
    for user_id in users:
        print(f"\n{'='*50}")
        print(f"开始获取用户 {user_id} 的数据")
        print(f"{'='*50}")
        
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
            
        if keyword:
            cmd.extend(["--keyword", keyword])
        
        # 执行命令
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"获取用户 {user_id} 的数据时出错:")
            print(e.stdout)
            print(e.stderr)
            print(f"继续处理下一个用户...")
        except FileNotFoundError:
            print("错误：找不到 selenium_scrape.py 文件，请确保在正确的目录下运行此脚本")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="批量爬取雪球用户数据")
    parser.add_argument("--users", required=True, nargs="+", help="用户ID列表，用空格分隔")
    parser.add_argument("--pages", type=int, default=5, help="抓取页数")
    parser.add_argument("--count", type=int, default=20, help="每页条数")
    parser.add_argument("--delay", type=float, default=3.0, help="两页之间的基础延时(秒)")
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl", help="输出格式")
    parser.add_argument("--outdir", default="output", help="输出目录")
    parser.add_argument("--keyword", default=None, help="仅保留包含该关键字的帖子")
    parser.add_argument("--download-images", action="store_true", help="是否下载图片")
    args = parser.parse_args()

    scrape_users(
        users=args.users,
        pages=args.pages,
        count=args.count,
        delay=args.delay,
        fmt=args.format,
        outdir=args.outdir,
        download_images=args.download_images,
        keyword=args.keyword
    )

if __name__ == "__main__":
    main()
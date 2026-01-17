#!/usr/bin/env python3
"""
快速批量爬取雪球大V数据
使用scrape.py（需要Cookie）
"""
import subprocess
import sys
import time
from pathlib import Path

# 从配置文件导入用户列表
from scheduler_config import ScraperConfig

def scrape_all_users():
    """批量爬取所有预设用户"""
    users = ScraperConfig.USER_IDS
    pages = ScraperConfig.PAGES
    count = ScraperConfig.COUNT
    delay = ScraperConfig.DELAY
    fmt = ScraperConfig.FORMAT
    outdir = ScraperConfig.OUTDIR
    
    print("=" * 60)
    print("🚀 开始批量爬取雪球大V数据")
    print("=" * 60)
    print(f"用户数量: {len(users)}")
    print(f"每用户页数: {pages}")
    print(f"每页条数: {count}")
    print(f"基础延迟: {delay}秒")
    print(f"输出格式: {fmt}")
    print(f"输出目录: {outdir}")
    print("=" * 60)
    print()
    
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ 错误：未找到.env文件")
        print("请先创建.env文件并配置XUEQIU_COOKIE")
        print()
        print("步骤：")
        print("1. 复制.env.example为.env")
        print("2. 在浏览器登录雪球网站")
        print("3. 复制Cookie到.env文件")
        print()
        return
    
    success_count = 0
    failed_users = []
    
    for i, user_id in enumerate(users, 1):
        print(f"\n[{i}/{len(users)}] 正在爬取用户 {user_id}...")
        
        # 构建命令
        cmd = [
            "python3", "scrape.py",
            "--user", str(user_id),
            "--pages", str(pages),
            "--count", str(count),
            "--delay", str(delay),
            "--format", fmt,
            "--outdir", outdir
        ]
        
        try:
            # 执行命令
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            print(f"✅ 用户 {user_id} 爬取成功")
            success_count += 1
            
            # 打印输出
            if result.stdout:
                print(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 用户 {user_id} 爬取失败")
            failed_users.append(user_id)
            
            # 打印错误信息
            if e.stderr:
                print(f"错误信息: {e.stderr}")
            
        except subprocess.TimeoutExpired:
            print(f"⏱️  用户 {user_id} 爬取超时")
            failed_users.append(user_id)
        
        # 用户间延迟
        if i < len(users):
            print(f"等待 {delay} 秒后继续...")
            time.sleep(delay)
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 爬取完成统计")
    print("=" * 60)
    print(f"总用户数: {len(users)}")
    print(f"成功: {success_count}")
    print(f"失败: {len(failed_users)}")
    
    if failed_users:
        print(f"\n失败的用户ID: {failed_users}")
    
    print(f"\n数据保存在: {outdir}/")
    print("=" * 60)

if __name__ == "__main__":
    try:
        scrape_all_users()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断爬取")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        sys.exit(1)

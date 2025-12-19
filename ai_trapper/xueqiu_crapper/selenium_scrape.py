import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import random
import re
import urllib.parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import requests


def load_cookie() -> str:
    """从.env文件加载Cookie"""
    load_dotenv()
    cookie = os.getenv("XUEQIU_COOKIE")
    if not cookie:
        raise ValueError("请在环境变量或 .env 中设置 XUEQIU_COOKIE")
    return cookie


def setup_driver(cookie_str: str) -> webdriver.Chrome:
    """设置Chrome浏览器驱动"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    # 创建驱动实例
    driver = webdriver.Chrome(options=chrome_options)
    
    # 设置Cookie
    driver.get("https://xueqiu.com/")  # 先访问主页以设置域名
    
    # 解析Cookie字符串并添加到浏览器
    cookies = cookie_str.split("; ")
    for cookie in cookies:
        if "=" in cookie:
            key, value = cookie.split("=", 1)
            driver.add_cookie({
                "name": key,
                "value": value,
                "domain": ".xueqiu.com",
                "path": "/",
            })
    
    return driver


def fetch_page_with_selenium(driver: webdriver.Chrome, user_id: str, page: int, count: int) -> Dict:
    """使用Selenium获取页面数据"""
    url = f"https://xueqiu.com/v4/statuses/user_timeline.json?user_id={user_id}&page={page}&count={count}"
    
    # 访问API URL
    driver.get(url)
    
    # 等待页面加载完成
    time.sleep(random.uniform(2, 5))
    
    # 获取页面内容
    page_content = driver.find_element(By.TAG_NAME, "pre").text
    
    try:
        return json.loads(page_content)
    except json.JSONDecodeError:
        raise ValueError(f"返回内容不是有效的JSON: {page_content[:200]}")


def get_user_info(driver: webdriver.Chrome, user_id: str) -> Dict:
    """获取用户信息"""
    try:
        url = f"https://xueqiu.com/user/show.json?user_id={user_id}"
        driver.get(url)
        time.sleep(random.uniform(1, 2))
        page_content = driver.find_element(By.TAG_NAME, "pre").text
        return json.loads(page_content)
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return {"screen_name": f"user_{user_id}"}


def parse_item(raw: Dict) -> Dict:
    """解析单个项目"""
    # 提取图片URL（如果有）
    pic_urls = []
    if raw.get("pic_sizes"):
        for pic_info in raw.get("pic_sizes", []):
            if isinstance(pic_info, dict) and pic_info.get("url"):
                pic_urls.append(pic_info["url"])
    elif raw.get("pics"):
        for pic_info in raw.get("pics", []):
            if isinstance(pic_info, dict) and pic_info.get("url"):
                pic_urls.append(pic_info["url"])
    elif raw.get("thumbnail_pic"):
        pic_urls.append(raw.get("thumbnail_pic"))
    
    return {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "text": raw.get("text"),
        "created_at": raw.get("created_at"),
        "retweet_count": raw.get("retweet_count"),
        "reply_count": raw.get("reply_count"),
        "like_count": raw.get("like_count"),
        "view_count": raw.get("view_count"),
        "pic_urls": pic_urls if pic_urls else None
    }


def download_images(posts: List[Dict], image_dir: Path):
    """下载所有图片"""
    image_dir.mkdir(parents=True, exist_ok=True)
    
    for post in posts:
        pic_urls = post.get("pic_urls")
        if not pic_urls:
            continue
            
        post_id = post.get("id", "unknown")
        for i, pic_url in enumerate(pic_urls):
            try:
                # 发送HTTP请求下载图片
                response = requests.get(pic_url, timeout=30)
                response.raise_for_status()
                
                # 从URL中提取文件扩展名
                ext = ".jpg"  # 默认扩展名
                match = re.search(r'\.(\w+)(?:\?|$)', pic_url)
                if match:
                    ext = "." + match.group(1)
                    
                # 保存图片
                img_filename = f"{post_id}_{i}{ext}"
                img_path = image_dir / img_filename
                
                with open(img_path, "wb") as f:
                    f.write(response.content)
                
                print(f"已下载图片: {img_filename}")
                
                # 添加延迟以避免过于频繁的请求
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                print(f"下载图片失败 {pic_url}: {e}")


def load_existing_data(file_path: Path) -> List[Dict]:
    """加载已有的数据"""
    if not file_path.exists():
        return []
    
    existing_data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    existing_data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"警告: 在文件 {file_path} 的第 {line_num} 行发现无效JSON，已跳过: {e}")
                    continue
    return existing_data


def save_records_incremental(new_records: List[Dict], out_path: Path, fmt: str):
    """增量保存记录到文件"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 加载已存在的数据
    existing_data = load_existing_data(out_path)
    
    # 创建已存在记录ID的集合
    existing_ids = {record["id"] for record in existing_data if record.get("id")}
    
    # 过滤出新的记录
    new_unique_records = [record for record in new_records if record.get("id") and record["id"] not in existing_ids]
    
    if fmt == "jsonl":
        # 追加新模式写入文件，使用美化格式
        with out_path.open("a", encoding="utf-8") as f:
            for r in new_unique_records:
                f.write(json.dumps(r, ensure_ascii=False, indent=2) + "\n")
    elif fmt == "csv":
        import csv

        # 对于CSV格式，我们需要重新写入所有数据（包括旧的和新的）
        all_data = existing_data + new_unique_records
        if all_data:
            with out_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(all_data[0].keys()))
                writer.writeheader()
                writer.writerows(all_data)
    else:
        raise ValueError(f"不支持的格式: {fmt}")
    
    print(f"新增 {len(new_unique_records)} 条记录")


def save_records(new_records: List[Dict], out_path: Path, fmt: str):
    """保存记录到文件（覆盖模式）"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jsonl":
        with out_path.open("w", encoding="utf-8") as f:
            for r in new_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    elif fmt == "csv":
        import csv

        if not new_records:
            return
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(new_records[0].keys()))
            writer.writeheader()
            writer.writerows(new_records)
    else:
        raise ValueError(f"不支持的格式: {fmt}")


def crawl_user(
    user_id: str,
    pages: int = 5,
    count: int = 20,
    delay: float = 3.0,
    fmt: str = "jsonl",
    outdir: str = "output",
    keyword: Optional[str] = None,
    download_images_flag: bool = False,
    incremental: bool = False,
):
    """爬取用户数据"""
    cookie = load_cookie()
    driver = setup_driver(cookie)
    
    try:
        # 获取用户信息
        user_info = get_user_info(driver, user_id)
        screen_name = user_info.get("screen_name", f"user_{user_id}")
        # 清理用户名中的非法字符
        safe_screen_name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', screen_name)
        
        all_items: List[Dict] = []
        for page in range(1, pages + 1):
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    print(f"正在获取第 {page} 页数据...")
                    data = fetch_page_with_selenium(driver, user_id, page, count)
                    break  # 成功获取则跳出重试循环
                except Exception as e:
                    retry_count += 1
                    print(f"第 {page} 页获取失败，第 {retry_count} 次重试: {str(e)}")
                    if retry_count >= max_retries:
                        raise e
                    time.sleep(delay * retry_count * 2)
            
            items = data.get("statuses", [])
            parsed = [parse_item(x) for x in items]
            if keyword:
                parsed = [p for p in parsed if p.get("text") and keyword in p.get("text")]
            all_items.extend(parsed)
            print(f"第 {page} 页: 获取到 {len(items)} 条数据，筛选后保留 {len(parsed)} 条")
            
            # 页面间增加随机延迟
            page_delay = random.uniform(delay, delay * 2)
            print(f"页面间延迟 {page_delay:.1f} 秒...")
            time.sleep(page_delay)

        # 使用包含用户名的文件名
        out_path = Path(outdir) / f"{safe_screen_name}_{user_id}.{fmt}"
        
        # 根据是否增量更新选择保存方式
        if incremental:
            save_records_incremental(all_items, out_path, fmt)
        else:
            save_records(all_items, out_path, fmt)
            
        print(f"保存完成: {out_path} ({len(all_items)} 条)")
        
        # 如果需要下载图片
        if download_images_flag:
            image_dir = Path(outdir) / f"{safe_screen_name}_{user_id}_images"
            print(f"开始下载图片到: {image_dir}")
            download_images(all_items, image_dir)
            print("图片下载完成")
            
    finally:
        driver.quit()


def main():
    parser = argparse.ArgumentParser(description="雪球博主爬取脚本 (Selenium版本)")
    parser.add_argument("--user", required=True, help="雪球用户ID")
    parser.add_argument("--pages", type=int, default=5, help="抓取页数")
    parser.add_argument("--count", type=int, default=20, help="每页条数")
    parser.add_argument("--delay", type=float, default=3.0, help="两页之间的基础延时(秒)")
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl", help="输出格式")
    parser.add_argument("--outdir", default="output", help="输出目录")
    parser.add_argument("--keyword", default=None, help="仅保留包含该关键字的帖子")
    parser.add_argument("--download-images", action="store_true", help="是否下载图片")
    parser.add_argument("--incremental", action="store_true", help="增量更新模式")
    args = parser.parse_args()

    crawl_user(
        user_id=args.user,
        pages=args.pages,
        count=args.count,
        delay=args.delay,
        fmt=args.format,
        outdir=args.outdir,
        keyword=args.keyword,
        download_images_flag=args.download_images,
        incremental=args.incremental,
    )


if __name__ == "__main__":
    main()
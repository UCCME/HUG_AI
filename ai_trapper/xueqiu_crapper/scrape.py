# -*- coding: utf-8 -*-
"""
雪球爬虫脚本
需要配置.env文件中的XUEQIU_COOKIE
"""
import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import random

import requests
from dotenv import load_dotenv

API_URL = "https://xueqiu.com/v4/statuses/user_timeline.json"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
]

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Host": "xueqiu.com",
    "Pragma": "no-cache",
    "Referer": "https://xueqiu.com/",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
}


def load_cookie() -> str:
    """从环境变量加载Cookie"""
    load_dotenv()
    cookie = os.getenv("XUEQIU_COOKIE", "").strip()
    if not cookie:
        raise ValueError("请在.env文件中配置XUEQIU_COOKIE")
    return cookie


def get_random_headers() -> Dict[str, str]:
    """生成随机请求头"""
    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    if "Mac" in headers["User-Agent"]:
        headers["Sec-Ch-Ua-Platform"] = '"macOS"'
    return headers


def fetch_page(user_id: str, page: int, count: int, cookie: str, timeout: int = 30) -> Dict:
    """获取单页数据"""
    params = {
        "user_id": user_id,
        "page": page,
        "count": count,
    }
    
    headers = get_random_headers()
    headers["Cookie"] = cookie
    
    # 随机延迟
    time.sleep(random.uniform(3, 8))
    
    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        
        # 检查WAF拦截
        if "aliyun_waf" in resp.text or "_waf_" in resp.text:
            raise ValueError(f"被WAF拦截，请降低访问频率")
        
        # 检查登录状态
        if "登录" in resp.text and "user" not in resp.text:
            raise ValueError(f"Cookie失效，请重新获取")
        
        return resp.json()
    except requests.RequestException as e:
        raise ValueError(f"网络请求失败: {str(e)}")
    except Exception as e:
        raise ValueError(f"解析失败: {str(e)}")


def parse_item(raw: Dict) -> Dict:
    """解析单条数据"""
    return {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "text": raw.get("text"),
        "created_at": raw.get("created_at"),
        "retweet_count": raw.get("retweet_count"),
        "reply_count": raw.get("reply_count"),
        "like_count": raw.get("like_count"),
        "view_count": raw.get("view_count"),
    }


def save_records(records: List[Dict], out_path: Path, fmt: str):
    """保存数据"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    if fmt == "jsonl":
        with out_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    elif fmt == "csv":
        import csv
        if not records:
            return
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    else:
        raise ValueError(f"不支持的格式: {fmt}")


def crawl_user(
    user_id: str,
    pages: int = 5,
    count: int = 20,
    delay: float = 5.0,
    fmt: str = "jsonl",
    outdir: str = "output",
    keyword: Optional[str] = None,
):
    """爬取用户数据"""
    cookie = load_cookie()
    all_items: List[Dict] = []
    
    for page in range(1, pages + 1):
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries:
            try:
                print(f"正在获取第 {page} 页数据...")
                data = fetch_page(user_id, page, count, cookie)
                break
            except ValueError as e:
                retry_count += 1
                print(f"第 {page} 页获取失败，第 {retry_count} 次重试: {str(e)}")
                
                if "WAF" in str(e):
                    sleep_time = delay * retry_count * 2
                    print(f"WAF拦截，延迟 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                elif retry_count >= max_retries:
                    raise
                else:
                    sleep_time = delay * retry_count
                    print(f"将在 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
            except Exception as e:
                retry_count += 1
                print(f"第 {page} 页发生错误，第 {retry_count} 次重试: {str(e)}")
                if retry_count >= max_retries:
                    raise
                time.sleep(delay * retry_count)
        
        items = data.get("statuses", [])
        parsed = [parse_item(x) for x in items]
        
        if keyword:
            parsed = [p for p in parsed if p.get("text") and keyword in p.get("text")]
        
        all_items.extend(parsed)
        print(f"第 {page} 页 获取了 {len(items)} 条数据，筛选后保留 {len(parsed)} 条")
        
        # 页面间延迟
        if page < pages:
            page_delay = random.uniform(delay, delay * 2)
            print(f"页面间延迟 {page_delay:.1f} 秒...")
            time.sleep(page_delay)
    
    out_path = Path(outdir) / f"user_{user_id}.{fmt}"
    save_records(all_items, out_path, fmt)
    print(f"保存完成: {out_path} ({len(all_items)} 条)")


def main():
    parser = argparse.ArgumentParser(description="雪球博主爬取脚本")
    parser.add_argument("--user", required=True, help="雪球用户ID")
    parser.add_argument("--pages", type=int, default=5, help="抓取页数")
    parser.add_argument("--count", type=int, default=20, help="每页条数")
    parser.add_argument("--delay", type=float, default=5.0, help="基础延时(秒)")
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl", help="输出格式")
    parser.add_argument("--outdir", default="output", help="输出目录")
    parser.add_argument("--keyword", default=None, help="关键字过滤")
    args = parser.parse_args()
    
    crawl_user(
        user_id=args.user,
        pages=args.pages,
        count=args.count,
        delay=args.delay,
        fmt=args.format,
        outdir=args.outdir,
        keyword=args.keyword,
    )


if __name__ == "__main__":
    main()

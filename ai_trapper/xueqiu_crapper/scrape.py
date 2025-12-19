import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import random

import requests
from dotenv import load_dotenv

"""
雪 球 博 主 爬 取 脚 手 架
说明：
 - 需要有效的雪球 Cookie（至少包含 xq_a_token / xq_r_token），通过环境变量或 .env 文件提供。
 - 本脚本未内置账号登录，请先在浏览器登录雪球后拷贝 Cookie。
 - 当前环境网络受限，需在可联网环境下运行。
"""

API_URL = "https://xueqiu.com/v4/statuses/user_timeline.json"
# 更真实的浏览器User-Agent列表
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

DEFAULT_COOKIE = (
    "cookiesu=841765824303628; device_id=a3c94db6bb24789908ff6369fa620b55; "
    "Hm_lvt_1db88642e346389874251b5a1eded6e3=1765824326; HMACCOUNT=5257701D54F973D3; "
    "remember=1; xq_a_token=86512bca795c86c78299c7cc54284ee609f075ad; "
    "xqat=86512bca795c86c78299c7cc54284ee609f075ad; "
    "xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjYwMjk1NTE1MzUsImlzcyI6InVjIiwiZXhwIjoxNzY3NzYxMjQ1LCJjdG0iOjE3NjU4MjQzOTM1NzYsImNpZCI6ImQ5ZDBuNEFadXAifQ.c6Rvd2LWqfzViy-WSJuXDXd9_AxKzQCWtxb2F7J8UQZFoOfgjzi3xjmKoQecfw8AcT4i1FmddW8LKZE7IK6p5Dm50_8GB9W-2tdFCV0E2nnf8wuCMW3D98hjzBJ72LGqW1rPYR6-gjSAakjupxfmfZhVT5RiZjZ5k21cSs6N7pkwZsGyIOKzZvSB2KFCf2SoFqagBiKJzr4ZOsl7QtNKxzVMXwDdwax18TUE2o8QNriHALLAlmyTxunzlw2MbdPJMGlGd76gw-sdvshfeXwEMnpsP-OMG5dJgB-Xrk7H66vVaw13paZhlSOpzmxbuW6Qhg975uM_9h7BDEBiHwbBow; "
    "xq_r_token=c80eb4c267942e65bc3428ffadb747f4d1ddd2ef; xq_is_login=1; u=6029551535; "
    "acw_tc=1a0c652117659059866724822ea5619ea9d9c9c547b618a21ba28b9c8e41b7; is_overseas=0; "
    "Hm_lpvt_1db88642e346389874251b5a1eded6e3=1765906768; "
    ".thumbcache_f24b8bbe5a5934237bbc0eda20c1b6e7=i5F+uVLxzUHjYBjxu1d2v37PHtf8CPZIpSN9LJkje0VIUewdFbBlloN+N43hdbfbsRzvrJNc1D8rortZrdlZMA%3D%3D; "
    "ssxmod_itna=1-YqRxBQi=0Qd=G7DhxoD2KLeGI5GQqDXDUqAQdGglDFqApxDHFGhbl4hDUx0Ie4D792kyICk4cx5D/fP4GzDiLPGhDBWAFkQlqv0sofxhgGCeGeb2UsQyjO6_9wy6igSyoWu96RnLhB7GSfq6iDB3DbqDyF7Dnt4GGf4GwDGoD34DiDDpfD03Db4D_/lrD7xTNPpWQpjeDQ4GyDitDKLeQxi3DA4Dj0QhG/xT1NCusDDXsW/vx4Zv=DYPQqZiOdhFDAkhihD4Qx0tWDBLeeH7DGklRVgniyUkAabb7hPGuDG6kVQr8hOuW5cwGIwBurBRDer47R4GGxYGkFDriut92DiYe/24B4xR2FFi5NuOB_YqxDG8_efrkD4MYeuuzgqTMLshieq7qlx7lroMGD3oxhDQVY53d57Qe6W5ZDY42QK0DdYAeGDeo53Ar5mD4D; "
    "ssxmod_itna2=1-YqRxBQi=0Qd=G7DhxoD2KLeGI5GQqDXDUqAQdGglDFqApxDHFGhbl4hDUx0Ie4D792kyICk4coeDAibYWmsoDj4eYdm9xDsVAUTSGxVKmdMnYbkWFSnPq9/ZdeqX=GzrFXi97NLtfqikw/YGfLbq4Unq6eSLinCLPYS_XF9q2Psq0PGYdd2n3EBf6jRYW/C0nPem5Ezo0/9dR5kmd0/g5l8cRCCdvFZ1ujUfbnBmLFl37ogRG1z4jP/xv8L3Xel4jQ06fBG08X97Giedx1YANZRgE2OyO1SxYhYitqFG1EhDv2PD"
)


def load_cookie() -> str:
    load_dotenv()
    cookie = os.getenv("XUEQIU_COOKIE", DEFAULT_COOKIE)
    if not cookie:
        raise ValueError("请在环境变量或 .env 中设置 XUEQIU_COOKIE")
    return cookie


def get_random_headers() -> Dict[str, str]:
    """生成包含随机User-Agent和可能变化的其他头部的请求头"""
    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    # 可以根据需要动态调整 Sec-Ch-Ua-Platform 等字段
    if "Mac" in headers["User-Agent"]:
        headers["Sec-Ch-Ua-Platform"] = '"macOS"'
    return headers

def load_proxies() -> Optional[List[str]]:
    """从环境变量加载代理列表"""
    proxy_string = os.getenv("PROXY_POOL")
    if proxy_string:
        return [p.strip() for p in proxy_string.split(",") if p.strip()]
    return None

def fetch_page(user_id: str, page: int, count: int, cookie: str, timeout: int = 30) -> Dict:
    params = {
        "user_id": user_id,
        "page": page,
        "count": count,
    }
    
    # 使用随机User-Agent
    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    headers["Cookie"] = cookie
    
    # 增加随机延迟，模拟真实用户行为 (3-8秒)
    time.sleep(random.uniform(3, 8))
    
    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        
        # 检查返回内容是否包含WAF拦截特征
        if "aliyun_waf" in resp.text or "_waf_" in resp.text or "<textarea id=\"renderData\"" in resp.text:
            raise ValueError(
                f"请求被阿里云WAF防火墙拦截，可能需要更新Cookie或降低访问频率，status={resp.status_code}"
            )
        
        # 检查是否是登录页面
        if "登录" in resp.text and "xueqiu" in resp.text and "user" not in resp.text:
            raise ValueError(
                f"返回内容似乎是登录页面，可能 Cookie 失效/不完整，status={resp.status_code}"
            )
        
        # 检查是否是空白页面或者其他错误页面
        if not resp.text.strip() or len(resp.text.strip()) < 20:
            raise ValueError(
                f"返回内容为空或过短，可能是请求被拦截，status={resp.status_code}, body_length={len(resp.text)}"
            )
        
        return resp.json()
    except requests.RequestException as e:
        raise ValueError(f"网络请求失败: {str(e)}") from e
    except Exception as exc:  # 处理非JSON返回（如未授权、跳登录页等）
        raise ValueError(
            f"接口返回非JSON，可能 Cookie 失效/不完整，status={resp.status_code if 'resp' in locals() else 'unknown'}, "
            f"body={resp.text[:500] if 'resp' in locals() and hasattr(resp, 'text') else 'unknown'}"
        ) from exc


def parse_item(raw: Dict) -> Dict:
    # 仅提取常用字段，可按需扩展
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
    delay: float = 5.0,  # 默认延迟增加到5秒
    fmt: str = "jsonl",
    outdir: str = "output",
    keyword: Optional[str] = None,
):
    cookie = load_cookie()
    all_items: List[Dict] = []
    
    for page in range(1, pages + 1):
        retry_count = 0
        max_retries = 5  # 增加重试次数
        
        while retry_count < max_retries:
            try:
                print(f"正在获取第 {page} 页数据...")
                data = fetch_page(user_id, page, count, cookie)
                break  # 成功获取则跳出重试循环
            except ValueError as e:
                retry_count += 1
                print(f"第 {page} 页获取失败，第 {retry_count} 次重试: {str(e)}")
                
                if "WAF防火墙拦截" in str(e):
                    # 如果是WAF拦截，增加更长的延迟
                    sleep_time = delay * retry_count * 2
                    print(f"WAF拦截，增加延迟 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                elif retry_count >= max_retries:
                    raise e  # 达到最大重试次数，抛出异常
                else:
                    # 其他错误，正常延迟后重试
                    sleep_time = delay * retry_count
                    print(f"将在 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
            except Exception as e:
                retry_count += 1
                print(f"第 {page} 页发生未知错误，第 {retry_count} 次重试: {str(e)}")
                if retry_count >= max_retries:
                    raise e
                time.sleep(delay * retry_count)
        
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

    out_path = Path(outdir) / f"user_{user_id}.{fmt}"
    save_records(all_items, out_path, fmt)
    print(f"保存完成: {out_path} ({len(all_items)} 条)")


def main():
    parser = argparse.ArgumentParser(description="雪球博主爬取脚本")
    parser.add_argument("--user", required=True, help="雪球用户ID")
    parser.add_argument("--pages", type=int, default=5, help="抓取页数")
    parser.add_argument("--count", type=int, default=20, help="每页条数")
    parser.add_argument("--delay", type=float, default=5.0, help="两页之间的基础延时(秒)")  # 更新默认值
    parser.add_argument("--proxy-pool", type=str, help="逗号分隔的HTTPS代理地址列表，例如: https://ip:port,https://ip2:port")
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl", help="输出格式")
    parser.add_argument("--outdir", default="output", help="输出目录")
    parser.add_argument("--keyword", default=None, help="仅保留包含该关键字的帖子")
    args = parser.parse_args()

    # 如果命令行提供了代理池，则设置环境变量
    if args.proxy_pool:
        os.environ["PROXY_POOL"] = args.proxy_pool
        
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

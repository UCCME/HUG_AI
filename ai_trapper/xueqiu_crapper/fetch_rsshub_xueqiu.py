import argparse
import csv
import json
from pathlib import Path

import feedparser
import requests

"""
基于 RSSHub 的雪球用户信息抓取脚本

使用前提：
- 你已在可联网环境部署/使用 RSSHub，并为雪球配置了有效 Cookie（参考 https://docs.rsshub.app/routes/social-media#xue-qiu ）。
- 提供 RSSHub 基地址和雪球用户 ID，即可抓取用户动态并可选按关键字过滤。
"""


def fetch_feed(url: str):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def save(records, out_path: Path, fmt: str):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jsonl":
        with out_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    elif fmt == "csv":
        if not records:
            return
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    else:
        raise ValueError(f"不支持的格式: {fmt}")


def main():
    ap = argparse.ArgumentParser(description="从 RSSHub 获取雪球用户动态")
    ap.add_argument("--base", default="http://localhost:1200", help="RSSHub 基地址")
    ap.add_argument("--user", required=True, help="雪球用户ID，例如 6029551535")
    ap.add_argument("--keyword", default=None, help="仅保留包含该关键字的条目（标题或摘要）")
    ap.add_argument("--fmt", choices=["jsonl", "csv"], default="jsonl", help="输出格式")
    ap.add_argument("--outdir", default="output", help="输出目录")
    args = ap.parse_args()

    feed_url = f"{args.base}/xueqiu/user/{args.user}"
    feed = fetch_feed(feed_url)

    records = []
    for entry in feed.entries:
        item = {
            "title": entry.get("title"),
            "link": entry.get("link"),
            "summary": entry.get("summary", ""),
            "published": entry.get("published", ""),
        }
        if args.keyword:
            text = (item["title"] or "") + " " + (item["summary"] or "")
            if args.keyword not in text:
                continue
        records.append(item)

    out_path = Path(args.outdir) / f"user_{args.user}.{args.fmt}"
    save(records, out_path, args.fmt)
    print(f"完成：{len(records)} 条，保存至 {out_path}")


if __name__ == "__main__":
    main()

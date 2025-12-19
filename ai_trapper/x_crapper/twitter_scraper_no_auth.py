import asyncio
import json
from pathlib import Path
from typing import List, Dict
import twscrape
from twscrape import API, gather


async def setup_twitter_api():
    """设置Twitter API（需要认证账户）"""
    api = API()
    
    # 注意：你需要添加有效的Twitter账户才能使用此脚本
    # 示例：
    # await api.pool.add_account("your_username", "your_password", "your_email", "your_email_password")
    # await api.pool.login_all()
    
    return api


def save_tweets(tweets: List[Dict], output_file: Path):
    """保存推文到JSONL文件"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for tweet in tweets:
            f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
    
    print(f"已保存 {len(tweets)} 条推文到 {output_file}")


async def search_tweets(api, query: str, limit: int = 100):
    """搜索推文（需要认证账户）"""
    tweets = []
    try:
        # 使用搜索API获取推文
        tweet_list = await gather(api.search(query, limit=limit))
        for tweet in tweet_list:
            tweet_data = {
                "id": tweet.id,
                "username": tweet.user.username if tweet.user else "unknown",
                "display_name": tweet.user.displayname if tweet.user else "unknown",
                "content": tweet.rawContent,
                "created_at": tweet.date.isoformat() if tweet.date else None,
                "retweet_count": getattr(tweet, 'retweetCount', 0),
                "like_count": getattr(tweet, 'likeCount', 0),
                "reply_count": getattr(tweet, 'replyCount', 0),
                "quote_count": getattr(tweet, 'quoteCount', 0),
                "view_count": getattr(tweet, 'viewCount', None),
                "lang": getattr(tweet, 'lang', None),
                "url": getattr(tweet, 'url', None),
                "hashtags": list(getattr(tweet, 'hashtags', [])),
                "mentions": list(getattr(tweet, 'mentions', [])),
            }
            tweets.append(tweet_data)
    except Exception as e:
        print(f"搜索 '{query}' 的推文时出错: {e}")
    
    return tweets


async def scrape_queries(queries: List[str], limit: int = 100, output_dir: str = "output"):
    """爬取多个搜索查询的结果"""
    api = await setup_twitter_api()
    
    for query in queries:
        print(f"正在搜索 '{query}' 的推文...")
        # 清理查询字符串，用于文件名
        safe_query = "".join(c for c in query if c.isalnum() or c in " _-").strip()
        safe_query = safe_query.replace(" ", "_")
        
        tweets = await search_tweets(api, query, limit)
        
        if tweets:
            # 保存推文
            output_file = Path(output_dir) / f"search_{safe_query}_tweets.jsonl"
            save_tweets(tweets, output_file)
        else:
            print(f"搜索 '{query}' 没有获取到推文")


def main():
    # 注意：使用此脚本前必须配置Twitter账户
    print("注意：使用此脚本需要配置Twitter账户")
    print("请在 setup_twitter_api() 函数中添加您的Twitter账户信息")
    print("")
    
    # 预设的搜索查询列表（你可以根据需要修改）
    search_queries = [
        "Elon Musk",           # 关于埃隆·马斯克的推文
        "Apple iPhone",        # 关于苹果iPhone的推文
        "stock market",        # 关于股票市场的推文
        "artificial intelligence",  # 关于人工智能的推文
        "climate change",      # 关于气候变化的推文
        # 你可以在这里添加更多搜索查询
    ]
    
    # 设置参数
    limit = 50  # 每个搜索获取的推文数量
    output_dir = "output"
    
    print("开始爬取Twitter数据...")
    print(f"搜索查询: {', '.join(search_queries)}")
    print(f"每个搜索获取 {limit} 条推文")
    
    # 运行异步任务
    asyncio.run(scrape_queries(search_queries, limit, output_dir))
    
    print("Twitter数据爬取完成!")


if __name__ == "__main__":
    main()
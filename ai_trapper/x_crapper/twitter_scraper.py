import asyncio
import json
import os
import traceback
from pathlib import Path
from typing import List, Dict
import twscrape
from twscrape import API, gather


async def setup_twitter_api():
    """设置Twitter API（需要有效的Twitter账户）"""
    api = API()
    
    # 注意：你需要添加有效的Twitter账户才能使用此脚本
    # 示例：
    # await api.pool.add_account("your_username", "your_password", "your_email", "your_email_password")
    # await api.pool.login_all()
    
    try:
        print("正在添加账户...")
        # 添加你的账户信息
        await api.pool.add_account("Tst3pu6FWY9283", "!Jh19980808", "19011288807@189.cn", "!Jiehai987654")
        
        print("正在登录账户...")
        # 尝试登录所有账户并显示详细错误信息
        await api.pool.login_all()
        print("账户登录完成")
        
        # 检查是否有活动账户
        try:
            active_accounts = await api.pool.accounts_info()
            print(f"账户信息: {active_accounts}")
            
            # 根据返回类型处理账户信息
            active_count = 0
            if isinstance(active_accounts, dict):
                active_count = sum(1 for acc in active_accounts.values() if getattr(acc, 'active', False))
            elif isinstance(active_accounts, list):
                # 如果是列表，可能需要特殊处理
                active_count = len(active_accounts)
                
            print(f"活动账户数量: {active_count}")
            
            if active_count == 0:
                print("警告: 没有活动账户可用")
                print("可能的原因:")
                print("1. 账户凭据不正确")
                print("2. 邮箱IMAP设置不正确")
                print("3. 账户启用了双重认证")
                print("4. 账户被Twitter限制")
                
        except Exception as account_error:
            print(f"检查账户状态时出错: {account_error}")
            
    except Exception as e:
        print(f"登录过程中出现错误: {e}")
        print(f"详细错误信息: {traceback.format_exc()}")
    
    return api


def save_tweets(tweets: List[Dict], output_file: Path):
    """保存推文到JSONL文件"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for tweet in tweets:
            f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
    
    print(f"已保存 {len(tweets)} 条推文到 {output_file}")


async def fetch_user_tweets(api, username: str, limit: int = 100):
    """获取用户的推文"""
    tweets = []
    try:
        print(f"正在获取 {username} 的推文...")
        # 获取用户的推文
        tweet_list = await gather(api.user_tweets(username, limit=limit))
        for tweet in tweet_list:
            tweet_data = {
                "id": tweet.id,
                "username": username,
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
        print(f"成功获取 {len(tweets)} 条推文")
    except Exception as e:
        print(f"获取用户 {username} 的推文时出错: {e}")
        print(f"详细错误信息: {traceback.format_exc()}")
    
    return tweets


async def scrape_users(usernames: List[str], limit: int = 100, output_dir: str = "output"):
    """爬取多个用户的推文"""
    api = await setup_twitter_api()
    
    for username in usernames:
        print(f"正在获取用户 @{username} 的推文...")
        tweets = await fetch_user_tweets(api, username, limit)
        
        if tweets:
            # 保存推文
            output_file = Path(output_dir) / f"{username}_tweets.jsonl"
            save_tweets(tweets, output_file)
        else:
            print(f"用户 @{username} 没有获取到推文")


def main():
    # 注意：使用此脚本前必须配置Twitter账户
    print("注意：使用此脚本需要配置Twitter账户")
    print("请在 setup_twitter_api() 函数中添加您的Twitter账户信息")
    print("")
    
    # 预设的Twitter用户列表（你可以根据需要修改）
    twitter_users = [
        "elonmusk",           # 埃隆·马斯克
        "realDonaldTrump",     # 特朗普
        "BillGates",          # 比尔·盖茨
        "tim_cook",           # 苹果CEO蒂姆·库克
        "sundarpichai",       # 谷歌CEO桑达尔·皮查伊
        # 你可以在这里添加更多用户
    ]
    
    # 设置参数
    limit = 50  # 每个用户获取的推文数量
    output_dir = "output"
    
    print("开始爬取Twitter数据...")
    print(f"目标用户: {', '.join(twitter_users)}")
    print(f"每个用户获取 {limit} 条推文")
    
    # 运行异步任务
    asyncio.run(scrape_users(twitter_users, limit, output_dir))
    
    print("Twitter数据爬取完成!")


if __name__ == "__main__":
    main()
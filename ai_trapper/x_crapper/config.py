import os
from pathlib import Path

# Twitter爬虫配置
class TwitterConfig:
    # Twitter用户名列表
    TWITTER_USERS = [
        "HANA__BRAVE",
        "elonmusk",           # 埃隆·马斯克
        "realDonaldTrump",     # 特朗普
        "BillGates",          # 比尔·盖茨
        "tim_cook",           # 苹果CEO蒂姆·库克
        "sundarpichai",       # 谷歌CEO桑达尔·皮查伊
        # 你可以在这里添加更多用户
    ]
    
    # 每个用户获取的推文数量
    TWEET_LIMIT = 50
    
    # 输出目录
    OUTPUT_DIR = "output"
    
    # 数据库文件路径
    DB_PATH = "twitter_accounts.db"


# 定时任务配置
class SchedulerConfig:
    # 定时间隔（分钟）
    INTERVAL_MINUTES = 60
    
    # 是否只执行一次
    ONCE = False
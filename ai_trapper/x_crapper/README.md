# Twitter爬虫 (X Crapper)

## 简介

本项目用于爬取Twitter上博主的推文数据。使用[twscrape](https://github.com/vladkens/twscrape)库来实现数据爬取，该库通过模拟Twitter API来获取数据。

## 功能特点

- 获取指定用户的推文数据
- 支持批量爬取多个用户
- 搜索特定关键词的推文
- 保存为JSONL格式便于后续分析
- 可配置爬取参数

## 使用方法

### 环境准备

1. 安装 Python 3.8+
2. 安装依赖包：
   ```
   pip install twscrape
   ```
   
   或者使用 requirements.txt：
   ```
   pip install -r requirements.txt
   ```

### 配置Twitter账户（必需）

twscrape需要真实的Twitter账户来进行数据爬取。你需要至少一个Twitter账户来使用这个爬虫。

1. 编辑 `twitter_scraper.py` 文件中的 `setup_twitter_api` 函数
2. 添加你的Twitter账户信息：
   ```python
   await api.pool.add_account("username", "password", "email", "email_password")
   ```
   
   然后登录账户：
   ```python
   await api.pool.login_all()
   ```

### 配置爬取目标

你可以在 `config.py` 文件中配置：

1. 要爬取的Twitter用户名列表
2. 每个用户爬取的推文数量
3. 输出目录

### 运行爬虫

```bash
python twitter_scraper.py
```

## 输出格式

默认输出为 JSONL 格式 (每行一条 JSON 记录)。

输出字段：
- `id`: 推文ID
- `username`: 用户名
- `display_name`: 用户显示名称
- `content`: 推文内容
- `created_at`: 创建时间
- `retweet_count`: 转发数
- `like_count`: 点赞数
- `reply_count`: 回复数
- `quote_count`: 引用数
- `view_count`: 查看数
- `lang`: 语言
- `url`: 推文链接
- `hashtags`: hashtag标签列表
- `mentions`: 提及的用户列表

## 常见问题

### AttributeError: 'API' object has no attribute 'get_tweets'

这是由于twscrape库的API发生了变化。请确保你使用的是正确的方法调用方式：
- 使用 `api.user_tweets(username, limit=limit)` 获取用户推文
- 使用 `gather()` 函数来收集异步生成器的结果

### No active accounts. Stopping...

这个错误表明没有配置有效的Twitter账户。即使是在搜索模式下，twscrape也需要有效的账户才能工作。

### 安装问题

如果遇到版本兼容性问题，请尝试安装最新版本的twscrape：
```
pip install twscrape
```

## 注意事项

1. 使用真实的Twitter账户信息是必需的
2. Twitter有速率限制，不要过于频繁地爬取数据
3. 本工具仅供学习交流使用，请遵守相关法律法规
4. 爬取的数据仅限个人使用，不得用于商业用途
5. 如果遇到版本兼容性问题，请尝试安装最新版本的twscrape
# 雪球爬虫 (Xueqiu Crapper)

## 简介

本项目用于爬取雪球网博主的帖子数据。由于雪球网站具有较强的反爬虫机制，本项目提供了两种爬取方式：

1. 基于 requests 的常规爬虫 (`scrape.py`) - 适用于反爬虫机制较弱的情况
2. 基于 Selenium 的浏览器自动化爬虫 (`selenium_scrape.py`) - 适用于反爬虫机制较强的情况

## 使用方法

### 环境准备

1. 安装 Python 3.8+
2. 安装依赖包：
   ```
   pip install requests python-dotenv selenium
   ```
   
   如果要使用 Selenium 版本，还需要安装：
   ```
   pip install selenium
   ```

3. 下载 ChromeDriver 并将其加入系统 PATH：
   - 访问 https://chromedriver.chromium.org/
   - 下载与你 Chrome 浏览器版本匹配的 ChromeDriver
   - 将其解压并放入系统 PATH 中的任意目录

### 配置 Cookie

1. 在浏览器中登录雪球账户
2. 打开开发者工具 (F12)
3. 刷新页面，在 Network 标签中找到任意请求
4. 复制请求头中的完整 Cookie 字符串
5. 将其粘贴到 `.env` 文件中的 `XUEQIU_COOKIE` 变量中

示例 `.env` 文件：
```
XUEQIU_COOKIE=your_cookie_here
```

### 配置文件

项目包含一个配置文件 `scheduler_config.py`，可用于自定义定时任务和爬取参数：

```python
# 定时任务配置
class SchedulerConfig:
    # 定时间隔（分钟）
    INTERVAL_MINUTES = 30
    
    # 是否使用增量更新模式
    INCREMENTAL = True
    
    # 是否只执行一次
    ONCE = False

# 用户爬取配置
class ScraperConfig:
    # 雪球大V ID 列表 (精选21个，涵盖价值、量化、宏观、科技)
    USER_IDS = [
        1247347556,  # 大道无形我有型 (段永平)
        8152922548,  # 梁宏 (私募大佬)
        # ... 更多用户ID
    ]
    
    # 爬取页数（增量模式下减少页数）
    PAGES = 2
    
    # 每页条数
    COUNT = 20
    
    # 基础延迟（秒）
    DELAY = 3.0
    
    # 输出格式
    FORMAT = "jsonl"
    
    # 输出目录
    OUTDIR = "output"
    
    # 是否下载图片
    DOWNLOAD_IMAGES = True
```

### 运行爬虫

#### 常规版本 (requests)
```bash
python scrape.py --user 用户ID [--pages 页数] [--count 每页条数] [--delay 延迟秒数]
```

#### 浏览器自动化版本 (Selenium)
```bash
python selenium_scrape.py --user 用户ID [--pages 页数] [--count 每页条数] [--delay 延迟秒数]
```

#### 批量爬取多个用户
```bash
python scrape_multiple.py --users 用户ID1 用户ID2 用户ID3 [--pages 页数] [--count 每页条数] [--delay 延迟秒数]
```

#### 使用预设参数运行（无需输入参数）
```bash
python scrape_presets.py
```

此脚本会自动爬取预设的21位雪球知名用户数据：
- 页数：2页（增量模式下）
- 每页条数：20条
- 延迟：3.0秒
- 输出格式：jsonl
- 输出目录：output
- 下载图片：是

预设用户包括：
1. 1247347556 - 大道无形我有型 (段永平)
2. 8152922548 - 梁宏 (私募大佬)
3. 8290096439 - 唐朝 (财报分析)
4. 4776750571 - ETF拯救世界 (指数定投)
5. 3029406972 - 银行螺丝钉 (估值数据)
6. 8866762335 - 月风_投资笔记 (宏观策略)
7. 9922501069 - 进化论一平 (量化+基本面)
8. 1540320649 - 但斌 (争议大V，茅台铁粉)
9. 6146070786 - 持有封基 (低风险套利)
10. 1626966144 - 释老毛 (深度逻辑)
11. 8226064047 - 望京博格 (基金数据)
12. 1843652844 - 省心省力 (大消费)
13. 1658392837 - 疯狂的里海 (成长股)
14. 8602695282 - 仓佑加错 (TMT/科技)
15. 6622605342 - 即使是微弱的光 (医药/价值)
16. 4684984024 - 饭统戴老板 (深度商业故事，适合做文案素材)
17. 6661853655 - 闲来一坐s话投资 (长文逻辑)
18. 1636936458 - 不明真相的群众 (方三文)
19. 8270588636 - 朋克民族 (新能源/特斯拉)
20. 7650893043 - 股海小宁 (实盘交易/短线情绪)
21. 2347043226 - 你指定的用户

#### 增量更新模式

使用增量更新模式只获取最新数据并追加到现有文件中：

```bash
python scrape_presets.py --incremental
```

或

```bash
python selenium_scrape.py --user 用户ID --incremental
```

#### 格式化JSON文件

将爬取的JSONL文件格式化为更易读的形式：

```bash
# 格式化单个文件
python format_json.py --input input_file.jsonl --output formatted_output.jsonl

# 格式化整个目录中的所有JSONL文件
python format_json.py --directory output
```

#### 定时任务执行

##### 一次性执行
```bash
python scheduled_scraper.py --once
```

##### 定时间隔执行（默认30分钟）
```bash
python scheduled_scraper.py
```

##### 自定义间隔执行（例如15分钟）
```bash
python scheduled_scraper.py --interval 15
```

##### 定时增量更新执行
```bash
python scheduled_scraper.py --incremental
```

参数说明：
- `--user`: 必需，雪球用户ID
- `--users`: 批量爬取时使用，多个用户ID用空格分隔
- `--pages`: 可选，默认5，要爬取的页数
- `--count`: 可选，默认20，每页的条数
- `--delay`: 可选，默认3.0，请求间隔的基础延迟(秒)
- `--format`: 可选，输出格式 (jsonl 或 csv)，默认 jsonl
- `--outdir`: 可选，输出目录，默认 output
- `--keyword`: 可选，仅保留包含指定关键词的帖子
- `--download-images`: 可选，是否下载帖子中的图片
- `--incremental`: 可选，增量更新模式，只获取新数据并追加到现有文件
- `--interval`: 定时间隔执行时使用，指定间隔时间（分钟）
- `--once`: 定时任务中只执行一次

## 输出格式

默认输出为 JSONL 格式 (每行一条 JSON 记录)，也可选择 CSV 格式。

输出字段：
- `id`: 帖子ID
- `title`: 标题
- `text`: 内容
- `created_at`: 创建时间
- `retweet_count`: 转发数
- `reply_count`: 回复数
- `like_count`: 点赞数
- `view_count`: 查看数
- `pic_urls`: 图片URL列表（如果有）

## JSON格式化

为了提高可读性，爬虫现在会输出格式化的JSON数据，每个字段都会换行显示。

## 日志记录

定时任务执行时会自动在 `logs` 目录下生成日志文件，文件名包含执行时间戳。

## 注意事项

1. 请合理控制爬取频率，避免对服务器造成过大压力
2. Cookie 具有时效性，如遇认证失败请更新 Cookie
3. 如遇到反爬虫拦截，建议使用 Selenium 版本
4. 本工具仅供学习交流使用，请遵守相关法律法规
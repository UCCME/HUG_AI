# 雪球爬虫配置指南

## 🚀 快速开始

### 1. 获取雪球Cookie

#### 方法一：Chrome浏览器（推荐）

1. 打开Chrome浏览器，访问 https://xueqiu.com
2. 登录你的雪球账号
3. 按 `F12` 打开开发者工具
4. 切换到 `Network` (网络) 标签
5. 刷新页面 (F5)
6. 在请求列表中找到任意一个请求
7. 点击该请求，在右侧找到 `Request Headers`
8. 找到 `Cookie:` 字段，复制整个Cookie值

#### 方法二：使用EditThisCookie插件

1. 安装Chrome插件：EditThisCookie
2. 登录雪球网站
3. 点击插件图标
4. 点击"导出"按钮
5. 将导出的Cookie转换为字符串格式

### 2. 配置Cookie

```bash
# 进入目录
cd ai_trapper/xueqiu_crapper

# 复制配置文件
cp .env.example .env

# 编辑.env文件
# 将你的Cookie粘贴到XUEQIU_COOKIE=后面
```

`.env` 文件示例：
```
XUEQIU_COOKIE=xq_a_token=xxxxx; xq_r_token=xxxxx; u=xxxxx; ...
PROXY_POOL=
```

### 3. 运行爬虫

#### 方式一：使用快速脚本（推荐）

```bash
# 爬取所有预设的21个大V
python3 quick_scrape.py
```

#### 方式二：爬取单个用户

```bash
# 爬取指定用户（例如：段永平）
python3 scrape.py --user 1247347556 --pages 2 --count 20
```

#### 方式三：使用定时任务

```bash
# 每30分钟自动爬取一次
python3 scheduled_scraper.py
```

## 📋 预设的21个雪球大V

| 用户ID | 昵称 | 特点 |
|--------|------|------|
| 1247347556 | 大道无形我有型 | 段永平，价值投资 |
| 8152922548 | 梁宏 | 私募大佬 |
| 8290096439 | 唐朝 | 财报分析专家 |
| 4776750571 | ETF拯救世界 | 指数定投 |
| 3029406972 | 银行螺丝钉 | 估值数据 |
| 8866762335 | 月风_投资笔记 | 宏观策略 |
| 9922501069 | 进化论一平 | 量化+基本面 |
| 1540320649 | 但斌 | 茅台铁粉 |
| 6146070786 | 持有封基 | 低风险套利 |
| 1626966144 | 释老毛 | 深度逻辑 |
| 8226064047 | 望京博格 | 基金数据 |
| 1843652844 | 省心省力 | 大消费 |
| 1658392837 | 疯狂的里海 | 成长股 |
| 8602695282 | 仓佑加错 | TMT/科技 |
| 6622605342 | 即使是微弱的光 | 医药/价值 |
| 4684984024 | 饭统戴老板 | 商业故事 |
| 6661853655 | 闲来一坐s话投资 | 长文逻辑 |
| 1636936458 | 不明真相的群众 | 方三文 |
| 8270588636 | 朋克民族 | 新能源/特斯拉 |
| 7650893043 | 股海小宁 | 实盘交易 |
| 2347043226 | 自定义用户 | - |

## 📁 输出文件

爬取的数据会保存在 `output/` 目录下：

```
output/
├── user_1247347556.jsonl  # 段永平的帖子
├── user_8152922548.jsonl  # 梁宏的帖子
└── ...
```

每个文件包含：
- id: 帖子ID
- title: 标题
- text: 内容
- created_at: 发布时间
- retweet_count: 转发数
- reply_count: 评论数
- like_count: 点赞数
- view_count: 浏览数

## ⚠️ 注意事项

1. **Cookie有效期**：Cookie可能会过期，如果爬取失败，请重新获取Cookie
2. **访问频率**：默认延迟3秒，避免被封IP
3. **WAF防护**：如果遇到阿里云WAF拦截，增加延迟时间
4. **代理池**：如果需要使用代理，在.env中配置PROXY_POOL

## 🔧 高级配置

修改 `scheduler_config.py` 中的参数：

```python
class ScraperConfig:
    PAGES = 2           # 每用户爬取页数
    COUNT = 20          # 每页条数
    DELAY = 3.0         # 请求间隔（秒）
    FORMAT = "jsonl"    # 输出格式（jsonl/csv）
    OUTDIR = "output"   # 输出目录
```

## 🐛 常见问题

### Q: 提示"Cookie失效"
A: 重新登录雪球网站，获取新的Cookie

### Q: 被WAF拦截
A: 增加DELAY参数，降低访问频率

### Q: 爬取速度慢
A: 减少PAGES参数，或使用增量模式

### Q: 想爬取其他用户
A: 在scheduler_config.py的USER_IDS列表中添加用户ID

# 消息面数据获取系统

## 📖 概述

这是一个专业的消息面数据获取系统，整合了10个最常用的数据源，提供统一的接口来获取、分析和处理金融市场的消息面数据。

## 🎯 核心特性

### ✅ 10个专业数据源

**API直达型（5个）**
1. **Tushare Pro** - 官方新闻联播摘要
2. **AkShare** - 开源数据接口之王
3. **金十数据** - 清洗度最高的宏观数据
4. **财联社** - A股最快的短快讯
5. **巨潮资讯** - 官方法定披露渠道

**爬虫挖掘型（5个）**
6. **华尔街见闻** - 编辑筛选的大新闻
7. **东方财富** - 数据量最大的数据中心
8. **股吧** - 散户情绪（反向指标）
9. **雪球** - 聪明钱情绪
10. **i问财** - 自然语言搜索

### ✅ 核心功能

- 📰 **新闻获取** - 多源新闻、公告、快讯
- 🎯 **大新闻筛选** - 智能筛选重要新闻
- 💭 **情绪分析** - 综合多源情绪指标
- 📊 **数据整合** - 统一接口管理所有数据源
- 🚦 **信号生成** - 基于消息面生成交易信号
- 📡 **实时监控** - 支持实时监控和推送

## 🚀 快速开始

### 安装依赖

```bash
pip install akshare tushare requests pandas
```

### 基础使用

```python
from news.data_integrator import NewsDataIntegrator

# 创建整合器
integrator = NewsDataIntegrator()

# 获取个股所有消息面数据
data = integrator.get_all_news("600893")

# 只获取重要新闻
important_news = integrator.get_important_news_only()

# 综合情绪分析
sentiment = integrator.analyze_comprehensive_sentiment("600893")

# 生成交易信号
signal = integrator.generate_trading_signal("600893")
```

## 📚 目录结构

```
news/
├── __init__.py                 # 模块初始化
├── api_sources/                # API直达型数据源
│   ├── __init__.py
│   ├── tushare_source.py      # Tushare Pro
│   ├── akshare_source.py      # AkShare
│   ├── jin10_source.py        # 金十数据
│   ├── cls_source.py          # 财联社
│   └── cninfo_source.py       # 巨潮资讯
├── crawler_sources/            # 爬虫挖掘型数据源
│   ├── __init__.py
│   ├── wallstreetcn_source.py # 华尔街见闻
│   ├── eastmoney_source.py    # 东方财富
│   ├── guba_source.py         # 股吧
│   ├── xueqiu_source.py       # 雪球
│   └── iwencai_source.py      # i问财
├── data_integrator.py          # 数据整合器
├── examples/                   # 使用示例
│   ├── quick_start.py         # 快速开始
│   └── data_source_demo.py    # 数据源演示
└── README.md                   # 本文档
```

## 💡 使用场景

### 场景1：捕捉航空航天板块机会

```python
# 监控板块消息面
result = integrator.monitor_sector(
    sector="航空航天",
    keywords=["国防预算", "军工订单", "航空航天"]
)

# 获取板块龙头
from news.crawler_sources import IWencaiSource
iwencai = IWencaiSource()
leaders = iwencai.get_sector_leaders("航空航天")
```

### 场景2：事件驱动策略

```python
from news.api_sources import CninfoSource

# 监控重大公告
cninfo = CninfoSource()
announcements = cninfo.get_major_announcements("600893")

# 分类公告并评估影响
for _, row in announcements.iterrows():
    classification = cninfo.classify_announcement(row['title'])
    print(f"公告: {row['title']}")
    print(f"影响: {classification['impact']}")
```

### 场景3：情绪反向指标

```python
from news.crawler_sources import GubaSource

# 股吧反向指标
guba = GubaSource()
indicator = guba.get_sentiment_indicator("600893")

if indicator['signal'] == 'sell':  # 反向
    print("散户过度乐观，考虑反向操作")
```

### 场景4：实时监控

```python
from news.api_sources import CLSSource

# 实时监控财联社快讯
cls = CLSSource()

def on_new_news(item):
    print(f"新快讯: {item['title']}")
    # 处理新快讯...

cls.monitor_realtime(callback=on_new_news, interval=60)
```

## 🎓 进阶用法

### 自定义数据源组合

```python
# 只使用特定数据源
from news.api_sources import AkShareSource, CLSSource
from news.crawler_sources import WallstreetCNSource

akshare = AkShareSource()
cls = CLSSource()
wallstreetcn = WallstreetCNSource()

# 组合使用
news_data = akshare.get_stock_news("600893")
important_flash = cls.get_important_news()
major_news = wallstreetcn.get_important_news()
```

### 数据持久化

```python
import pandas as pd

# 获取数据
data = integrator.get_all_news("600893")

# 保存到CSV
for key, df in data.items():
    if isinstance(df, pd.DataFrame) and not df.empty:
        df.to_csv(f"{key}.csv", index=False)
```

### 定时任务

```python
import schedule
import time

def daily_monitor():
    """每日监控任务"""
    integrator = NewsDataIntegrator()
    
    # 监控航空航天板块
    result = integrator.monitor_sector("航空航天", ["国防", "军工"])
    
    # 生成报告
    print(f"板块新闻数: {result['news_count']}")
    print(f"龙头股票: {result['hot_stocks']}")

# 每天9点执行
schedule.every().day.at("09:00").do(daily_monitor)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## ⚠️ 注意事项

### 1. 数据源限制

- **Tushare Pro**: 需要注册并获取Token，免费版有积分限制
- **雪球**: 需要Cookie认证，部分功能可能受限
- **i问财**: 可能有反爬限制，建议控制请求频率

### 2. 网络问题

- 部分数据源可能需要稳定的网络连接
- 建议添加重试机制和异常处理

### 3. 数据质量

- 不同数据源的数据质量和时效性不同
- 建议交叉验证多个数据源
- 注意区分官方数据和社交媒体数据

### 4. 合规使用

- 遵守各数据源的使用协议
- 不要过度爬取
- 尊重版权和隐私

## 📊 数据源对比

| 数据源 | 类型 | 数据质量 | 更新频率 | 难度 | 最佳用途 |
|--------|------|----------|----------|------|----------|
| Tushare Pro | API | ⭐⭐⭐⭐⭐ | 实时 | 简单 | 历史数据、NLP训练 |
| AkShare | API | ⭐⭐⭐⭐ | 实时 | 简单 | 综合数据获取 |
| 金十数据 | API | ⭐⭐⭐⭐⭐ | 实时 | 简单 | 宏观数据、策略判断 |
| 财联社 | API | ⭐⭐⭐⭐⭐ | 秒级 | 简单 | 短线交易、实时监控 |
| 巨潮资讯 | API | ⭐⭐⭐⭐⭐ | 实时 | 中等 | 事件驱动策略 |
| 华尔街见闻 | 爬虫 | ⭐⭐⭐⭐⭐ | 实时 | 中等 | 大新闻筛选 |
| 东方财富 | 爬虫 | ⭐⭐⭐⭐ | 每日 | 简单 | 资金流向分析 |
| 股吧 | 爬虫 | ⭐⭐⭐ | 实时 | 中等 | 反向指标 |
| 雪球 | 爬虫 | ⭐⭐⭐⭐ | 实时 | 中等 | 聪明钱情绪 |
| i问财 | 爬虫 | ⭐⭐⭐⭐⭐ | 实时 | 中等 | 逻辑归因、快速筛选 |

## 🔗 相关资源

- [AkShare文档](https://akshare.akfamily.xyz/)
- [Tushare Pro文档](https://tushare.pro/document/2)
- [项目主页](https://github.com/your-repo)

## 📝 更新日志

### v1.0.0 (2025-01-17)
- ✅ 实现10个数据源
- ✅ 数据整合器
- ✅ 情绪分析
- ✅ 信号生成
- ✅ 使用示例

---

**版本**: v1.0.0  
**更新日期**: 2025-01-17  
**作者**: Aone Copilot

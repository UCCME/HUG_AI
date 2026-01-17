# 消息面数据获取指南

## 📰 消息面数据分类

### 1️⃣ 新闻资讯类

#### **财经新闻**
- **数据源**：
  - 新浪财经、东方财富、同花顺
  - 财联社、证券时报、中国证券报
  - Wind资讯、Bloomberg（国际）

- **获取内容**：
  - 标题、正文、发布时间
  - 相关股票代码
  - 新闻分类（政策、业绩、行业等）
  - 情绪标签（正面/负面/中性）

- **获取方式**：
  ```python
  # 示例：使用akshare获取新闻
  import akshare as ak
  
  # 东方财富新闻
  news_df = ak.stock_news_em(symbol="600893")  # 航发动力
  
  # 新浪财经新闻
  news_sina = ak.stock_news_sina(symbol="sh600893")
  ```

- **关键字段**：
  - `title`: 新闻标题
  - `content`: 新闻内容
  - `publish_time`: 发布时间
  - `source`: 新闻来源
  - `sentiment`: 情绪得分（需要自己分析）

---

#### **行业研报**
- **数据源**：
  - 券商研报（中信、国泰君安、华泰等）
  - 研究机构报告
  - 行业协会报告

- **获取内容**：
  - 行业趋势分析
  - 公司评级变化
  - 目标价调整
  - 盈利预测

- **获取方式**：
  ```python
  # 示例：获取研报
  import akshare as ak
  
  # 个股研报
  report_df = ak.stock_research_report_em(symbol="600893")
  
  # 机构评级
  rating_df = ak.stock_institute_recommend(symbol="600893")
  ```

---

### 2️⃣ 公司公告类

#### **重大公告**
- **数据源**：
  - 上交所、深交所官网
  - 巨潮资讯网
  - 东方财富、同花顺

- **重点公告类型**：
  ```
  ✅ 利好公告：
  - 业绩预增/大幅增长
  - 重大合同/订单
  - 股权激励计划
  - 战略合作协议
  - 资产重组
  - 股东增持
  
  ❌ 利空公告：
  - 业绩预亏/下滑
  - 违规处罚
  - 诉讼仲裁
  - 股东减持
  - 风险提示
  - 商誉减值
  ```

- **获取方式**：
  ```python
  # 示例：获取公司公告
  import akshare as ak
  
  # 个股公告
  announcement_df = ak.stock_notice_report(symbol="航发动力")
  
  # 公告分类
  announcement_type = ak.stock_notice_classify()
  ```

---

### 3️⃣ 政策法规类

#### **国家政策**
- **关注重点**：
  - 国防政策（军工板块）
  - 产业政策（新能源、半导体等）
  - 科技政策（人工智能、量子计算等）
  - 金融政策（降息、降准等）

- **数据源**：
  - 国务院官网
  - 发改委、工信部官网
  - 央行官网
  - 财政部官网

- **获取方式**：
  ```python
  # 政策新闻爬虫
  # 需要自己实现或使用第三方服务
  
  # 示例：监控关键词
  policy_keywords = [
      '国防预算', '军工订单', '航空航天',
      '科技创新', '产业升级', '政策支持'
  ]
  ```

---

### 4️⃣ 社交媒体类

#### **股吧/论坛**
- **数据源**：
  - 东方财富股吧
  - 雪球
  - 淘股吧
  - 集思录

- **获取内容**：
  - 帖子标题、内容
  - 评论数、点赞数
  - 发帖时间
  - 用户情绪

- **获取方式**：
  ```python
  # 示例：东方财富股吧
  import akshare as ak
  
  # 股吧帖子
  guba_df = ak.stock_comment_em(symbol="600893")
  
  # 情绪分析（需要自己实现）
  # 可以使用NLP模型分析文本情绪
  ```

---

#### **微博/Twitter**
- **数据源**：
  - 微博财经大V
  - 机构账号
  - KOL意见领袖

- **关注对象**：
  - 券商分析师
  - 财经媒体
  - 行业专家
  - 上市公司官方账号

---

### 5️⃣ 资金流向类

#### **北向资金**
- **数据源**：
  - 东方财富、同花顺
  - Wind、Choice

- **获取方式**：
  ```python
  import akshare as ak
  
  # 北向资金流向
  hsgt_df = ak.stock_hsgt_individual_em(symbol="600893")
  
  # 北向资金持股
  hsgt_hold = ak.stock_hsgt_hold_detail_em(symbol="600893")
  ```

---

#### **机构调研**
- **数据源**：
  - 上市公司公告
  - 东方财富、同花顺

- **获取方式**：
  ```python
  # 机构调研
  research_df = ak.stock_institute_research_em(symbol="600893")
  ```

---

### 6️⃣ 舆情监控类

#### **媒体曝光度**
- **监控指标**：
  - 新闻提及次数
  - 搜索热度
  - 话题讨论量
  - 传播速度

- **获取方式**：
  ```python
  # 百度指数
  import akshare as ak
  
  baidu_index = ak.baidu_search_index(
      word="航发动力",
      start_date="2024-01-01",
      end_date="2024-12-31"
  )
  
  # 微博指数
  weibo_index = ak.weibo_index(word="航空航天")
  ```

---

## 🔧 数据获取工具推荐

### **Python库**

#### 1. **akshare**（推荐）
```bash
pip install akshare
```

**优点**：
- ✅ 免费开源
- ✅ 数据源丰富
- ✅ 更新及时
- ✅ 中文文档完善

**主要功能**：
```python
import akshare as ak

# 新闻资讯
news = ak.stock_news_em(symbol="600893")

# 公司公告
announcement = ak.stock_notice_report(symbol="航发动力")

# 研报评级
report = ak.stock_research_report_em(symbol="600893")

# 资金流向
fund_flow = ak.stock_individual_fund_flow(symbol="600893")

# 北向资金
hsgt = ak.stock_hsgt_individual_em(symbol="600893")

# 股吧情绪
guba = ak.stock_comment_em(symbol="600893")
```

---

#### 2. **tushare**
```bash
pip install tushare
```

**优点**：
- ✅ 数据质量高
- ✅ 接口稳定
- ✅ 历史数据完整

**缺点**：
- ❌ 需要积分（免费版有限制）

---

#### 3. **efinance**
```bash
pip install efinance
```

**优点**：
- ✅ 东方财富数据
- ✅ 实时性好

---

### **商业数据服务**

#### 1. **Wind金融终端**
- 专业级数据
- 价格昂贵（几万/年）
- 适合机构

#### 2. **Choice金融终端**
- 东方财富旗下
- 价格适中
- 数据全面

#### 3. **聚宽/米筐**
- 量化平台
- 提供API
- 按需付费

---

## 📊 数据处理流程

### **1. 数据采集**
```python
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def collect_news_data(symbol, days=30):
    """采集新闻数据"""
    # 新闻
    news_df = ak.stock_news_em(symbol=symbol)
    
    # 公告
    announcement_df = ak.stock_notice_report(symbol=symbol)
    
    # 研报
    report_df = ak.stock_research_report_em(symbol=symbol)
    
    return {
        'news': news_df,
        'announcement': announcement_df,
        'report': report_df
    }
```

---

### **2. 情绪分析**
```python
from snownlp import SnowNLP

def analyze_sentiment(text):
    """
    分析文本情绪
    
    Returns:
        float: 0-1之间，越大越正面
    """
    s = SnowNLP(text)
    return s.sentiments

def batch_sentiment_analysis(df, text_column='title'):
    """批量情绪分析"""
    df['sentiment'] = df[text_column].apply(analyze_sentiment)
    return df
```

---

### **3. 热度计算**
```python
def calculate_heat_score(df, time_column='publish_time'):
    """
    计算热度得分
    
    考虑因素：
    - 新闻数量
    - 时间衰减
    - 来源权重
    """
    # 按日期分组统计
    daily_count = df.groupby(df[time_column].dt.date).size()
    
    # 计算移动平均
    ma = daily_count.rolling(window=7).mean()
    
    # 热度得分 = 当前数量 / 平均数量
    heat_score = daily_count / ma
    
    return heat_score
```

---

### **4. 数据整合**
```python
def integrate_news_data(symbol, date):
    """整合消息面数据"""
    # 采集数据
    data = collect_news_data(symbol)
    
    # 情绪分析
    news_sentiment = batch_sentiment_analysis(data['news'])
    
    # 计算热度
    heat_score = calculate_heat_score(data['news'])
    
    # 整合
    result = {
        'date': date,
        'symbol': symbol,
        'news_sentiment': news_sentiment['sentiment'].mean(),
        'news_count': len(news_sentiment),
        'heat_score': heat_score.iloc[-1] if len(heat_score) > 0 else 1.0,
        'has_major_announcement': check_major_announcement(data['announcement'])
    }
    
    return result
```

---

## 🎯 实战应用

### **航空航天板块消息面监控**

```python
# 监控股票池
aerospace_stocks = {
    '600893': '航发动力',
    '600760': '中航沈飞',
    '002013': '中航机电',
    '000768': '中航西飞'
}

# 关键词监控
keywords = [
    '国防预算', '军工订单', '航空航天',
    '军民融合', '装备采购', '技术突破',
    '合同签订', '业绩增长', '政策支持'
]

# 每日监控
def daily_monitor():
    for code, name in aerospace_stocks.items():
        # 采集数据
        data = collect_news_data(code)
        
        # 分析情绪
        sentiment = analyze_sentiment(data)
        
        # 检查关键词
        for keyword in keywords:
            if check_keyword_in_news(data, keyword):
                print(f"⚠️  {name} 出现关键词: {keyword}")
        
        # 生成报告
        generate_report(code, name, data, sentiment)
```

---

## ⚠️ 注意事项

### **1. 数据质量**
- 验证数据来源可靠性
- 过滤虚假信息
- 交叉验证多个数据源

### **2. 时效性**
- 实时监控重要公告
- 设置推送提醒
- 快速响应市场变化

### **3. 合规性**
- 遵守数据使用协议
- 不要过度爬取
- 尊重版权

### **4. 隐私保护**
- 不泄露个人信息
- 安全存储数据
- 加密敏感信息

---

## 📚 推荐资源

### **学习资料**
- akshare文档：https://akshare.akfamily.xyz/
- tushare文档：https://tushare.pro/document/2
- NLP情绪分析教程

### **数据源网站**
- 东方财富：http://www.eastmoney.com/
- 同花顺：http://www.10jqka.com.cn/
- 巨潮资讯：http://www.cninfo.com.cn/
- 上交所：http://www.sse.com.cn/
- 深交所：http://www.szse.cn/

---

**更新日期**: 2025-01-17

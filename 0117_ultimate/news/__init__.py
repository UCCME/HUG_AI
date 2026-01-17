"""
消息面数据获取系统

支持10个专业数据源：
- API直达型：Tushare、AkShare、金十数据、财联社、巨潮资讯
- 爬虫挖掘型：华尔街见闻、东方财富、股吧、雪球、同花顺问财
"""

__version__ = "1.0.0"
__author__ = "Aone Copilot"

from .api_sources import *
from .crawler_sources import *

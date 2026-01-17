"""
爬虫挖掘型数据源
需要网页解析和反爬处理的高价值数据源
"""

from .wallstreetcn_source import WallstreetCNSource
from .eastmoney_source import EastMoneySource
from .guba_source import GubaSource
from .xueqiu_source import XueqiuSource
from .iwencai_source import IWencaiSource

__all__ = [
    'WallstreetCNSource',
    'EastMoneySource',
    'GubaSource',
    'XueqiuSource',
    'IWencaiSource'
]

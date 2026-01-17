"""
API直达型数据源
提供结构化的金融数据接口
"""

from .tushare_source import TushareSource
from .akshare_source import AkShareSource
from .jin10_source import Jin10Source
from .cls_source import CLSSource
from .cninfo_source import CninfoSource

__all__ = [
    'TushareSource',
    'AkShareSource',
    'Jin10Source',
    'CLSSource',
    'CninfoSource'
]

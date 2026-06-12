"""lookscanned - Make PDF documents look like they were scanned."""

from .locale import get_lang, set_lang, tr
from .scanner import ScanConfig, look_scanned

__version__ = "0.1.0"
__all__ = ["ScanConfig", "look_scanned", "launch", "get_lang", "set_lang", "tr"]

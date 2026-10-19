"""
Реэкспорт констант событий HR для удобства.
Определены в core.events.HREvents.
"""
from core.events import HREvents as HR  # noqa: F401

__all__ = ["HR"]
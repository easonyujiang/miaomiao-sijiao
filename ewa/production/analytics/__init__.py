"""Analytics 框架 — 事件追踪与分析接口。

DEMO 阶段通过 visitor_events 表和 SQLite 记录事件。
生产阶段通过此模块接入专业分析平台。
"""

from ewa.production.analytics.interfaces import AnalyticsBackend, AnalyticsEvent

__all__ = ["AnalyticsBackend", "AnalyticsEvent"]

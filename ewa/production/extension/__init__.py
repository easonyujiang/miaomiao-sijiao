"""Extension 框架 — 插件领域抽象接口。

DEMO 阶段使用本地字幕 JSON 文件和离线 FAQ 字典。
生产阶段通过此模块接入实时字幕 API 和 RAG 问答。
"""

from ewa.production.extension.interfaces import (
    SubtitleProvider,
    VideoMatcher,
    QAService,
)

__all__ = ["SubtitleProvider", "VideoMatcher", "QAService"]

"""妙喵私教 — Lesson 模块

视频课程学习相关的核心实现：
- scoring: 关键词 + LLM 混合评分引擎
- store: SQLite 学习状态持久化
- feedback: 猫咪反馈消息生成
- faq: 离线 FAQ 知识库
- subtitle: 字幕加载、缓存、搜索与视频匹配
"""

from ewa.extension.scoring import score_answer, score_answer_with_llm
from ewa.extension.store import LessonStore, get_session, persist_session, set_db_path
from ewa.extension.feedback import build_cat_message, build_cat_feedback, calc_cat_state
from ewa.extension.faq import match_offline_faq
from ewa.extension.subtitle import (
    get_video_cache,
    load_subtitles,
    match_bilibili_video,
    get_context_subtitles,
    search_subtitles,
)

__all__ = [
    "score_answer",
    "score_answer_with_llm",
    "LessonStore",
    "get_session",
    "persist_session",
    "set_db_path",
    "build_cat_message",
    "calc_cat_state",
    "match_offline_faq",
    "get_video_cache",
    "load_subtitles",
    "match_bilibili_video",
    "get_context_subtitles",
    "search_subtitles",
]

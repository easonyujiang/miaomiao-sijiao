"""字幕工具

- 加载字幕 JSON 文件
- 字幕缓存
- B站/抖音视频标题匹配
- 时间窗口上下文检索
- 字幕全文搜索
"""

from __future__ import annotations

import json

from ewa.config import SUBTITLE_DIR, SCORED_VIDEOS

# 简单内存缓存
_video_cache: dict[str, dict] = {}
_subtitle_cache: dict[str, list[dict]] = {}


# ── 视频索引 ─────────────────────────────────────────────────

def load_scored_videos() -> list[dict]:
    """加载已评分的视频列表。"""
    if not SCORED_VIDEOS.exists():
        return []
    with open(SCORED_VIDEOS, encoding="utf-8") as f:
        return json.load(f)


# ── 字幕加载与缓存 ───────────────────────────────────────────

def load_subtitles(bvid: str) -> list[dict]:
    """加载指定 bvid 的字幕（带缓存）。"""
    if bvid in _subtitle_cache:
        return _subtitle_cache[bvid]
    path = SUBTITLE_DIR / f"{bvid}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    subs = data.get("subtitles", [])
    _subtitle_cache[bvid] = subs
    return subs


# ── 视频匹配 ─────────────────────────────────────────────────

def match_bilibili_video(title: str) -> dict | None:
    """用标题关键词匹配 B 站已下载字幕库中最相关的视频。"""
    scored = load_scored_videos()
    if not scored:
        for path in SUBTITLE_DIR.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                scored.append({
                    "bvid": data.get("bvid", path.stem),
                    "title": data.get("title", ""),
                    "subtitle_count": len(data.get("subtitles", [])),
                })
            except Exception:
                pass

    if not scored:
        return None

    title_chars = set(title)
    best, best_score = None, 0
    for v in scored:
        v_chars = set(v.get("title", ""))
        overlap = len(title_chars & v_chars)
        if overlap > best_score:
            best_score = overlap
            best = v

    if best and best_score >= 3:
        return best
    return None


# ── 字幕检索 ─────────────────────────────────────────────────

def get_context_subtitles(bvid: str, current_sec: int, window: int = 30) -> list[dict]:
    """返回当前时间戳前后 window 秒的字幕句子。"""
    subs = load_subtitles(bvid)
    if not subs:
        return []
    lo, hi = current_sec - window, current_sec + window
    return [s for s in subs if lo <= s.get("start", 0) <= hi]


def search_subtitles(bvid: str, query: str, top_k: int = 3) -> list[dict]:
    """在字幕中搜索与 query 最相关的片段（离线回退用）。"""
    subs = load_subtitles(bvid)
    if not subs:
        return []

    query_chars = set(query)
    scored = []
    for s in subs:
        text = s.get("text", "")
        text_chars = set(text)
        overlap = len(query_chars & text_chars)
        if overlap >= 3:
            scored.append((overlap, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:top_k]]


# ── 缓存管理 ─────────────────────────────────────────────────

def get_video_cache() -> dict[str, dict]:
    """获取视频注册缓存（模块级）。"""
    return _video_cache


def clear_cache() -> None:
    """清空所有内存缓存。"""
    _video_cache.clear()
    _subtitle_cache.clear()

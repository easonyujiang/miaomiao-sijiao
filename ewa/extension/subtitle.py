"""字幕工具

- 加载字幕 JSON（按 BV 号精确匹配）
- 内存缓存
- 标题回退匹配（Jaccard 相似度）
- 时间窗口上下文检索
- 字幕全文子串搜索
"""

from __future__ import annotations

import json

from ewa.config import SUBTITLE_DIR, SCORED_VIDEOS

# 内存缓存
_video_cache: dict[str, dict] = {}
_subtitle_cache: dict[str, list[dict]] = {}


# ── 视频索引 ─────────────────────────────────────────────────

def load_scored_videos() -> list[dict]:
    """加载已评分的视频列表。"""
    if not SCORED_VIDEOS.exists():
        return []
    with open(SCORED_VIDEOS, encoding="utf-8") as f:
        return json.load(f)


# ── 字幕加载 ─────────────────────────────────────────────────

def load_subtitles(bvid: str) -> list[dict]:
    """按 BV 号加载字幕（带缓存）。"""
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


def _scan_subtitle_files() -> list[dict]:
    """扫描字幕目录，返回全部可用的 {bvid, title} 列表。"""
    entries: list[dict] = []
    if not SUBTITLE_DIR.exists():
        return entries
    for path in SUBTITLE_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            entries.append({
                "bvid": data.get("bvid", path.stem),
                "title": data.get("title", ""),
                "subtitle_count": len(data.get("subtitles", [])),
            })
        except Exception:
            pass
    return entries


# ── 视频匹配 ─────────────────────────────────────────────────

def _jaccard(a: str, b: str) -> float:
    """两个字符串的 Jaccard 相似度（字符级）。"""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def match_bilibili_video(video_id: str = "", title: str = "") -> dict | None:
    """匹配字幕库中最相关的视频。

    优先 BV 号精确匹配；回退到标题 Jaccard 相似度（阈值 0.3）。
    """
    entries = _scan_subtitle_files()
    if not entries:
        return None

    # 1. BV 号精确匹配
    if video_id:
        for v in entries:
            if v["bvid"] == video_id:
                return v

    # 2. 标题 Jaccard 回退
    if title:
        best, best_score = None, 0.0
        for v in entries:
            score = _jaccard(title, v.get("title", ""))
            if score > best_score:
                best_score = score
                best = v
        if best and best_score >= 0.3:
            return best

    return None


# ── 字幕检索 ─────────────────────────────────────────────────

def get_context_subtitles(bvid: str, current_sec: int, window: int = 30) -> list[dict]:
    """返回当前时间戳前后 window 秒的字幕。"""
    subs = load_subtitles(bvid)
    if not subs:
        return []
    lo, hi = current_sec - window, current_sec + window
    return [s for s in subs if lo <= s.get("start", 0) <= hi]


def search_subtitles(bvid: str, query: str, top_k: int = 3) -> list[dict]:
    """在字幕中搜索与 query 最相关的片段。

    两层匹配：先子串匹配，不够时回退到 Jaccard 字符集。
    """
    subs = load_subtitles(bvid)
    if not subs:
        return []

    exact_matches: list[dict] = []
    fuzzy_matches: list[tuple[float, dict]] = []

    for s in subs:
        text = s.get("text", "")
        # 子串匹配
        if query in text:
            exact_matches.append(s)
        else:
            score = _jaccard(query, text)
            if score >= 0.15:
                fuzzy_matches.append((score, s))

    # 优先返回精确匹配
    results = exact_matches[:top_k]
    if len(results) < top_k:
        fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
        results.extend(s for _, s in fuzzy_matches[: top_k - len(results)])

    return results[:top_k]


# ── 缓存管理 ─────────────────────────────────────────────────

def get_video_cache() -> dict[str, dict]:
    return _video_cache


def clear_cache() -> None:
    _video_cache.clear()
    _subtitle_cache.clear()

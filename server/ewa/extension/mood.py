"""妙喵情绪与形态服务

把任意文本映射为猫咪形态（CatStateKey），并提供分句标注能力。
"""

from __future__ import annotations

import re
from typing import Any

# 与扩展端、网站端共用的形态 key
CatStateKey = str

CAT_STATES: list[CatStateKey] = [
    "idle",
    "watching",
    "listening",
    "analyzing",
    "correcting",
    "celebrating",
    "reward",
    "failed",
    "levelup",
    "seeking",
    "sleepy",
    "stretch",
    "tail",
]

# 优先级保护：播放期间不能被 idle 闲聊/随机动作打断
FORM_PROTECTED: list[CatStateKey] = ["analyzing", "celebrating", "failed", "levelup"]

# 情绪关键词 -> 形态
_MOOD_KEYWORDS: list[tuple[list[str], CatStateKey]] = [
    # 升级/胜利/撒娇
    (["升级", "满星", "完美", "太棒了", "好棒", "答对", "通过", "胜利"], "celebrating"),
    (["小鱼干", "奖励", "给你鱼"], "reward"),
    # 学习/专注
    (["讲解", "关键", "注意", "重点是", "意味着", "构成要件", "法条", "条款"], "watching"),
    (["别太久", "做笔记", "认真听", "专心"], "watching"),
    # 思考
    (["分析", "想想", "思考一下", "让我看看"], "analyzing"),
    # 倾听/提问
    (["好问题", "问我", "你说", "歪头", "呢？", "吗？"], "listening"),
    # 纠正/失败/安慰
    (["不对", "错了", "不成立", "偏了", "搞反"], "correcting"),
    (["没关系", "再看一遍", "别灰心", "差一点", "失败"], "failed"),
    # 跳转
    (["跳回", "回到", "SEEK", "时间点"], "seeking"),
    # 困倦/休息
    (["困", "休息", "打个盹", "zzz"], "sleepy"),
    # 小动作
    (["伸懒腰", "拉伸"], "stretch"),
    (["甩尾巴", "摇尾巴"], "tail"),
]


def mood_for(text: str) -> CatStateKey:
    """根据文本内容判断最合适的猫形态。"""
    if not text:
        return "idle"

    t = text.strip()
    lowered = t.lower()

    for keywords, form in _MOOD_KEYWORDS:
        if any(kw in t for kw in keywords):
            return form

    # 默认：以标点语气做兜底
    if t.endswith(("！", "!")):
        return "celebrating"
    if t.endswith(("？", "?")):
        return "listening"
    if t.endswith(("…", "...", "zzz")):
        return "sleepy"

    return "idle"


def split_sentences(text: str, max_len: int = 80) -> list[str]:
    """把文本切成适合一句一切形态的小段。

    优先按句子切分（句号/问号/感叹号/换行），超长句再按逗号或长度截断。
    """
    if not text:
        return []

    # 统一换行并清理多余空白
    text = re.sub(r"\s+", " ", text.strip())

    # 1. 按句子边界切分
    parts = re.split(r"([。！？!\?]\s*)", text)
    sentences: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        current += part
        if re.search(r"[。！？!?]\s*$", part):
            if current.strip():
                sentences.append(current.strip())
            current = ""
    if current.strip():
        sentences.append(current.strip())

    # 2. 长句再截断到 max_len 以内
    result: list[str] = []
    for s in sentences:
        while len(s) > max_len:
            # 优先在逗号/分号处截断
            cut = max(
                s.rfind("，", 0, max_len),
                s.rfind(",", 0, max_len),
                s.rfind("；", 0, max_len),
            )
            if cut <= 0:
                cut = max_len
            result.append(s[:cut].strip())
            s = s[cut:].lstrip("，,；")
        if s.strip():
            result.append(s.strip())

    return result


def calc_duration(text: str, ms_per_char: int = 50, min_ms: int = 1200) -> int:
    """根据文本长度计算朗读/展示时长。"""
    if not text:
        return min_ms
    # 标点额外给一点停顿
    extra = sum(1 for c in text if c in "，。！？；、：")
    return max(min_ms, (len(text) + extra) * ms_per_char)


def build_segments(
    text: str,
    seek_to_sec: int | None = None,
    default_form: CatStateKey | None = None,
) -> list[dict[str, Any]]:
    """把一段文本拆成带形态和时长的 segments。

    如果传了 seek_to_sec，会把它绑定到最后一句（通常是含跳转提示的句子）。
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    segments = []
    for i, s in enumerate(sentences):
        form = default_form or mood_for(s)
        seg: dict[str, Any] = {
            "text": s,
            "form": form,
            "duration_ms": calc_duration(s),
        }
        # 跳转时间戳绑定到文本含"跳"/"回"/"SEEK"或最后一句
        if seek_to_sec is not None and (
            i == len(sentences) - 1 or "跳" in s or "回" in s or "SEEK" in s
        ):
            seg["seek_to_sec"] = seek_to_sec
        segments.append(seg)

    return segments

"""
妙喵私教 — 浏览器插件扩展 API
提供给 Chrome Extension 使用的端点：
- POST /api/ext/register_video  注册视频并匹配B站字幕
- POST /api/ext/chat            带当前时间戳的视频问答（LLM + 离线回退）
- GET  /api/ext/health          后端连通性检查

业务逻辑委托给 ewa.lesson 模块：
- faq: 离线 FAQ 知识库匹配
- subtitle: 字幕加载/缓存/搜索/视频匹配
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ewa.config import SUBTITLE_DIR, MOONSHOT_API_KEY, DEEPSEEK_API_KEY
from ewa.llm import LLMClient
from ewa.extension.faq import match_offline_faq
from ewa.extension.subtitle import (
    get_video_cache,
    load_subtitles,
    match_bilibili_video,
    get_context_subtitles,
    search_subtitles,
)

router = APIRouter(prefix="/api/ext", tags=["extension"])


# ── 请求/响应模型 ────────────────────────────────────────────

class RegisterVideoRequest(BaseModel):
    video_id: str
    title: str
    platform: str  # "douyin" | "bilibili"


class ChatRequest(BaseModel):
    message: str
    video_id: str
    platform: str
    current_time_sec: int = 0


# ── 端点 ────────────────────────────────────────────────────

@router.get("/health")
async def health() -> dict[str, Any]:
    """连通性检查（Extension 可用此端点判断后端是否在线）。"""
    llm_available = bool(MOONSHOT_API_KEY or DEEPSEEK_API_KEY)
    subtitle_count = len(list(SUBTITLE_DIR.glob("*.json"))) if SUBTITLE_DIR.exists() else 0
    return {
        "status": "ok",
        "llm_available": llm_available,
        "subtitle_files": subtitle_count,
        "cached_videos": len(get_video_cache()),
    }


@router.post("/register_video")
async def register_video(req: RegisterVideoRequest) -> dict[str, Any]:
    """注册视频：
    - 抖音视频：用标题匹配 B 站字幕库
    - B站视频：直接检查字幕是否存在
    """
    video_cache = get_video_cache()
    ckey = f"{req.platform}:{req.video_id}"
    if ckey in video_cache:
        return video_cache[ckey]

    result: dict[str, Any] = {
        "video_id": req.video_id,
        "platform": req.platform,
        "title": req.title,
        "matched_bilibili": None,
        "subtitle_count": 0,
    }

    if req.platform == "douyin":
        match = match_bilibili_video(title=req.title)
        if match:
            subs = load_subtitles(match["bvid"])
            result["matched_bilibili"] = {
                "bvid": match["bvid"],
                "title": match.get("title", ""),
                "subtitle_count": len(subs),
            }
            result["subtitle_count"] = len(subs)
    elif req.platform == "bilibili":
        # B站直接用 BV 号精确加载
        subs = load_subtitles(req.video_id)
        if not subs:
            # 无精确匹配时回退标题搜索
            match = match_bilibili_video(video_id=req.video_id, title=req.title)
            if match:
                subs = load_subtitles(match["bvid"])
        result["subtitle_count"] = len(subs)

    video_cache[ckey] = result
    return result


@router.post("/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    """视频问答：根据当前时间戳，截取字幕上下文，调用 LLM 作答。

    三层回退策略：
    1. LLM（Kimi → DeepSeek）— 最佳
    2. 字幕搜索 — LLM 不可用时搜索相关字幕片段作为回答依据
    3. 离线 FAQ — 匹配预设知识库
    """
    # 确定 bvid
    if req.platform == "douyin":
        video_cache = get_video_cache()
        ckey = f"douyin:{req.video_id}"
        cached = video_cache.get(ckey, {})
        matched = cached.get("matched_bilibili")
        bvid = matched["bvid"] if matched else None
    else:
        bvid = req.video_id

    # 获取字幕上下文
    context_subs = []
    if bvid:
        context_subs = get_context_subtitles(bvid, req.current_time_sec, window=45)

    context_text = ""
    if context_subs:
        lines = [
            f"[{int(s['start'] // 60)}:{int(s['start'] % 60):02d}] {s['text']}"
            for s in context_subs
        ]
        context_text = "\n".join(lines)

    # ── 第一层：LLM ────────────────────────────────────────
    ctx_block = (
        f"以下是当前时间段（前后45秒）的视频字幕内容：\n\n{context_text}"
        if context_text
        else "当前暂无字幕数据，请根据问题尽力回答。"
    )
    system = f"""你是妙喵，一只帮助用户学习教学视频的猫咪私教。
你的回答简洁、有个性，像一只认真但可爱的小猫。
用户正在观看视频，当前播放时间：{req.current_time_sec} 秒（{req.current_time_sec // 60}:{req.current_time_sec % 60:02d}）。

{ctx_block}

回答要求：
1. 如果涉及视频中某个具体时间点，在回答末尾用格式 [SEEK:秒数] 标注，例如 [SEEK:72]
2. 法学题目必须引用刑法条款或案例名，不能凭感觉作答
3. 回答不超过200字"""

    llm_client = LLMClient()
    llm_answer = await llm_client.chat(system, req.message, max_tokens=600)

    if llm_answer:
        seek_to_sec = None
        m = re.search(r"\[SEEK:(\d+)\]", llm_answer)
        if m:
            seek_to_sec = int(m.group(1))
            llm_answer = re.sub(r"\[SEEK:\d+\]", "", llm_answer).strip()

        return {
            "answer": llm_answer,
            "seek_to_sec": seek_to_sec,
            "context_used": len(context_subs),
            "bvid": bvid,
            "offline": False,
        }

    # ── 第二层：字幕搜索 ────────────────────────────────────
    if bvid:
        relevant = search_subtitles(bvid, req.message, top_k=3)
        if relevant:
            lines = [
                f"[{int(s['start'] // 60)}:{int(s['start'] % 60):02d}] {s['text']}"
                for s in relevant
            ]
            seek_sec = relevant[0].get("start", 0) if relevant else None
            return {
                "answer": (
                    "猫猫在视频中找到了相关内容，喵~\n\n"
                    + "\n".join(lines)
                    + "\n\n💡 建议回看这些片段加深理解。"
                ),
                "seek_to_sec": seek_sec,
                "context_used": len(relevant),
                "bvid": bvid,
                "offline": True,
            }

    # ── 第三层：离线 FAQ ────────────────────────────────────
    faq_answer = match_offline_faq(req.message)
    if faq_answer:
        return {
            "answer": "🤖 猫猫暂时连不上后端大脑，但我知道这个：\n\n" + faq_answer,
            "seek_to_sec": None,
            "context_used": 0,
            "bvid": bvid,
            "offline": True,
        }

    # ── 完全无数据 ──────────────────────────────────────────
    return {
        "answer": (
            "喵呜…猫猫现在还回答不了这个问题 😿\n\n"
            "可能的原因：\n"
            "1. 后端 LLM 未配置（需要设置 MOONSHOT_API_KEY 或 DEEPSEEK_API_KEY）\n"
            "2. 当前视频没有字幕数据\n"
            "3. 这个问题不在我的知识范围内\n\n"
            "试试问关于「正当防卫的构成要件」或直接开始答题闯关吧！"
        ),
        "seek_to_sec": None,
        "context_used": 0,
        "bvid": bvid,
        "offline": True,
    }

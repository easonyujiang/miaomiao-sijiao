"""
妙喵私教 — 浏览器插件扩展 API
提供给 Chrome Extension 使用的端点：
- POST /api/ext/register_video  注册视频并匹配B站字幕
- POST /api/ext/chat            带当前时间戳的视频问答（LLM + 离线回退）
- GET  /api/ext/health          后端连通性检查
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ewa.config import SUBTITLE_DIR, SCORED_VIDEOS, MOONSHOT_API_KEY, DEEPSEEK_API_KEY

router = APIRouter(prefix="/api/ext", tags=["extension"])

# 简单内存缓存
_video_cache: dict[str, dict] = {}
_subtitle_cache: dict[str, list[dict]] = {}


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


# ── 离线 FAQ 知识库 ─────────────────────────────────────────

OFFLINE_FAQ = {
    "正当防卫": {
        "answer": (
            "正当防卫需要满足五个构成要件：\n"
            "1️⃣ 起因条件——必须存在现实的不法侵害\n"
            "2️⃣ 时间条件——不法侵害必须正在进行\n"
            "3️⃣ 对象条件——只能针对侵害人本人\n"
            "4️⃣ 主观条件——必须具有防卫意图\n"
            "5️⃣ 限度条件——不能明显超过必要限度\n\n"
            "此外，刑法第20条第3款规定了特殊防卫权：对正在进行的行凶、杀人、抢劫、强奸、绑架等"
            "严重危及人身安全的暴力犯罪，防卫致不法侵害人伤亡的，不负刑事责任。"
        ),
        "keywords": ["正当防卫", "构成要件", "要件", "条件", "防卫"],
    },
    "假想防卫": {
        "answer": (
            "假想防卫是指客观上不存在不法侵害，但行为人误以为存在而实施防卫行为。\n"
            "假想防卫不构成正当防卫！因为正当防卫要求不法侵害客观存在。\n"
            "处理方式：按事实认识错误处理——有过失的定过失犯罪，无过失的属意外事件。"
        ),
        "keywords": ["假想防卫", "假想", "误以为", "想象"],
    },
    "防卫过当": {
        "answer": (
            "防卫过当是指防卫行为明显超过必要限度造成重大损害。\n"
            "防卫过当应当负刑事责任，但是应当减轻或者免除处罚。\n"
            "注意：特殊防卫（刑法第20条第3款）不存在防卫过当的问题。"
        ),
        "keywords": ["防卫过当", "过当", "超过", "限度", "过度"],
    },
    "特殊防卫": {
        "answer": (
            "特殊防卫（无限防卫权）规定在刑法第20条第3款：\n"
            "对正在进行的行凶、杀人、抢劫、强奸、绑架以及其他严重危及人身安全的暴力犯罪，"
            "采取防卫行为，造成不法侵害人伤亡的，不属于防卫过当，不负刑事责任。\n"
            "适用条件：必须是严重危及人身安全的暴力犯罪，且侵害正在进行。"
        ),
        "keywords": ["特殊防卫", "无限防卫", "第3款", "20条", "伤亡"],
    },
    "互殴": {
        "answer": (
            "互殴是指双方都有加害对方的意图，互相打斗。\n"
            "互殴双方都不成立正当防卫！因为双方都没有防卫意图，只有伤害故意。\n"
            "例外：互殴中一方明确停止而另一方继续攻击的，停止方可以成立正当防卫。"
        ),
        "keywords": ["互殴", "互相打", "斗殴", "打架", "双方"],
    },
    "挑拨防卫": {
        "answer": (
            "挑拨防卫是指故意用言语或行为挑逗、激怒对方，让对方先动手，"
            "然后以'防卫'为名进行反击。\n"
            "挑拨防卫不构成正当防卫！因为你主观上没有防卫意图，目的是加害对方。\n"
            "这是滥用防卫权的行为，要承担故意犯罪的刑事责任。"
        ),
        "keywords": ["挑拨", "挑逗", "激怒", "故意引发"],
    },
}


def _match_offline_faq(message: str) -> str | None:
    """匹配离线 FAQ，返回最佳答案或 None"""
    best, best_score = None, 0
    for item in OFFLINE_FAQ.values():
        score = sum(1 for kw in item["keywords"] if kw in message)
        if score > best_score:
            best_score = score
            best = item["answer"]
    return best if best_score >= 1 else None


# ── 字幕工具 ────────────────────────────────────────────────

def load_scored_videos() -> list[dict]:
    if not SCORED_VIDEOS.exists():
        return []
    with open(SCORED_VIDEOS, encoding="utf-8") as f:
        return json.load(f)


def load_subtitles(bvid: str) -> list[dict]:
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


def match_bilibili_video(title: str) -> dict | None:
    """用标题关键词匹配 B 站已下载字幕库里最相关的视频"""
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


def get_context_subtitles(bvid: str, current_sec: int, window: int = 30) -> list[dict]:
    """返回当前时间戳前后 window 秒的字幕句子"""
    subs = load_subtitles(bvid)
    if not subs:
        return []
    lo, hi = current_sec - window, current_sec + window
    return [s for s in subs if lo <= s.get("start", 0) <= hi]


def search_subtitles(bvid: str, query: str, top_k: int = 3) -> list[dict]:
    """在字幕中搜索与 query 最相关的片段（离线回退用）"""
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


# ── LLM 调用 ────────────────────────────────────────────────

async def call_llm(system: str, user: str) -> str | None:
    """
    调用可用的 LLM。优先 Kimi，其次 DeepSeek。
    返回 None 表示全部不可用（触发离线回退）。
    """
    kimi_key = MOONSHOT_API_KEY
    if kimi_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20) as client:
                res = await client.post(
                    "https://api.moonshot.cn/v1/chat/completions",
                    headers={"Authorization": f"Bearer {kimi_key}"},
                    json={
                        "model": "moonshot-v1-8k",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "max_tokens": 600,
                    },
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    ds_key = DEEPSEEK_API_KEY
    if ds_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20) as client:
                res = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {ds_key}"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "max_tokens": 600,
                    },
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    return None  # 全部不可用


# ── 端点 ────────────────────────────────────────────────────

@router.get("/health")
async def health() -> dict[str, Any]:
    """连通性检查（Extension 可用此端点判断后端是否在线）"""
    llm_available = bool(MOONSHOT_API_KEY or DEEPSEEK_API_KEY)
    subtitle_count = len(list(SUBTITLE_DIR.glob("*.json"))) if SUBTITLE_DIR.exists() else 0
    return {
        "status": "ok",
        "llm_available": llm_available,
        "subtitle_files": subtitle_count,
        "cached_videos": len(_video_cache),
    }


@router.post("/register_video")
async def register_video(req: RegisterVideoRequest) -> dict[str, Any]:
    """
    注册视频：
    - 抖音视频：用标题匹配 B 站字幕库
    - B站视频：直接检查字幕是否存在
    """
    ckey = f"{req.platform}:{req.video_id}"
    if ckey in _video_cache:
        return _video_cache[ckey]

    result: dict[str, Any] = {
        "video_id": req.video_id,
        "platform": req.platform,
        "title": req.title,
        "matched_bilibili": None,
        "subtitle_count": 0,
    }

    if req.platform == "douyin":
        match = match_bilibili_video(req.title)
        if match:
            subs = load_subtitles(match["bvid"])
            result["matched_bilibili"] = {
                "bvid": match["bvid"],
                "title": match.get("title", ""),
                "subtitle_count": len(subs),
            }
            result["subtitle_count"] = len(subs)
    elif req.platform == "bilibili":
        subs = load_subtitles(req.video_id)
        result["subtitle_count"] = len(subs)

    _video_cache[ckey] = result
    return result


@router.post("/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    """
    视频问答：根据当前时间戳，截取字幕上下文，调用 LLM 作答。

    三层回退策略：
    1. LLM（Kimi → DeepSeek）— 最佳
    2. 字幕搜索 — LLM 不可用时搜索相关字幕片段作为回答依据
    3. 离线 FAQ — 匹配预设知识库
    """
    # 确定 bvid
    if req.platform == "douyin":
        ckey = f"douyin:{req.video_id}"
        cached = _video_cache.get(ckey, {})
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

    llm_answer = await call_llm(system, req.message)

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
    faq_answer = _match_offline_faq(req.message)
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

"""
妙喵私教 — 法学案例判卷 API
POST /api/lesson/load         加载 Lesson 数据
POST /api/lesson/quiz_submit   提交作答，返回评分 + 纠错 + 跳转时间戳
GET  /api/lesson/state         获取当前学习状态
POST /api/lesson/next_step     标记步骤完成/推进

业务逻辑委托给 ewa.lesson 模块。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ewa.config import LESSONS_DIR
from ewa.extension.scoring import score_answer_with_llm
from ewa.extension.store import LessonStore, get_session, persist_session
from ewa.extension.feedback import build_cat_message, calc_cat_state

router = APIRouter(prefix="/api/lesson", tags=["lesson"])


# ── 课程数据加载（数据访问属路由层职责） ───────────────────────

def load_lesson(lesson_id: str) -> dict | None:
    """根据 lesson_id 加载课程 JSON 数据。"""
    path = LESSONS_DIR / f"{lesson_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_lesson_by_video(video_id: str) -> dict | None:
    """根据 video_id 匹配课程。"""
    for path in LESSONS_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("video_id") == video_id or data.get("douyin_video_id") == video_id:
                return data
        except Exception:
            pass
    return None


# ── 请求/响应模型 ────────────────────────────────────────────

class LessonRequest(BaseModel):
    video_id: str
    platform: str = "bilibili"


class QuizSubmitRequest(BaseModel):
    session_id: str
    lesson_id: str
    step_id: str
    answer: str
    current_time_sec: int = 0


class StepCompleteRequest(BaseModel):
    session_id: str
    lesson_id: str
    step_id: str


# ── 端点 ────────────────────────────────────────────────────

@router.post("/load")
async def load_lesson_api(req: LessonRequest) -> dict[str, Any]:
    """根据视频 ID（或其他索引键）加载对应的 Lesson。"""
    lesson = find_lesson_by_video(req.video_id)
    if not lesson:
        return {"error": "no lesson found", "steps": [], "hint": "此视频尚未收录课程，请确认 video_id 是否正确或联系博主创建课程"}

    safe_steps = []
    for step in lesson.get("steps", []):
        safe_steps.append({
            "id": step["id"],
            "title": step["title"],
            "start_ms": step["start_ms"],
            "end_ms": step["end_ms"],
            "instruction": step["instruction"],
            "key_point": step["key_point"],
            "common_errors": step["common_errors"],
            "question": step.get("quiz", {}).get("question", ""),
            "hint_seek_ms": step.get("quiz", {}).get("hint_seek_ms"),
            "pass_threshold": step.get("pass_threshold", 0.75),
        })

    return {
        "lesson_id": lesson["id"],
        "title": lesson["title"],
        "video_id": lesson["video_id"],
        "creator_name": lesson.get("creator_name", ""),
        "total_steps": len(safe_steps),
        "steps": safe_steps,
        "gamification": lesson.get("gamification", {}),
    }


@router.post("/quiz_submit")
async def quiz_submit(req: QuizSubmitRequest) -> dict[str, Any]:
    """
    提交作答，返回：
    - passed: 是否通过
    - score: 0-1
    - cat_message: 妙喵反馈（含具体错误）
    - seek_to_ms: 建议回退的时间点
    - missed_points: 漏答的要点
    - stars_earned: 本题得星
    - llm_used: 是否使用了 LLM 语义判断
    """
    lesson = load_lesson(req.lesson_id)
    if not lesson:
        return {"error": "lesson not found"}

    step = next((s for s in lesson["steps"] if s["id"] == req.step_id), None)
    if not step:
        return {"error": "step not found"}

    quiz = step.get("quiz", {})
    answer_key = quiz.get("answer_key", [])
    wrong_key = quiz.get("wrong_key", [])
    min_correct = quiz.get("min_correct", 2)
    hint_seek_ms = quiz.get("hint_seek_ms")
    question = quiz.get("question", "")

    # ── 混合评分（关键词 + LLM 回退） ──────────────────────
    result = await score_answer_with_llm(
        answer=req.answer,
        answer_key=answer_key,
        wrong_key=wrong_key,
        min_correct=min_correct,
        question=question,
        key_point=step.get("key_point", ""),
        domain=lesson.get("domain", "通用"),
    )

    passed = len(result["matched"]) >= min_correct and len(result["wrong_hits"]) == 0

    # ── 更新 session ───────────────────────────────────────
    session = get_session(req.session_id, req.lesson_id, lesson.get("video_id", ""))
    attempt_num = (
        session["step_results"].get(req.step_id, {}).get("attempts", 0) + 1
    )
    session["step_results"][req.step_id] = {
        "attempts": attempt_num,
        "passed": passed,
        "last_score": result["score"],
        "matched_count": len(result["matched"]),
    }

    if passed:
        gamification = lesson.get("gamification", {})
        stars = min(3, 4 - attempt_num)
        fish = gamification.get("fish_reward_per_step", 3)
        growth = gamification.get("growth_per_pass", 10)
        session["total_stars"] += stars
        session["fish"] += fish
        session["growth"] += growth
    else:
        if req.step_id not in session["review_queue"]:
            session["review_queue"].append(req.step_id)

    # 持久化
    persist_session(session)
    LessonStore.save_attempt(
        session_id=req.session_id,
        step_id=req.step_id,
        attempt_num=attempt_num,
        answer=req.answer,
        score=result["score"],
        matched_count=len(result["matched"]),
        required_count=min_correct,
        passed=passed,
        stars_earned=(min(3, 4 - attempt_num) if passed else 0),
        cat_message="",
        missed_points=result["missed"],
        wrong_points=result["wrong_hits"],
    )

    # ── 生成妙喵反馈 ───────────────────────────────────────
    cat_message = build_cat_message(
        passed=passed,
        matched=result["matched"],
        missed=result["missed"],
        wrong_hits=result["wrong_hits"],
        attempt_num=attempt_num,
        step_title=step["title"],
        key_point=step["key_point"],
    )
    if result.get("llm_comment"):
        cat_message += f"\n\n🤖 猫猫深度分析：{result['llm_comment']}"

    # ── 找下一步 ───────────────────────────────────────────
    steps = lesson["steps"]
    current_idx = next(
        (i for i, s in enumerate(steps) if s["id"] == req.step_id), -1
    )
    next_step_data = None
    if passed and current_idx >= 0 and current_idx + 1 < len(steps):
        session["current_step_index"] = current_idx + 1
        persist_session(session)
        ns = steps[current_idx + 1]
        next_step_data = {
            "id": ns["id"],
            "title": ns["title"],
            "start_ms": ns["start_ms"],
            "end_ms": ns["end_ms"],
            "instruction": ns["instruction"],
            "question": ns.get("quiz", {}).get("question", ""),
            "hint_seek_ms": ns.get("quiz", {}).get("hint_seek_ms"),
        }

    return {
        "passed": passed,
        "score": result["score"],
        "matched_count": len(result["matched"]),
        "required_count": min_correct,
        "cat_message": cat_message,
        "seek_to_ms": hint_seek_ms if not passed else None,
        "missed_points": result["missed"] if not passed else [],
        "wrong_points": result["wrong_hits"],
        "stars_earned": (min(3, 4 - attempt_num) if passed else 0),
        "attempt_num": attempt_num,
        "llm_used": result.get("llm_used", False),
        "next_step": next_step_data,
        "session_summary": {
            "total_stars": session["total_stars"],
            "fish": session["fish"],
            "growth": session["growth"],
            "review_queue_len": len(session["review_queue"]),
        },
    }


@router.get("/state/{session_id}/{lesson_id}")
async def get_state(session_id: str, lesson_id: str) -> dict[str, Any]:
    """获取当前学习状态（优先 SQLite）。"""
    session = get_session(session_id, lesson_id)
    lesson = load_lesson(lesson_id)
    if not lesson:
        return {"error": "lesson not found"}

    steps = lesson.get("steps", [])
    current_idx = session["current_step_index"]
    current_step = steps[current_idx] if current_idx < len(steps) else None

    return {
        "current_step_index": current_idx,
        "total_steps": len(steps),
        "current_step": {
            "id": current_step["id"],
            "title": current_step["title"],
            "start_ms": current_step["start_ms"],
            "question": current_step.get("quiz", {}).get("question", ""),
        }
        if current_step
        else None,
        "completed_steps": [
            sid for sid, r in session["step_results"].items() if r.get("passed")
        ],
        "review_queue": session["review_queue"],
        "gamification": {
            "total_stars": session["total_stars"],
            "fish": session["fish"],
            "growth": session["growth"],
        },
        "cat_state": calc_cat_state(session, current_idx, len(steps)),
        "persisted": LessonStore.load_session(session_id) is not None,
    }


@router.post("/next_step")
async def next_step(req: StepCompleteRequest) -> dict[str, Any]:
    """推进到下一步。"""
    session = get_session(req.session_id, req.lesson_id)
    lesson = load_lesson(req.lesson_id)
    if not lesson:
        return {"error": "lesson not found"}

    steps = lesson["steps"]
    idx = session["current_step_index"]

    if idx < len(steps) - 1:
        session["current_step_index"] += 1
        persist_session(session)
        next_s = steps[session["current_step_index"]]
        return {
            "status": "advanced",
            "next_step": {
                "id": next_s["id"],
                "title": next_s["title"],
                "start_ms": next_s["start_ms"],
                "end_ms": next_s["end_ms"],
                "instruction": next_s["instruction"],
                "question": next_s.get("quiz", {}).get("question", ""),
            },
        }
    else:
        return {
            "status": "lesson_complete",
            "message": "你已经完成了本节课所有内容！",
            "summary": {
                "total_stars": session["total_stars"],
                "fish": session["fish"],
                "growth": session["growth"],
                "review_queue": session["review_queue"],
            },
        }

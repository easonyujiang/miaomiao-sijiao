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
from ewa.llm import LLMClient
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
        is_non_answer=result.get("is_non_answer", False),
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


# ── 学习分析报告 ─────────────────────────────────────────────

async def _build_lesson_report(session_id: str, lesson_id: str) -> dict[str, Any]:
    """汇总 session 和 attempts，生成结构化学习报告。"""
    session = get_session(session_id, lesson_id)
    lesson = load_lesson(lesson_id)
    attempts = LessonStore.load_attempts(session_id)

    if not lesson:
        return {"error": "lesson not found"}

    steps = lesson.get("steps", [])
    step_map = {s["id"]: s for s in steps}
    step_results = session.get("step_results", {})

    total_steps = len(steps)
    completed_steps = [sid for sid, info in step_results.items() if info.get("passed")]
    completion_rate = round(len(completed_steps) / max(total_steps, 1), 2)

    # 按 step 聚合 attempts（如 attempts 表未持久化，会用 session step_results 兜底）
    per_step: dict[str, dict] = {}
    for a in attempts:
        sid = a["step_id"]
        per_step.setdefault(sid, {"attempts": 0, "passed": False, "scores": [], "wrong": set(), "missed": set()})
        per_step[sid]["attempts"] += 1
        per_step[sid]["scores"].append(a["score"])
        if a["passed"]:
            per_step[sid]["passed"] = True
        per_step[sid]["wrong"].update(a.get("wrong_points", []))
        per_step[sid]["missed"].update(a.get("missed_points", []))

    # 如果 attempts 表没数据，用 session step_results 补齐 attempts 计数
    for sid, info in step_results.items():
        if sid not in per_step:
            per_step[sid] = {
                "attempts": info.get("attempts", 0),
                "passed": info.get("passed", False),
                "scores": [info.get("last_score", 0)] if info.get("last_score") else [],
                "wrong": set(),
                "missed": set(),
            }
        else:
            per_step[sid]["attempts"] = max(per_step[sid]["attempts"], info.get("attempts", 0))
            per_step[sid]["passed"] = per_step[sid]["passed"] or info.get("passed", False)

    # 薄弱知识点：未通过 或 尝试次数 > 1 的步骤
    weak_steps = []
    for sid, info in per_step.items():
        step = step_map.get(sid, {})
        if not info["passed"] or info["attempts"] > 1:
            weak_steps.append({
                "step_id": sid,
                "title": step.get("title", ""),
                "start_ms": step.get("start_ms", 0),
                "key_point": step.get("key_point", ""),
                "attempts": info["attempts"],
                "passed": info["passed"],
                "wrong_points": list(info["wrong"]) or step.get("common_errors", [])[:2],
                "missed_points": list(info["missed"]) or [step.get("key_point", "")[:80]] if step.get("key_point") else [],
            })

    # 推荐回看：取薄弱步骤的 start_ms（前 3 个）
    review_recommendations = [
        {"step_id": ws["step_id"], "title": ws["title"], "seek_ms": ws["start_ms"]}
        for ws in sorted(weak_steps, key=lambda x: (not x["passed"], x["attempts"]), reverse=True)[:3]
    ]

    base_report = {
        "completed": len(completed_steps) >= total_steps and total_steps > 0,
        "completion_rate": completion_rate,
        "total_steps": total_steps,
        "completed_steps": completed_steps,
        "total_stars": session["total_stars"],
        "fish": session["fish"],
        "growth": session["growth"],
        "weak_points": [
            {"step_id": ws["step_id"], "title": ws["title"], "points": ws["wrong_points"] + ws["missed_points"]}
            for ws in weak_steps
        ],
        "review_recommendations": review_recommendations,
    }

    # LLM 生成个性化指导
    llm_guidance = await _generate_llm_guidance(lesson, session, attempts, weak_steps)
    base_report["llm_guidance"] = llm_guidance

    # 组装对话式报告文本
    report_text = _format_report_text(base_report, lesson)
    base_report["report_text"] = report_text

    return base_report


async def _generate_llm_guidance(lesson: dict, session: dict, attempts: list[dict], weak_steps: list[dict]) -> str:
    """用 LLM 生成鼓励 + 薄弱点 + 复习建议。"""
    client = LLMClient()
    if not client.is_available or not attempts:
        return "继续加油，记得回看薄弱知识点喵~"

    total_steps = len(lesson.get("steps", []))
    completed = sum(1 for a in attempts if a["passed"])

    weak_lines = []
    for ws in weak_steps[:3]:
        points = "、".join(ws["wrong_points"] + ws["missed_points"]) or ws["key_point"][:60]
        weak_lines.append(f"- {ws['title']}（尝试 {ws['attempts']} 次）：{points}")

    weak_text = "\n".join(weak_lines) if weak_lines else "暂无明显薄弱点"

    system = """你是妙喵，一位亲切、有博主个人色彩的 AI 私教。请根据学生的课程表现，用鼓励的语气写一段学习总结。

要求：
- 简短、口语化、有温度（150 字以内）
- 先肯定进步，再指出最需要补的 1-2 个薄弱点
- 给出具体可执行的复习建议（建议回跳哪个时间片段）
- 不要罗列所有数据，只抓重点"""

    user = f"""课程：{lesson.get('title', '')}
完成情况：完成 {completed}/{total_steps} 关
总星数：{session['total_stars']} · 小鱼干：{session['fish']} · 成长值：{session['growth']}

薄弱点：
{weak_text}

请写一段学习总结。"""

    return await client.chat(system, user, max_tokens=250, temperature=0.7) or "继续加油，记得回看薄弱知识点喵~"


def _format_report_text(report: dict, lesson: dict) -> str:
    """把结构化报告格式化成对话式文本。"""
    lines = ["🎉 全部通关！" if report["completed"] else "📝 学习小结"]
    lines.append(f"⭐ 总星数：{report['total_stars']}")
    lines.append(f"🐟 小鱼干：{report['fish']}")
    lines.append(f"🌱 成长值：+{report['growth']}")
    lines.append(f"📊 完成度：{int(report['completion_rate'] * 100)}% ({report['completed_steps'].__len__()}/{report['total_steps']})")

    if report["weak_points"]:
        weak_titles = "、".join(w["title"] for w in report["weak_points"][:3])
        lines.append(f"\n📌 薄弱点：{weak_titles}")

    if report["llm_guidance"]:
        lines.append(f"\n💡 妙喵建议：\n{report['llm_guidance']}")

    if report["review_recommendations"]:
        lines.append("\n⏪ 推荐回看：")
        for rec in report["review_recommendations"]:
            sec = rec["seek_ms"] // 1000
            lines.append(f"- {rec['title']}：{sec // 60:02d}:{sec % 60:02d}")

    return "\n".join(lines)


@router.get("/report/{session_id}/{lesson_id}")
async def get_lesson_report(session_id: str, lesson_id: str) -> dict[str, Any]:
    """获取课程学习分析报告（完成课程后自动触发）。"""
    report = await _build_lesson_report(session_id, lesson_id)
    if report.get("error"):
        return report
    return report

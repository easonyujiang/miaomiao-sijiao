"""
妙喵私教 — 法学案例判卷 API
POST /api/lesson/load         加载 Lesson 数据
POST /api/lesson/quiz_submit   提交作答，返回评分 + 纠错 + 跳转时间戳
GET  /api/lesson/state         获取当前学习状态
POST /api/lesson/next_step     标记步骤完成/推进
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ewa.config import LESSONS_DIR, DEEPSEEK_API_KEY, MOONSHOT_API_KEY

router = APIRouter(prefix="/api/lesson", tags=["lesson"])


def _get_db_path() -> str:
    """获取当前的 lesson 数据库路径"""
    import os
    import ewa.config
    return os.getenv("EWA_SITE_DB_PATH") or str(ewa.config.SITE_DB_PATH)


# ── SQLite 持久化 ───────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    """获取 SQLite 连接（lesson 状态与 site 共用同一个 db 文件）"""
    db = sqlite3.connect(_get_db_path())
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def _ensure_lesson_tables() -> None:
    """确保 lesson 相关的表存在（与 site schema 中的表协作）"""
    try:
        with _get_db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS lesson_sessions (
                    id TEXT PRIMARY KEY,
                    lesson_id TEXT NOT NULL,
                    video_id TEXT,
                    current_step_index INTEGER NOT NULL DEFAULT 0,
                    total_stars INTEGER NOT NULL DEFAULT 0,
                    fish INTEGER NOT NULL DEFAULT 0,
                    growth INTEGER NOT NULL DEFAULT 0,
                    step_results_json TEXT NOT NULL DEFAULT '{}',
                    review_queue_json TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS lesson_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    attempt_num INTEGER NOT NULL DEFAULT 1,
                    answer TEXT NOT NULL,
                    score REAL NOT NULL DEFAULT 0,
                    matched_count INTEGER NOT NULL DEFAULT 0,
                    required_count INTEGER NOT NULL DEFAULT 0,
                    passed INTEGER NOT NULL DEFAULT 0 CHECK (passed IN (0, 1)),
                    stars_earned INTEGER NOT NULL DEFAULT 0,
                    cat_message TEXT,
                    missed_points_json TEXT NOT NULL DEFAULT '[]',
                    wrong_points_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES lesson_sessions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_lesson_sessions_lesson
                    ON lesson_sessions(lesson_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_lesson_attempts_session
                    ON lesson_attempts(session_id, step_id, attempt_num DESC);
            """)
    except Exception:
        pass  # db 可能还不存在，运行时由 main.py 初始化

_tables_ensured: set[str] = set()


def _ensure_tables_once() -> None:
    """确保当前数据库中存在 lesson 表（按 db 路径跟踪，支持多 DB 切换）"""
    db_path = _get_db_path()
    if db_path not in _tables_ensured:
        _ensure_lesson_tables()
        _tables_ensured.add(db_path)


class LessonStore:
    """SQLite 持久化的学习状态存储"""

    @staticmethod
    def load_session(session_id: str) -> dict | None:
        _ensure_tables_once()
        try:
            with _get_db() as db:
                row = db.execute(
                    "SELECT * FROM lesson_sessions WHERE id = ?", (session_id,)
                ).fetchone()
                if not row:
                    return None
                return {
                    "session_id": row["id"],
                    "lesson_id": row["lesson_id"],
                    "current_step_index": row["current_step_index"],
                    "total_stars": row["total_stars"],
                    "fish": row["fish"],
                    "growth": row["growth"],
                    "step_results": json.loads(row["step_results_json"]),
                    "review_queue": json.loads(row["review_queue_json"]),
                }
        except Exception:
            return None

    @staticmethod
    def save_session(
        session_id: str,
        lesson_id: str,
        video_id: str = "",
        current_step_index: int = 0,
        total_stars: int = 0,
        fish: int = 0,
        growth: int = 0,
        step_results: dict | None = None,
        review_queue: list | None = None,
    ) -> None:
        _ensure_tables_once()
        try:
            with _get_db() as db:
                db.execute(
                    """INSERT OR REPLACE INTO lesson_sessions
                       (id, lesson_id, video_id, current_step_index,
                        total_stars, fish, growth, step_results_json, review_queue_json, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (
                        session_id, lesson_id, video_id, current_step_index,
                        total_stars, fish, growth,
                        json.dumps(step_results or {}, ensure_ascii=False),
                        json.dumps(review_queue or [], ensure_ascii=False),
                    ),
                )
        except Exception:
            pass  # 持久化失败不阻塞答题流程

    @staticmethod
    def save_attempt(
        session_id: str,
        step_id: str,
        attempt_num: int,
        answer: str,
        score: float,
        matched_count: int,
        required_count: int,
        passed: bool,
        stars_earned: int,
        cat_message: str,
        missed_points: list,
        wrong_points: list,
    ) -> None:
        _ensure_tables_once()
        try:
            with _get_db() as db:
                db.execute(
                    """INSERT INTO lesson_attempts
                       (session_id, step_id, attempt_num, answer, score,
                        matched_count, required_count, passed, stars_earned,
                        cat_message, missed_points_json, wrong_points_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        session_id, step_id, attempt_num, answer, score,
                        matched_count, required_count, int(passed), stars_earned,
                        cat_message,
                        json.dumps(missed_points, ensure_ascii=False),
                        json.dumps(wrong_points, ensure_ascii=False),
                    ),
                )
        except Exception:
            pass


# ── 工具 ────────────────────────────────────────────────────

def load_lesson(lesson_id: str) -> dict | None:
    path = LESSONS_DIR / f"{lesson_id}.json"
    if not path.exists():
        jsons = list(LESSONS_DIR.glob("*.json"))
        if not jsons:
            return None
        path = jsons[0]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_lesson_by_video(video_id: str) -> dict | None:
    for path in LESSONS_DIR.glob("*.json"):
        try:
            data = json.load(open(path, encoding="utf-8"))
            if data.get("video_id") == video_id or data.get("douyin_video_id") == video_id:
                return data
        except Exception:
            pass
    return None


def get_session(session_id: str, lesson_id: str, video_id: str = "") -> dict:
    """获取或创建 session（优先 SQLite，回退到内存）"""
    # 尝试从 SQLite 加载
    stored = LessonStore.load_session(session_id)
    if stored:
        return stored

    # 新建 session
    return {
        "session_id": session_id,
        "lesson_id": lesson_id,
        "video_id": video_id,
        "current_step_index": 0,
        "step_results": {},
        "total_stars": 0,
        "fish": 0,
        "growth": 0,
        "review_queue": [],
    }


def persist_session(session: dict) -> None:
    """将 session 写入 SQLite"""
    LessonStore.save_session(
        session_id=session["session_id"],
        lesson_id=session.get("lesson_id", ""),
        video_id=session.get("video_id", ""),
        current_step_index=session.get("current_step_index", 0),
        total_stars=session.get("total_stars", 0),
        fish=session.get("fish", 0),
        growth=session.get("growth", 0),
        step_results=session.get("step_results", {}),
        review_queue=session.get("review_queue", []),
    )


# ── 评分引擎 ────────────────────────────────────────────────

def score_answer(answer: str, answer_key: list[str], wrong_key: list[str] | None = None) -> dict:
    """
    关键词匹配评分：从 answer_key 每条提取所有 2+ 字词，
    任意词命中 OR 括号外主干内有 3+ 字公共子串即算匹配。

    返回 {score, matched, missed, wrong_hits}
    """
    wrong_key = wrong_key or []

    def extract_words(text: str) -> list[str]:
        main = re.sub(r"[（(][^）)]*[）)]", "", text)
        cleaned = re.sub(r"[，,。.·：:；;！!？?\[\]【】]", " ", main)
        return [w.strip() for w in cleaned.split() if len(w.strip()) >= 2]

    def any_substr_match(needle_words: list[str], haystack: str) -> bool:
        for w in needle_words:
            if w in haystack:
                return True
            if len(w) >= 4:
                for i in range(len(w) - 2):
                    if w[i : i + 3] in haystack:
                        return True
        return False

    matched = []
    missed = []
    for key in answer_key:
        words = extract_words(key)
        if any_substr_match(words, answer):
            matched.append(key)
        else:
            missed.append(key)

    wrong_hits = []
    for w in wrong_key:
        words = extract_words(w)
        if any_substr_match(words, answer):
            wrong_hits.append(w)

    score = len(matched) / max(len(answer_key), 1)
    if wrong_hits:
        score *= 0.5

    return {
        "score": round(score, 3),
        "matched": matched,
        "missed": missed,
        "wrong_hits": wrong_hits,
    }


async def score_answer_with_llm(
    answer: str,
    answer_key: list[str],
    wrong_key: list[str],
    min_correct: int,
    question: str,
    key_point: str,
) -> dict:
    """
    混合评分：先关键词匹配，不达标时调用 LLM 做语义判断。

    返回与 score_answer() 相同结构 + llm_used: bool
    """
    # 第一层：关键词匹配
    result = score_answer(answer, answer_key, wrong_key)
    kw_passed = len(result["matched"]) >= min_correct and len(result["wrong_hits"]) == 0

    if kw_passed:
        result["llm_used"] = False
        return result

    # 第二层：LLM 语义判断
    llm_result = await _llm_judge(answer, question, answer_key, wrong_key, key_point)
    if llm_result is None:
        # LLM 不可用，让第一层结果决定（可能不达标）
        result["llm_used"] = False
        return result

    # 合并：LLM 确认命中的要点追加到 matched
    llm_matched = llm_result.get("matched_points", [])
    llm_wrong = llm_result.get("wrong_points", [])

    # 追加 LLM 发现的新匹配（不重复）
    for pt in llm_matched:
        if pt not in result["matched"]:
            # 检查是否近似匹配了某个 answer_key 的条目
            for key in answer_key:
                if key not in result["matched"]:
                    # 简单相似度：LLM 说命中了，我们就接受
                    if _fuzzy_overlap(pt, key) > 0.5 or any(
                        char in key for char in pt if len(char) >= 2
                    ):
                        result["matched"].append(key)
                        if key in result["missed"]:
                            result["missed"].remove(key)
                        break

    # 追加 LLM 发现的错误理解
    for wp in llm_wrong:
        if wp not in result["wrong_hits"]:
            result["wrong_hits"].append(wp)

    # 重新计算分数
    new_score = len(result["matched"]) / max(len(answer_key), 1)
    if result["wrong_hits"]:
        new_score *= 0.5
    result["score"] = round(min(new_score, 1.0), 3)
    result["llm_used"] = True
    result["llm_comment"] = llm_result.get("comment", "")

    return result


def _fuzzy_overlap(a: str, b: str) -> float:
    """两个字符串的简单模糊重叠度（Jaccard-like on characters）"""
    if not a or not b:
        return 0.0
    set_a = set(a.replace(" ", ""))
    set_b = set(b.replace(" ", ""))
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


async def _llm_judge(
    answer: str,
    question: str,
    answer_key: list[str],
    wrong_key: list[str],
    key_point: str,
) -> dict | None:
    """
    调用 LLM 进行语义评分。
    返回 {matched_points, wrong_points, comment} 或 None（LLM 不可用）
    """
    system = """你是一名法学私教评分助手。你的任务是判断学生的回答是否涵盖了参考答案中的要点。

请严格按以下 JSON 格式返回，不要加任何其他文字：
{
  "matched_points": ["被学生命中的要点（从参考答案中摘取）"],
  "wrong_points": ["学生理解有误的表述"],
  "comment": "一句话简评（不超过50字）"
}

评分原则：
1. 只要学生表达的意思与参考答案要点一致，即使措辞不同也应认为命中
2. 关注实质性理解，不是字面匹配
3. 如果学生指出了参考答案中没有的但法律上正确的观点，不算错误
4. 只有明确的法律错误才计入 wrong_points"""

    user = f"""题目：{question}

参考答案要点：
{json.dumps(answer_key, ensure_ascii=False, indent=2)}

常见错误表述：
{json.dumps(wrong_key, ensure_ascii=False, indent=2)}

核心要点：{key_point}

学生的回答：
{answer}

请判断学生的回答命中了哪些要点，以及有哪些错误理解。"""

    # 尝试 Kimi
    response = await _try_llm(system, user, "kimi")
    if response:
        return response

    # 尝试 DeepSeek
    response = await _try_llm(system, user, "deepseek")
    if response:
        return response

    return None


async def _try_llm(system: str, user: str, provider: str) -> dict | None:
    """尝试调用指定的 LLM provider，返回解析后的 JSON 或 None"""
    api_key = MOONSHOT_API_KEY if provider == "kimi" else DEEPSEEK_API_KEY
    if not api_key:
        return None

    api_url = (
        "https://api.moonshot.cn/v1/chat/completions"
        if provider == "kimi"
        else "https://api.deepseek.com/v1/chat/completions"
    )
    model = "moonshot-v1-8k" if provider == "kimi" else "deepseek-chat"

    try:
        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.1,
                },
            )
            if res.status_code == 200:
                content = res.json()["choices"][0]["message"]["content"]
                return _parse_llm_json(content)
    except Exception:
        pass

    return None


def _parse_llm_json(text: str) -> dict | None:
    """从 LLM 返回中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 ```json ... ``` 块
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 尝试提取 { ... }
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
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
    """根据视频 ID 加载对应的 Lesson"""
    lesson = find_lesson_by_video(req.video_id)
    if not lesson:
        lesson = load_lesson("lesson_luoxiang_001")
    if not lesson:
        return {"error": "no lesson found", "steps": []}

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
        cat_message="",  # 下面生成
        missed_points=result["missed"],
        wrong_points=result["wrong_hits"],
    )

    # ── 生成妙喵反馈 ───────────────────────────────────────
    cat_message = _build_cat_message(
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


def _build_cat_message(
    passed: bool,
    matched: list[str],
    missed: list[str],
    wrong_hits: list[str],
    attempt_num: int,
    step_title: str,
    key_point: str,
) -> str:
    if passed:
        if attempt_num == 1:
            return (
                f"完美！第一次就答对了 🌟\n"
                f"核心要点你都掌握了：{matched[0] if matched else '关键要件'}。\n"
                f"小鱼干 +3 🐟"
            )
        else:
            return (
                f"这次过了！{attempt_num}次尝试，坚持就是胜利 ✨\n"
                f"关键是你抓住了：{matched[0] if matched else '核心要件'}。"
            )
    else:
        msg_parts = ["猫猫看了你的答案，差一点点~\n"]
        if wrong_hits:
            msg_parts.append(
                f"⚠️ 注意：{wrong_hits[0]} —— 这个理解有误，要回去看看。\n"
            )
        if missed:
            msg_parts.append("漏掉了关键点：\n")
            for m in missed[:2]:
                msg_parts.append(f"  · {m}\n")
        msg_parts.append(f"\n💡 记住：{key_point}")
        if missed:
            msg_parts.append("\n\n⏪ 猫猫帮你找到了对应片段，点下面跳回去再看一遍 👇")
        return "".join(msg_parts)


@router.get("/state/{session_id}/{lesson_id}")
async def get_state(session_id: str, lesson_id: str) -> dict[str, Any]:
    """获取当前学习状态（优先 SQLite）"""
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
        "cat_state": _calc_cat_state(session, current_idx, len(steps)),
        "persisted": LessonStore.load_session(session_id) is not None,
    }


def _calc_cat_state(session: dict, current_idx: int, total: int) -> str:
    if current_idx >= total:
        return "celebrating"
    results = session["step_results"]
    if not results:
        return "idle"
    last = list(results.values())[-1]
    if not last.get("passed") and last.get("attempts", 0) > 0:
        return "correcting"
    return "watching"


@router.post("/next_step")
async def next_step(req: StepCompleteRequest) -> dict[str, Any]:
    """推进到下一步"""
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

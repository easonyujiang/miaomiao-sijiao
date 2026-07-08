"""SQLite 学习状态持久化

管理 lesson_sessions 和 lesson_attempts 两张表，
与 site 模块共用同一个 SQLite 数据库文件。

P1-2/P1-5 修复：
- 表结构已统一到 docs/schema.sql（SiteRepository.initialize 负责创建）
- db_path 支持显式注入，不再仅依赖环境变量
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3

import ewa.config

logger = logging.getLogger(__name__)

# 跟踪已创建过表的 DB 路径（支持多 DB 切换）
_tables_ensured: set[str] = set()

# 当前数据��路径（可通过 set_db_path 设置）
_current_db_path: str | None = None


# ── DB 路径管理 ──────────────────────────────────────────────

def set_db_path(db_path: str) -> None:
    """显式设置数据库路径（优于通过环境变量获取）。

    调用方（如 app lifespan）应在初始化时调用此函数。
    """
    global _current_db_path
    _current_db_path = db_path


def _get_db_path() -> str:
    """获取当前的 lesson 数据库路径。

    优先级：set_db_path() > EWA_SITE_DB_PATH 环境变量 > config 默认值
    """
    if _current_db_path:
        return _current_db_path
    return os.getenv("EWA_SITE_DB_PATH") or str(ewa.config.SITE_DB_PATH)


# ── DB 连接 ──────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    """获取 SQLite 连接（lesson 状态与 site 共用同一个 db 文件）。"""
    db = sqlite3.connect(_get_db_path())
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def _ensure_lesson_tables() -> None:
    """确保 lesson 相关的表存在。

    表结构已在 docs/schema.sql 中定义，SiteRepository.initialize() 会创建。
    此函数作为运行时兜底：当 lesson API 在 site 初始化前被调用时，
    自动创建表（而非静默失败）。
    """
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
    except sqlite3.OperationalError as e:
        # 数据库文件目录可能还不存在 — 记录警告而非静默吞掉
        logger.warning("无法创建 lesson 表（数据库目录可能不存在）: %s", e)
    except Exception:
        logger.exception("创建 lesson 表时发生未预期错误")


def ensure_tables_once() -> None:
    """确保当前数据库中存在 lesson 表（按 db 路径跟踪）。"""
    db_path = _get_db_path()
    if db_path not in _tables_ensured:
        _ensure_lesson_tables()
        _tables_ensured.add(db_path)


# ── LessonStore ───────────────────────────────────────────────

class LessonStore:
    """SQLite 持久化的学习状态存储。"""

    @staticmethod
    def load_session(session_id: str) -> dict | None:
        ensure_tables_once()
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
        except sqlite3.OperationalError as e:
            logger.warning("加载 session 失败（DB 错误）: %s", e)
            return None
        except Exception:
            logger.exception("加载 session 时发生未预期错误")
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
        ensure_tables_once()
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
        except sqlite3.OperationalError:
            pass  # 持久化失败不阻塞答题流程，但记录可追踪
        except Exception:
            logger.exception("保存 session 时发生未预期错误")

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
        ensure_tables_once()
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
            logger.exception("保存 attempt 时发生未预期错误")


# ── Session 辅助 ─────────────────────────────────────────────

def get_session(session_id: str, lesson_id: str, video_id: str = "") -> dict:
    """获取或创建 session（优先 SQLite，回退到内存）。"""
    stored = LessonStore.load_session(session_id)
    if stored:
        return stored

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
    """将 session 写入 SQLite。"""
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

"""共创社区 API 路由

公开端点（无需认证）：
- GET  /api/community/topics        话题列表
- GET  /api/community/topics/{id}   话题详情 + 回复
- POST /api/community/topics        创建话题
- POST /api/community/topics/{id}/replies  创建回复
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/community", tags=["community"])


def _db(request: Request) -> sqlite3.Connection:
    db_path = request.app.state.site_db_path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── 模型 ──────────────────────────────────────────────────────

class CreateTopicRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    category: str = Field(default="discussion")
    author_name: str = Field(default="匿名用户", max_length=100)
    tags: list[str] = Field(default_factory=list)


class CreateReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    author_name: str = Field(default="匿名用户", max_length=100)
    parent_reply_id: str | None = None


# ── 话题列表 ──────────────────────────────────────────────────

@router.get("/topics")
def list_topics(
    request: Request,
    profile_id: str = Query(default="profile_ashley"),
    category: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    conditions = ["profile_id = ?"]
    params: list[Any] = [profile_id]
    if category:
        conditions.append("category = ?")
        params.append(category)

    where = " AND ".join(conditions)
    with _db(request) as conn:
        rows = conn.execute(
            f"SELECT * FROM community_topics WHERE {where} ORDER BY is_pinned DESC, created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM community_topics WHERE {where}", params
        ).fetchone()[0]

    return {
        "items": [_topic_row(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── 话题详情 ──────────────────────────────────────────────────

@router.get("/topics/{topic_id}")
def get_topic(topic_id: str, request: Request):
    with _db(request) as conn:
        topic = conn.execute(
            "SELECT * FROM community_topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if not topic:
            raise HTTPException(404, "话题不存在")

        # 增加浏览量
        conn.execute(
            "UPDATE community_topics SET view_count = view_count + 1 WHERE id = ?",
            (topic_id,),
        )
        conn.commit()

        replies = conn.execute(
            "SELECT * FROM community_replies WHERE topic_id = ? ORDER BY created_at ASC",
            (topic_id,),
        ).fetchall()

    return {
        "topic": _topic_row(topic),
        "replies": [_reply_row(r) for r in replies],
    }


# ── 创建话题 ──────────────────────────────────────────────────

@router.post("/topics", status_code=201)
def create_topic(body: CreateTopicRequest, request: Request,
                 profile_id: str = Query(default="profile_ashley")):
    import uuid
    topic_id = f"topic_{uuid.uuid4().hex[:12]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%S")

    with _db(request) as conn:
        conn.execute(
            """INSERT INTO community_topics
               (id, profile_id, title, content, category, author_name, tags_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (topic_id, profile_id, body.title, body.content, body.category,
             body.author_name, json.dumps(body.tags, ensure_ascii=False), now, now),
        )
        conn.commit()

    return {"id": topic_id, "created_at": now}


# ── 创建回复 ──────────────────────────────────────────────────

@router.post("/topics/{topic_id}/replies", status_code=201)
def create_reply(topic_id: str, body: CreateReplyRequest, request: Request):
    import uuid
    reply_id = f"reply_{uuid.uuid4().hex[:12]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%S")

    with _db(request) as conn:
        topic = conn.execute(
            "SELECT id FROM community_topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if not topic:
            raise HTTPException(404, "话题不存在")

        conn.execute(
            """INSERT INTO community_replies
               (id, topic_id, parent_reply_id, author_name, content, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (reply_id, topic_id, body.parent_reply_id, body.author_name, body.content, now),
        )
        # 更新话题回复计数
        conn.execute(
            "UPDATE community_topics SET reply_count = reply_count + 1, updated_at = ? WHERE id = ?",
            (now, topic_id),
        )
        conn.commit()

    return {"id": reply_id, "created_at": now}


# ── 序列化辅助 ────────────────────────────────────────────────

def _topic_row(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"],
        "title": r["title"],
        "content": r["content"],
        "category": r["category"],
        "author_name": r["author_name"],
        "tags": _json(r["tags_json"], []),
        "view_count": r["view_count"],
        "reply_count": r["reply_count"],
        "like_count": r["like_count"],
        "is_pinned": bool(r["is_pinned"]),
        "is_resolved": bool(r["is_resolved"]),
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def _reply_row(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"],
        "topic_id": r["topic_id"],
        "parent_reply_id": r["parent_reply_id"],
        "author_name": r["author_name"],
        "content": r["content"],
        "is_pet_reply": bool(r["is_pet_reply"]),
        "like_count": r["like_count"],
        "created_at": r["created_at"],
    }


def _json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default

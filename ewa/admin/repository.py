"""管理后台通用 CRUD Repository

提供对 20 张表的统一增删改查接口，通过白名单防止 SQL 注入。
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ewa.core.logging import get_logger, log_admin_action

logger = get_logger(__name__)

# 可读写的表
READ_WRITE_TABLES: set[str] = {
    "profiles", "pet_personas", "projects", "faqs", "profile_links",
    "knowledge_sources", "videos", "video_segments", "diary_entries",
    "creator_style_examples", "content_chunks", "lesson_sessions",
}

# 仅可读的表
READ_ONLY_TABLES: set[str] = {
    "visitors", "visitor_sessions", "conversation_messages",
    "visitor_events", "lesson_attempts", "viewer_video_progress",
    "video_relations", "visitor_memories", "agent_actions",
}

ALLOWED_TABLES: set[str] = READ_WRITE_TABLES | READ_ONLY_TABLES

# 各表的搜索字段名（用于模糊搜索）
TABLE_SEARCH_FIELDS: dict[str, str] = {
    "profiles": "display_name",
    "pet_personas": "name",
    "projects": "name",
    "faqs": "question",
    "profile_links": "label",
    "knowledge_sources": "title",
    "videos": "title",
    "video_segments": "title",
    "diary_entries": "title",
    "creator_style_examples": "content",
    "content_chunks": "title",
    "lesson_sessions": "lesson_id",
    "lesson_attempts": "answer",
    "conversation_messages": "content",
    "visitors": "anonymous_key",
    "visitor_sessions": "landing_path",
    "visitor_events": "event_type",
    "viewer_video_progress": "video_id",
    "video_relations": "relation_type",
    "visitor_memories": "memory_key",
    "agent_actions": "action_type",
}


class AdminRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ── 查询辅助 ──────────────────────────────────────────────

    def _safe_table(self, table: str) -> str:
        if table not in ALLOWED_TABLES:
            raise ValueError(f"不允许操作表: {table}")
        return table

    def _is_json_column(self, table: str, column: str) -> bool:
        return column.endswith("_json") or column in (
            "tags", "keywords", "sources", "actions",
        )

    # ── 读取 ──────────────────────────────────────────────────

    def list_rows(
        self, table: str, profile_id: str = "", search: str = "",
        limit: int = 20, offset: int = 0,
    ) -> list[dict[str, Any]]:
        table = self._safe_table(table)
        conditions: list[str] = []
        params: list[Any] = []

        # profile 过滤
        if profile_id:
            cols = self._columns(table)
            if "profile_id" in cols:
                conditions.append("profile_id = ?")
                params.append(profile_id)

        # 搜索
        search_field = TABLE_SEARCH_FIELDS.get(table, "")
        if search and search_field:
            conditions.append(f"{search_field} LIKE ?")
            params.append(f"%{search}%")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM {table} {where} ORDER BY rowid DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connect() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def count_rows(self, table: str, profile_id: str = "", search: str = "") -> int:
        table = self._safe_table(table)
        conditions: list[str] = []
        params: list[Any] = []

        if profile_id:
            cols = self._columns(table)
            if "profile_id" in cols:
                conditions.append("profile_id = ?")
                params.append(profile_id)

        search_field = TABLE_SEARCH_FIELDS.get(table, "")
        if search and search_field:
            conditions.append(f"{search_field} LIKE ?")
            params.append(f"%{search}%")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT COUNT(*) FROM {table} {where}"

        with self._connect() as conn:
            return conn.execute(query, params).fetchone()[0]

    def get_row(self, table: str, row_id: str) -> dict[str, Any] | None:
        table = self._safe_table(table)
        with self._connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
            return dict(row) if row else None

    def _columns(self, table: str) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({self._safe_table(table)})").fetchall()
            return {row[1] for row in rows}

    # ── 写入 ──────────────────────────────────────────────────

    def create_row(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        table = self._safe_table(table)
        if table not in READ_WRITE_TABLES:
            raise ValueError(f"表 {table} 不允许新增")

        cols = self._columns(table)
        filtered = {k: v for k, v in data.items() if k in cols}
        # JSON 字段序列化
        for k, v in filtered.items():
            if self._is_json_column(table, k) and not isinstance(v, str):
                filtered[k] = json.dumps(v, ensure_ascii=False)

        columns = ", ".join(filtered.keys())
        placeholders = ", ".join("?" for _ in filtered)
        values = list(filtered.values())

        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
            row_id = data.get("id", "")
            if row_id:
                return self.get_row(table, row_id) or {}
            return {}

    def update_row(self, table: str, row_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        table = self._safe_table(table)
        if table not in READ_WRITE_TABLES:
            raise ValueError(f"表 {table} 不允许修改")

        cols = self._columns(table)
        filtered = {k: v for k, v in data.items() if k in cols and k != "id"}
        for k, v in filtered.items():
            if self._is_json_column(table, k) and not isinstance(v, str):
                filtered[k] = json.dumps(v, ensure_ascii=False)

        if not filtered:
            return self.get_row(table, row_id)

        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        values = list(filtered.values()) + [row_id]

        with self._connect() as conn:
            conn.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)
            conn.commit()
        return self.get_row(table, row_id)

    def delete_row(self, table: str, row_id: str) -> bool:
        table = self._safe_table(table)
        if table not in READ_WRITE_TABLES:
            raise ValueError(f"表 {table} 不允许删除")

        with self._connect() as conn:
            cursor = conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ── 统计 ──────────────────────────────────────────────────

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        with self._connect() as conn:
            for table in sorted(ALLOWED_TABLES):
                try:
                    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                    counts[table] = row[0] if row else 0
                except Exception:
                    counts[table] = -1
        return counts

    def schema(self) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []
        with self._connect() as conn:
            for table in sorted(ALLOWED_TABLES):
                cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
                tables.append({
                    "name": table,
                    "writable": table in READ_WRITE_TABLES,
                    "search_field": TABLE_SEARCH_FIELDS.get(table, ""),
                    "columns": [
                        {"name": c[1], "type": c[2], "nullable": not c[3], "pk": bool(c[5])}
                        for c in cols
                    ],
                })
        return tables

    # ── 审计日志 ──────────────────────────────────────────────

    def log_list(self, level: str = "", module: str = "", limit: int = 50) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if level:
            conditions.append("level = ?")
            params.append(level.upper())
        if module:
            conditions.append("module LIKE ?")
            params.append(f"%{module}%")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM admin_audit_log {where} ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def log_write(self, level: str, module: str, action: str,
                  table_name: str = "", record_id: str = "",
                  detail: str = "", ip: str = "") -> None:
        import time
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO admin_audit_log
                   (timestamp, level, module, action, table_name, record_id, detail, ip)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (time.strftime("%Y-%m-%dT%H:%M:%S"), level, module, action,
                 table_name, record_id, detail[:500], ip),
            )
            conn.commit()

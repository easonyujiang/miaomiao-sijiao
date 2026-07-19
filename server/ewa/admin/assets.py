"""视频资产三通道统一管理

一个"可上线的视频"需要三条数据通道齐备：
1. videos 表行（DB）          — 网站妙喵视频查询的数据源
2. 字幕 JSON（文件）           — subtitles/{video_id}.json，摘要质量的基础
3. 课程 JSON（文件，可选）      — lessons/{lesson_id}.json，插件课程模式

本模块提供合并视图与一站式 upsert，避免三条通道手动同步导致缺漏。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ewa.config import SUBTITLE_DIR, LESSONS_DIR
from ewa.core.logging import get_logger

logger = get_logger(__name__)


class AssetValidationError(ValueError):
    """资产格式校验失败。"""


def validate_subtitle(data: Any) -> dict:
    """校验字幕 JSON 格式，返回原数据。失败抛 AssetValidationError。"""
    if not isinstance(data, dict):
        raise AssetValidationError("字幕必须是 JSON 对象")
    entries = data.get("subtitles")
    if not isinstance(entries, list) or not entries:
        raise AssetValidationError("字幕必须包含非空 subtitles 数组")
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise AssetValidationError(f"subtitles[{i}] 必须是对象")
        if not str(entry.get("text", "")).strip():
            raise AssetValidationError(f"subtitles[{i}].text 不能为空")
        start, end = entry.get("start"), entry.get("end")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise AssetValidationError(f"subtitles[{i}] 的 start/end 必须是数字")
        if end <= start:
            raise AssetValidationError(f"subtitles[{i}] 要求 end > start")
    return data


def validate_lesson(data: Any) -> dict:
    """校验课程 JSON 格式，返回原数据。失败抛 AssetValidationError。"""
    if not isinstance(data, dict):
        raise AssetValidationError("课程必须是 JSON 对象")
    if not data.get("id"):
        raise AssetValidationError("课程缺少 id")
    if not data.get("video_id"):
        raise AssetValidationError("课程缺少 video_id")
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise AssetValidationError("课程必须包含非空 steps 数组")
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise AssetValidationError(f"steps[{i}] 必须是对象")
        for field in ("id", "question"):
            if not step.get(field):
                raise AssetValidationError(f"steps[{i}] 缺少 {field}")
        for field in ("start_ms", "end_ms"):
            if not isinstance(step.get(field), (int, float)):
                raise AssetValidationError(f"steps[{i}].{field} 必须是数字")
    return data


class AssetService:
    """视频资产管理（DB 行 + 字幕文件 + 课程文件）。

    目录可注入：测试传临时目录，生产默认走 config。
    """

    def __init__(
        self,
        db_path: str,
        subtitle_dir: Path | None = None,
        lessons_dir: Path | None = None,
    ) -> None:
        self.db_path = db_path
        self.subtitle_dir = Path(subtitle_dir) if subtitle_dir else SUBTITLE_DIR
        self.lessons_dir = Path(lessons_dir) if lessons_dir else LESSONS_DIR

    # ── DB 辅助 ────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ── 文件辅助 ───────────────────────────────────────────────

    def _subtitle_path(self, video_id: str) -> Path:
        return self.subtitle_dir / f"{video_id}.json"

    def _lesson_files(self) -> list[Path]:
        if not self.lessons_dir.exists():
            return []
        return sorted(self.lessons_dir.glob("*.json"))

    def _load_json(self, path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _lesson_for_video(self, video_id: str) -> tuple[str, Path] | None:
        """找到 video_id 对应的课程，返回 (lesson_id, 路径)。"""
        for path in self._lesson_files():
            data = self._load_json(path)
            if data and data.get("video_id") == video_id:
                return data.get("id", path.stem), path
        return None

    # ── 合并视图 ───────────────────────────────────────────────

    def list_videos(self) -> list[dict[str, Any]]:
        """所有视频的三通道状态合并视图。"""
        with self._connect() as conn:
            videos = [dict(r) for r in conn.execute(
                "SELECT id, title, platform, duration_ms, transcript_status, visibility FROM videos ORDER BY rowid DESC"
            ).fetchall()]
            seg_counts = dict(conn.execute(
                "SELECT video_id, COUNT(*) FROM video_segments GROUP BY video_id"
            ).fetchall())

        items = []
        for v in videos:
            lesson = self._lesson_for_video(v["id"])
            items.append({
                "id": v["id"],
                "title": v["title"],
                "platform": v["platform"],
                "duration_ms": v["duration_ms"],
                "visibility": v["visibility"],
                "segments_count": seg_counts.get(v["id"], 0),
                "has_subtitle": self._subtitle_path(v["id"]).exists(),
                "has_lesson": lesson is not None,
                "lesson_id": lesson[0] if lesson else "",
            })
        return items

    def get_video(self, video_id: str) -> dict[str, Any] | None:
        """单视频三通道详情。"""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
            if not row:
                return None
            video = dict(row)
            video["segments"] = [dict(r) for r in conn.execute(
                "SELECT * FROM video_segments WHERE video_id = ? ORDER BY start_ms, id", (video_id,)
            ).fetchall()]

        subtitle_path = self._subtitle_path(video_id)
        subtitle_data = self._load_json(subtitle_path) if subtitle_path.exists() else None
        lesson = self._lesson_for_video(video_id)
        lesson_data = self._load_json(lesson[1]) if lesson else None

        video["subtitle"] = {
            "exists": subtitle_path.exists(),
            "entries": len(subtitle_data.get("subtitles", [])) if subtitle_data else 0,
        }
        video["lesson"] = {
            "exists": lesson is not None,
            "lesson_id": lesson[0] if lesson else "",
            "steps": len(lesson_data.get("steps", [])) if lesson_data else 0,
        }
        return video

    # ── 一站式 upsert ─────────────────────────────────────────

    def upsert_video(
        self,
        video: dict[str, Any],
        segments: list[dict[str, Any]] | None = None,
        subtitle: dict[str, Any] | None = None,
        lesson: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """一站式上线/更新视频：DB 行 + 片段 + 字幕 + 课程（幂等）。"""
        video_id = video.get("id")
        if not video_id:
            raise AssetValidationError("video.id 为必填字段")
        if subtitle is not None:
            validate_subtitle(subtitle)
        if lesson is not None:
            validate_lesson(lesson)

        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM videos WHERE id = ?", (video_id,)).fetchone()
            cols = {r[1] for r in conn.execute("PRAGMA table_info(videos)").fetchall()}
            filtered = {k: v for k, v in video.items() if k in cols}
            for k, v in filtered.items():
                if k.endswith("_json") and not isinstance(v, str):
                    filtered[k] = json.dumps(v, ensure_ascii=False)

            if exists:
                assignments = ", ".join(f"{k} = ?" for k in filtered if k != "id")
                values = [v for k, v in filtered.items() if k != "id"] + [video_id]
                if assignments:
                    conn.execute(f"UPDATE videos SET {assignments} WHERE id = ?", values)
            else:
                conn.execute(
                    f"INSERT INTO videos ({', '.join(filtered)}) VALUES ({', '.join('?' for _ in filtered)})",
                    list(filtered.values()),
                )

            # segments 全量替换（同事务）
            if segments is not None:
                conn.execute("DELETE FROM video_segments WHERE video_id = ?", (video_id,))
                seg_cols = {r[1] for r in conn.execute("PRAGMA table_info(video_segments)").fetchall()}
                for i, seg in enumerate(segments):
                    seg = dict(seg)
                    seg.setdefault("id", f"{video_id}_seg_{i + 1}")
                    seg["video_id"] = video_id
                    # title/summary 是 NOT NULL 列，缺省补空串
                    seg.setdefault("title", "")
                    seg.setdefault("summary", "")
                    seg_filtered = {k: v for k, v in seg.items() if k in seg_cols}
                    for k, v in seg_filtered.items():
                        if k.endswith("_json") and not isinstance(v, str):
                            seg_filtered[k] = json.dumps(v, ensure_ascii=False)
                    conn.execute(
                        f"INSERT INTO video_segments ({', '.join(seg_filtered)}) VALUES ({', '.join('?' for _ in seg_filtered)})",
                        list(seg_filtered.values()),
                    )
            conn.commit()

        written: dict[str, str] = {}
        if subtitle is not None:
            self.subtitle_dir.mkdir(parents=True, exist_ok=True)
            path = self._subtitle_path(video_id)
            path.write_text(json.dumps(subtitle, ensure_ascii=False, indent=2), encoding="utf-8")
            written["subtitle_path"] = str(path)

        if lesson is not None:
            lesson = dict(lesson)
            lesson.setdefault("video_id", video_id)
            lesson.setdefault("id", f"lesson_{video_id}")
            self.lessons_dir.mkdir(parents=True, exist_ok=True)
            path = self.lessons_dir / f"{lesson['id']}.json"
            path.write_text(json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
            written["lesson_path"] = str(path)

        return {"video_id": video_id, "updated": bool(exists), **written}

    # ── 单资产写入 ─────────────────────────────────────────────

    def save_subtitle(self, video_id: str, data: dict[str, Any]) -> Path:
        validate_subtitle(data)
        self.subtitle_dir.mkdir(parents=True, exist_ok=True)
        path = self._subtitle_path(video_id)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_lesson(self, video_id: str, data: dict[str, Any]) -> Path:
        data = dict(data)
        data.setdefault("video_id", video_id)
        data.setdefault("id", f"lesson_{video_id}")
        validate_lesson(data)
        if data["video_id"] != video_id:
            raise AssetValidationError("课程 video_id 与路径参数不一致")
        self.lessons_dir.mkdir(parents=True, exist_ok=True)
        path = self.lessons_dir / f"{data['id']}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    # ── 删除 ───────────────────────────────────────────────────

    def delete_video(self, video_id: str) -> dict[str, Any]:
        """删除视频及全部关联：DB 行、片段、字幕文件、课程文件。"""
        removed: dict[str, Any] = {"video_row": False, "segments": 0, "subtitle_file": False, "lesson_file": ""}

        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM video_segments WHERE video_id = ?", (video_id,))
            removed["segments"] = cursor.rowcount
            cursor = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            removed["video_row"] = cursor.rowcount > 0
            conn.commit()

        subtitle_path = self._subtitle_path(video_id)
        if subtitle_path.exists():
            subtitle_path.unlink()
            removed["subtitle_file"] = True

        lesson = self._lesson_for_video(video_id)
        if lesson:
            lesson[1].unlink()
            removed["lesson_file"] = lesson[0]

        return removed

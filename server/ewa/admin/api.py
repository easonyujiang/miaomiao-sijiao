"""管理后台 API 路由

提供对 20 张表的统一 CRUD 端点 + 日志查询 + 统计 + schema 元数据。
所有端点在 /api/admin/* 下，需要 Bearer Token 认证。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ewa.admin.auth import verify_token
from ewa.admin.repository import AdminRepository, ALLOWED_TABLES, READ_WRITE_TABLES
from ewa.core.logging import get_logger, log_admin_action

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _repo(request: Request) -> AdminRepository:
    return request.app.state.admin_repository


# ── 特殊路由（必须在 /{table} 之前注册） ──────────────────────

@router.get("/stats")
async def admin_stats(request: Request, _token: str = Depends(verify_token)):
    repo = _repo(request)
    return {"tables": repo.stats()}


@router.get("/schema")
async def admin_schema(request: Request, _token: str = Depends(verify_token)):
    return _repo(request).schema()


@router.get("/logs/list")
async def list_logs(
    request: Request,
    _token: str = Depends(verify_token),
    level: str = Query(""),
    module: str = Query(""),
    limit: int = Query(50, ge=1, le=500),
):
    return {"items": _repo(request).log_list(level, module, limit)}


# ── 通用 CRUD ──────────────────────────────────────────────────

@router.get("/{table}")
async def list_rows(
    table: str,
    request: Request,
    _token: str = Depends(verify_token),
    profile_id: str = Query(""),
    search: str = Query(""),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(404, f"未知表: {table}")
    repo = _repo(request)
    rows = repo.list_rows(table, profile_id, search, limit, offset)
    total = repo.count_rows(table, profile_id, search)
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/{table}/{row_id}")
async def get_row(
    table: str, row_id: str,
    request: Request, _token: str = Depends(verify_token),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(404, f"未知表: {table}")
    row = _repo(request).get_row(table, row_id)
    if not row:
        raise HTTPException(404, f"记录不存在: {row_id}")
    return row


@router.post("/{table}", status_code=201)
async def create_row(
    table: str,
    request: Request,
    _token: str = Depends(verify_token),
):
    if table not in READ_WRITE_TABLES:
        raise HTTPException(400, f"表 {table} 不允许新增")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "请求体必须为 JSON")
    repo = _repo(request)
    try:
        result = repo.create_row(table, body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log_admin_action("admin", "CREATE", table, body.get("id", ""),
                      f"创建 {table} 记录", request.client.host if request.client else None)
    return result


@router.put("/{table}/{row_id}")
async def update_row(
    table: str, row_id: str,
    request: Request, _token: str = Depends(verify_token),
):
    if table not in READ_WRITE_TABLES:
        raise HTTPException(400, f"表 {table} 不允许修改")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "请求体必须为 JSON")
    repo = _repo(request)
    try:
        result = repo.update_row(table, row_id, body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if result is None:
        raise HTTPException(404, f"记录不存在: {row_id}")
    log_admin_action("admin", "UPDATE", table, row_id,
                      f"更新 {table}/{row_id}", request.client.host if request.client else None)
    return result


@router.delete("/{table}/{row_id}")
async def delete_row(
    table: str, row_id: str,
    request: Request, _token: str = Depends(verify_token),
):
    if table not in READ_WRITE_TABLES:
        raise HTTPException(400, f"表 {table} 不允许删除")
    repo = _repo(request)
    if not repo.delete_row(table, row_id):
        raise HTTPException(404, f"记录不存在: {row_id}")
    log_admin_action("admin", "DELETE", table, row_id,
                      f"删除 {table}/{row_id}", request.client.host if request.client else None)
    return {"ok": True}


# ── 视频导入（批量：video + segments + lesson） ─────────────────

class VideoImportRequest(BaseModel):
    video: dict[str, Any]           # videos 表字段
    segments: list[dict[str, Any]]  # video_segments 表字段数组
    lesson: dict[str, Any] | None = None  # 可选的课程 JSON（含 steps）

@router.post("/import/video", status_code=201)
async def import_video(
    request: Request,
    _token: str = Depends(verify_token),
):
    """批量导入视频：一条视频 + N 个片段 + 可选课程数据。"""
    try:
        body = await request.json()
        payload = VideoImportRequest(**body)
    except Exception as e:
        raise HTTPException(400, f"请求格式错误: {e}")

    repo = _repo(request)
    video = payload.video
    segments = payload.segments
    lesson = payload.lesson

    # 1. 写入视频
    if "id" not in video:
        raise HTTPException(400, "video.id 为必填字段")
    try:
        repo.create_row("videos", video)
    except Exception as e:
        raise HTTPException(400, f"创建视频失败: {e}")

    # 2. 批量写入片段
    created_segments = []
    for seg in segments:
        seg["video_id"] = video["id"]
        if "id" not in seg:
            seg["id"] = f"{video['id']}_seg_{len(created_segments)+1}"
        try:
            repo.create_row("video_segments", seg)
            created_segments.append(seg["id"])
        except Exception as e:
            raise HTTPException(400, f"创建片段失败 ({seg.get('id')}): {e}")

    # 3. 保存课程 JSON（如果提供了）
    lesson_path = ""
    if lesson:
        lesson.setdefault("video_id", video["id"])
        lesson.setdefault("platform", video.get("platform", "bilibili"))
        lesson.setdefault("creator_name", video.get("creator_name", ""))
        if "id" not in lesson:
            lesson["id"] = f"lesson_{video['id']}"

        from pathlib import Path
        import json
        lessons_dir = Path("data/miaomiao/lessons")
        lessons_dir.mkdir(parents=True, exist_ok=True)
        lesson_file = lessons_dir / f"{lesson['id']}.json"
        lesson_file.write_text(json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
        lesson_path = str(lesson_file)

    log_admin_action("admin", "IMPORT", "videos", video["id"],
                      f"导入视频 + {len(created_segments)} 片段" +
                      (f" + 课程" if lesson else ""),
                      request.client.host if request.client else None)

    return {
        "ok": True,
        "video_id": video["id"],
        "segments": created_segments,
        "lesson_path": lesson_path,
    }

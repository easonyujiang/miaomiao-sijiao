from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .service import SiteService


router = APIRouter(prefix="/api", tags=["creator-site"])


class SessionCreateRequest(BaseModel):
    slug: str = Field(default="ashley", description="创作者 site slug；多博主部署时由前端从 NEXT_PUBLIC_SITE_SLUG 传入")
    anonymous_key: str = Field(min_length=8, max_length=200)
    source: str = "direct"
    landing_path: str = "/"


class EventCreateRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    section_id: str | None = None
    target_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ProgressUpdateRequest(BaseModel):
    visitor_id: str
    position_ms: int = Field(ge=0)


class SiteChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    video_id: str | None = None
    current_time_ms: int = Field(default=0, ge=0)


def _service(request: Request) -> SiteService:
    return request.app.state.site_service


@router.get("/site/{slug}")
async def get_site(slug: str, request: Request):
    site = _service(request).site(slug)
    if not site:
        raise HTTPException(status_code=404, detail="Creator site not found")
    return site


@router.get("/videos/{video_id}")
async def get_video(video_id: str, request: Request):
    video = _service(request).video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/site/{slug}/diary")
async def list_diary(slug: str, request: Request, limit: int = 30, offset: int = 0):
    diary = _service(request).diary_list(slug, limit=limit, offset=offset)
    if diary is None:
        raise HTTPException(status_code=404, detail="Creator site not found")
    return {"items": diary}


@router.get("/site/{slug}/diary/{entry_date}")
async def get_diary(slug: str, entry_date: str, request: Request):
    diary = _service(request).diary_by_date(slug, entry_date)
    if not diary:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    return diary


@router.post("/sessions", status_code=201)
async def create_session(payload: SessionCreateRequest, request: Request):
    result = request.app.state.site_repository.create_session(
        payload.slug, payload.anonymous_key, payload.source, payload.landing_path
    )
    if not result:
        raise HTTPException(status_code=404, detail="Creator site not found")
    return result


@router.post("/sessions/{session_id}/events", status_code=201)
async def create_event(session_id: str, payload: EventCreateRequest, request: Request):
    try:
        event_id = request.app.state.site_repository.record_event(
            session_id, payload.event_type, payload.section_id, payload.target_id, payload.payload
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    return {"event_id": event_id}


@router.put("/videos/{video_id}/progress")
async def update_video_progress(video_id: str, payload: ProgressUpdateRequest, request: Request):
    if not _service(request).video(video_id):
        raise HTTPException(status_code=404, detail="Video not found")
    try:
        request.app.state.site_repository.update_progress(
            payload.visitor_id, video_id, payload.position_ms
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=404, detail="Visitor not found") from exc
    return {"success": True}


@router.post("/site/{slug}/chat")
async def chat_with_pet(slug: str, payload: SiteChatRequest, request: Request):
    try:
        result = await _service(request).chat(
            slug,
            payload.message,
            payload.session_id,
            payload.video_id,
            payload.current_time_ms,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    if not result:
        raise HTTPException(status_code=404, detail="Creator site not found")
    return result

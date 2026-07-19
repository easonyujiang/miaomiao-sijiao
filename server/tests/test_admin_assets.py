"""管理后台视频资产三通道管理测试

覆盖：
- AssetService 服务层：upsert / 校验 / 删除（临时目录注入）
- /api/admin/assets/* API：鉴权 + 端到端
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ewa.admin.assets import AssetService, AssetValidationError
from ewa.api.main import create_app
from ewa.core.middleware import reset_rate_limiters


# ── 测试素材 ──────────────────────────────────────────────────

VIDEO = {
    "id": "test_video_001",
    "profile_id": "profile_ashley",
    "platform": "bilibili",
    "title": "测试视频",
    "transcript_status": "manual",
    "visibility": "public",
}

SEGMENTS = [
    {"start_ms": 0, "end_ms": 10000, "title": "开场", "segment_type": "hook", "summary": "开场白"},
    {"start_ms": 10000, "end_ms": 20000, "title": "正片", "segment_type": "knowledge", "summary": "正文"},
]

SUBTITLE = {
    "bvid": "test_video_001",
    "title": "测试视频",
    "subtitles": [
        {"start": 0, "end": 5, "text": "大家好"},
        {"start": 5, "end": 10, "text": "今天讲测试"},
    ],
}

LESSON = {
    "id": "lesson_test_001",
    "video_id": "test_video_001",
    "title": "测试课程",
    "steps": [
        {"id": "step_1", "question": "什么是测试？", "start_ms": 0, "end_ms": 10000},
    ],
}


# ── 服务层 fixture ────────────────────────────────────────────

@pytest.fixture
def service():
    """独立临时 DB + 临时资产目录。"""
    tmp = Path(tempfile.mkdtemp())
    db_path = str(tmp / "test.db")

    # 用完整 app 初始化 DB 表结构（走 lifespan 建表 + seed）
    os.environ["EWA_SITE_DB_PATH"] = db_path
    app = create_app(site_db_path=db_path)
    with TestClient(app):
        pass

    return AssetService(
        db_path,
        subtitle_dir=tmp / "subtitles",
        lessons_dir=tmp / "lessons",
    )


# ── 服务层测试 ────────────────────────────────────────────────

class TestAssetService:
    def test_upsert_creates_all_channels(self, service):
        result = service.upsert_video(VIDEO, SEGMENTS, SUBTITLE, LESSON)
        assert result["video_id"] == "test_video_001"
        assert result["updated"] is False
        assert "subtitle_path" in result and "lesson_path" in result

        items = {v["id"]: v for v in service.list_videos()}
        item = items["test_video_001"]
        assert item["has_subtitle"] is True
        assert item["has_lesson"] is True
        assert item["lesson_id"] == "lesson_test_001"
        assert item["segments_count"] == 2

        detail = service.get_video("test_video_001")
        assert detail["subtitle"]["entries"] == 2
        assert detail["lesson"]["steps"] == 1
        assert len(detail["segments"]) == 2

    def test_upsert_is_idempotent_and_replaces_segments(self, service):
        service.upsert_video(VIDEO, SEGMENTS, SUBTITLE, LESSON)
        # 再次 upsert：更新标题，片段换成 1 个
        updated_video = {**VIDEO, "title": "测试视频 v2"}
        result = service.upsert_video(updated_video, SEGMENTS[:1])
        assert result["updated"] is True

        detail = service.get_video("test_video_001")
        assert detail["title"] == "测试视频 v2"
        assert len(detail["segments"]) == 1  # 全量替换，不追加

    def test_upsert_missing_id_rejected(self, service):
        with pytest.raises(AssetValidationError):
            service.upsert_video({"title": "没有 id"})

    def test_subtitle_validation(self, service):
        with pytest.raises(AssetValidationError):
            service.save_subtitle("v", {"subtitles": []})
        with pytest.raises(AssetValidationError):
            service.save_subtitle("v", {"subtitles": [{"start": 0, "end": 5, "text": "  "}]})
        with pytest.raises(AssetValidationError):
            service.save_subtitle("v", {"subtitles": [{"start": 5, "end": 5, "text": "x"}]})

    def test_lesson_validation(self, service):
        with pytest.raises(AssetValidationError):
            service.save_lesson("test_video_001", {"id": "l1", "steps": []})
        with pytest.raises(AssetValidationError):
            # video_id 与路径参数不一致
            service.save_lesson("test_video_001", {**LESSON, "video_id": "other_video"})

    def test_delete_removes_all_channels(self, service):
        service.upsert_video(VIDEO, SEGMENTS, SUBTITLE, LESSON)
        removed = service.delete_video("test_video_001")
        assert removed["video_row"] is True
        assert removed["segments"] == 2
        assert removed["subtitle_file"] is True
        assert removed["lesson_file"] == "lesson_test_001"

        assert service.get_video("test_video_001") is None
        items = {v["id"]: v for v in service.list_videos()}
        assert "test_video_001" not in items


# ── API 层测试 ────────────────────────────────────────────────

@pytest.fixture
def api_client(monkeypatch):
    """带鉴权的 API 客户端，资产目录指向临时目录。"""
    import ewa.admin.auth as auth_module
    import ewa.admin.assets as assets_module

    reset_rate_limiters()
    tmp = Path(tempfile.mkdtemp())
    db_path = str(tmp / "test.db")
    os.environ["EWA_SITE_DB_PATH"] = db_path

    monkeypatch.setattr(auth_module, "_ADMIN_TOKEN", "test-token")
    monkeypatch.setattr(assets_module, "SUBTITLE_DIR", tmp / "subtitles")
    monkeypatch.setattr(assets_module, "LESSONS_DIR", tmp / "lessons")

    app = create_app(site_db_path=db_path)
    with TestClient(app) as c:
        c.headers["Authorization"] = "Bearer test-token"
        yield c


class TestAssetsAPI:
    def test_requires_auth(self, api_client):
        r = TestClient(api_client.app).get("/api/admin/assets/videos")
        assert r.status_code == 401

    def test_strict_bearer_prefix(self, api_client):
        c = TestClient(api_client.app)
        r = c.get("/api/admin/assets/videos", headers={"Authorization": "xxBearer test-token"})
        assert r.status_code == 401

    def test_full_lifecycle(self, api_client):
        # 上线
        r = api_client.post("/api/admin/assets/videos", json={
            "video": VIDEO, "segments": SEGMENTS, "subtitle": SUBTITLE, "lesson": LESSON,
        })
        assert r.status_code == 201, r.text
        assert r.json()["ok"] is True

        # 列表可见三通道状态
        r = api_client.get("/api/admin/assets/videos")
        items = {v["id"]: v for v in r.json()["items"]}
        assert items["test_video_001"]["has_subtitle"] is True
        assert items["test_video_001"]["has_lesson"] is True

        # 详情
        r = api_client.get("/api/admin/assets/videos/test_video_001")
        assert r.status_code == 200
        assert r.json()["subtitle"]["entries"] == 2

        # 替换字幕
        new_sub = {**SUBTITLE, "subtitles": [{"start": 0, "end": 3, "text": "新字幕"}]}
        r = api_client.put("/api/admin/assets/videos/test_video_001/subtitle", json=new_sub)
        assert r.status_code == 200

        # 非法字幕被拒
        r = api_client.put("/api/admin/assets/videos/test_video_001/subtitle",
                           json={"subtitles": [{"start": 3, "end": 0, "text": "坏"}]})
        assert r.status_code == 400

        # 删除
        r = api_client.delete("/api/admin/assets/videos/test_video_001")
        assert r.status_code == 200
        assert r.json()["removed"]["video_row"] is True
        # 二次删除 404
        r = api_client.delete("/api/admin/assets/videos/test_video_001")
        assert r.status_code == 404

    def test_assets_route_not_shadowed_by_generic_crud(self, api_client):
        """/assets/* 必须先于通用 /{table} 匹配（回归：路由顺序）。"""
        r = api_client.get("/api/admin/assets/videos")
        assert r.status_code == 200
        assert "items" in r.json()

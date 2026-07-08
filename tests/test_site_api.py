from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from ewa.api.main import create_app


def test_creator_site_end_to_end(tmp_path):
    db_path = tmp_path / "miaomiao.db"
    app = create_app(site_db_path=str(db_path))

    with TestClient(app) as client:
        site_response = client.get("/api/site/ashley")
        assert site_response.status_code == 200
        site = site_response.json()
        assert site["pet"]["name"] == "妙喵"
        assert len(site["videos"]) == 2
        assert site["videos"][0]["segments"]

        session_response = client.post(
            "/api/sessions",
            json={
                "slug": "ashley",
                "anonymous_key": "test-visitor-0001",
                "source": "pytest",
                "landing_path": "/",
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        chat_response = client.post(
            "/api/site/ashley/chat",
            json={
                "message": "怎么关闭设备动作权限？",
                "session_id": session["session_id"],
                "video_id": "device-motion-permission-demo",
                "current_time_ms": 5000,
            },
        )
        assert chat_response.status_code == 200
        chat = chat_response.json()
        assert chat["actions"][0]["type"] == "seek_video"
        assert chat["actions"][0]["time_ms"] == 9000

        event_response = client.post(
            f"/api/sessions/{session['session_id']}/events",
            json={
                "event_type": "video_seek",
                "section_id": "videos",
                "target_id": "device-motion-permission-demo",
                "payload": {"seconds": 9},
            },
        )
        assert event_response.status_code == 201

        progress_response = client.put(
            "/api/videos/device-motion-permission-demo/progress",
            json={"visitor_id": session["visitor_id"], "position_ms": 9000},
        )
        assert progress_response.status_code == 200

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT count(*) FROM conversation_messages").fetchone()[0] == 2
        assert connection.execute("SELECT last_position_ms FROM viewer_video_progress").fetchone()[0] == 9000


def test_unknown_creator_returns_404(tmp_path):
    app = create_app(site_db_path=str(tmp_path / "site.db"))
    with TestClient(app) as client:
        assert client.get("/api/site/not-found").status_code == 404

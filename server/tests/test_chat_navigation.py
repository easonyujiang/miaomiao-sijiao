"""问答 → 精确跳转闭环测试

覆盖三个新能力：
1. 网站妙喵：问"有没有相关讨论"→ community 意图 + open_topic 跳转按钮
2. 网站妙喵：视频摘要里的 [mm:ss] → seek 按钮落到真实时间点
3. 插件问答：问"有没有相关讨论"→ 返回 topics 列表
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

from ewa.api.main import create_app
from ewa.core.middleware import reset_rate_limiters
from ewa.website.service import SiteService


@pytest.fixture
def client():
    reset_rate_limiters()
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    os.environ["EWA_SITE_DB_PATH"] = db_path
    app = create_app(site_db_path=db_path)
    with TestClient(app) as c:
        c.app_state_db_path = db_path
        yield c


def _insert_topic(db_path: str, topic_id: str, title: str, content: str, reply_count: int = 2):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO community_topics (id, profile_id, title, content, category, reply_count)
           VALUES (?, 'profile_ashley', ?, ?, 'discussion', ?)""",
        (topic_id, title, content, reply_count),
    )
    conn.commit()
    conn.close()


class TestWebsiteCommunityQuery:
    def test_discussion_query_returns_open_topic_actions(self, client):
        _insert_topic(
            client.app_state_db_path,
            "topic_test_001",
            "正当防卫的构成要件讨论",
            "大家对假想防卫和防卫过当有什么理解？",
        )
        r = client.post("/api/site/ashley/chat", json={"message": "有没有关于正当防卫的讨论？"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "community"
        topic_actions = [a for a in data["actions"] if a["type"] == "open_topic"]
        assert len(topic_actions) == 1
        assert topic_actions[0]["topic_id"] == "topic_test_001"
        # 附带社区总入口
        assert any(a.get("target") == "community" for a in data["actions"])

    def test_discussion_query_no_match_falls_through(self, client):
        """无匹配话题时不应返回 community 意图。"""
        r = client.post("/api/site/ashley/chat", json={"message": "有没有关于量子力学的讨论？"})
        assert r.status_code == 200
        assert r.json()["intent"] != "community"


class TestSeekTimestamp:
    def test_extract_first_time_ms(self):
        assert SiteService._extract_first_time_ms("关键在 [08:23] 这里") == (8 * 60 + 23) * 1000
        assert SiteService._extract_first_time_ms("[00:05] 开场") == 5000
        assert SiteService._extract_first_time_ms("没有时间戳") is None
        assert SiteService._extract_first_time_ms("多个 [01:00] 和 [02:30] 取第一个") == 60000


class TestExtCommunityQuery:
    def test_ext_chat_returns_topics(self, client):
        _insert_topic(
            client.app_state_db_path,
            "topic_test_002",
            "正当防卫的构成要件讨论",
            "大家对假想防卫有什么理解？",
        )
        r = client.post("/api/ext/chat", json={
            "message": "有没有关于正当防卫的讨论？",
            "video_id": "BV1mJ4m147PG",
            "platform": "bilibili",
            "current_time_sec": 60,
        })
        assert r.status_code == 200
        data = r.json()
        assert "topics" in data
        assert data["topics"][0]["id"] == "topic_test_002"
        assert "正当防卫" in data["answer"]

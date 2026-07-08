from __future__ import annotations

from typing import Any

from .repository import SiteRepository


class SiteService:
    def __init__(self, repository: SiteRepository):
        self.repository = repository

    def site(self, slug: str) -> dict[str, Any] | None:
        profile = self.repository.profile(slug)
        if not profile:
            return None
        profile_id = profile["id"]
        pet = self.repository.pet(profile_id) or {}
        return {
            "identity": {
                "name": profile["display_name"],
                "initials": profile["initials"],
                "role": profile["role"],
                "location": profile["location"],
                "status": profile["status"],
                "tagline": profile["tagline"],
                "summary": profile["summary"],
                "tags": self.repository.decode_json(profile["tags_json"], []),
            },
            "product": {
                "validationEndpoint": "先用我的个人网站、我的资料和我的视频跑通端到端体验。",
                "finalGoal": "为每位视频博主生成一个有个人色彩的宠物 Agent，让粉丝能围绕视频学习、聊天、追问，并跳转到博主的其他视频和具体片段。",
                "competitionTrack": "抖音精选赛道二：内容重构，让视频成为你的生活搭子。",
            },
            "pet": {
                "name": pet.get("name", "妙喵"),
                "role": pet.get("role", "博主宠物"),
                "greeting": pet.get("greeting", "你好，我是妙喵。"),
                "traits": self.repository.decode_json(pet.get("traits_json"), []),
                "styleBasis": self.repository.decode_json(pet.get("style_rules_json"), {}).get("basis", ""),
            },
            "projects": [self._project(row) for row in self.repository.projects(profile_id)],
            "videos": [self._video(row) for row in self.repository.videos(profile_id)],
            "faq": [self._faq(row) for row in self.repository.faqs(profile_id)],
            "links": [self._link(row) for row in self.repository.links(profile_id)],
            "sources": [self._source(row) for row in self.repository.sources(profile_id)],
            "diary": [self._diary(row) for row in self.repository.diary(profile_id, limit=10)],
            "stats": self.repository.public_stats(profile_id),
        }

    def diary_list(self, slug: str, limit: int = 30, offset: int = 0) -> list[dict[str, Any]] | None:
        profile = self.repository.profile(slug)
        if not profile:
            return None
        return [self._diary(row) for row in self.repository.diary(profile["id"], limit=limit, offset=offset)]

    def diary_by_date(self, slug: str, entry_date: str) -> dict[str, Any] | None:
        profile = self.repository.profile(slug)
        if not profile:
            return None
        row = self.repository.diary_by_date(profile["id"], entry_date)
        return self._diary(row) if row else None

    def video(self, video_id: str) -> dict[str, Any] | None:
        row = self.repository.video(video_id)
        return self._video(row) if row else None

    def chat(self, slug: str, message: str, session_id: str | None = None, video_id: str | None = None, current_time_ms: int = 0) -> dict[str, Any] | None:
        profile = self.repository.profile(slug)
        if not profile:
            return None
        # 日记优先：当访客问"最近在做什么 / 今天 / 昨天 / 在忙什么 / 近况 / 日记"时，
        # 先用最近公开日记作答，让博主是"持续在更新的人"，而不是回退到 FAQ。
        normalized = message.lower().strip()
        diary_triggers = ("最近", "今天", "昨天", "在做什么", "在忙什么", "近况", "日记", "更新", "最近在", "在干")
        if any(trigger in message for trigger in diary_triggers):
            diary_rows = self.repository.diary(profile["id"], limit=3)
            if diary_rows:
                latest = self._diary(diary_rows[0])
                summaries = "；".join(f"{d['date']} {d['title']}" for d in (self._diary(r) for r in diary_rows))
                answer = f"主人最近在做的：{summaries}。最新一条是 {latest['date']} 的「{latest['title']}」——{latest['summary']}"
                sources = [{"type": "diary", "date": latest["date"], "label": latest["title"]}]
                actions = [{"type": "open_section", "target": "diary", "label": "查看最近日记"}]
                result = {
                    "answer": answer,
                    "expression": "excited",
                    "intent": "diary",
                    "sources": sources,
                    "actions": actions,
                    "context": {"video_id": video_id, "current_time_ms": current_time_ms},
                }
                if session_id:
                    self.repository.save_message(session_id, "visitor", message, "diary")
                    self.repository.save_message(session_id, "pet", answer, "diary", sources, actions)
                return result
        faqs = self.repository.faqs(profile["id"])
        ranked: list[tuple[int, dict[str, Any]]] = []
        for faq in faqs:
            keywords = self.repository.decode_json(faq.get("keywords_json"), [])
            score = sum(2 for keyword in keywords if str(keyword).lower() in normalized)
            if faq["question"].replace("？", "").lower() in normalized:
                score += 10
            if video_id and faq["intent"] in {"permission", "video"}:
                score += 1
            ranked.append((score, faq))
        ranked.sort(key=lambda item: (item[0], -item[1]["sort_order"]), reverse=True)
        faq = ranked[0][1] if ranked and ranked[0][0] > 0 else next((row for row in faqs if row["intent"] == "who"), faqs[0])
        sources = self.repository.decode_json(faq.get("sources_json"), [])
        actions = self.repository.decode_json(faq.get("actions_json"), [])
        result = {
            "answer": faq["answer"],
            "expression": "excited" if any(action.get("type") in {"seek_video", "open_video"} for action in actions) else "thinking",
            "intent": faq["intent"],
            "sources": sources,
            "actions": actions,
            "context": {"video_id": video_id, "current_time_ms": current_time_ms},
        }
        if session_id:
            self.repository.save_message(session_id, "visitor", message, faq["intent"])
            pet_message_id = self.repository.save_message(session_id, "pet", faq["answer"], faq["intent"], sources, actions)
            for action in actions:
                self.repository.record_event(session_id, "agent_action_proposed", faq.get("target_section"), action.get("video_id") or action.get("target"), {"message_id": pet_message_id, "action": action})
        return result

    @staticmethod
    def _project(row: dict[str, Any]) -> dict[str, Any]:
        return {"id": row["id"], "name": row["name"], "stage": row["stage"], "summary": row["summary"], "result": row.get("body") or "", "tags": SiteRepository.decode_json(row.get("tags_json"), []), "href": "#videos" if row["id"] != "creator-workbench" else "#projects", "featured": bool(row["is_featured"])}

    @staticmethod
    def _video(row: dict[str, Any]) -> dict[str, Any]:
        return {"id": row["id"], "title": row["title"], "type": "本地竖屏演示视频" if row["duration_ms"] else "录音文稿", "duration": round(row["duration_ms"] / 1000), "source": row.get("source_url") or row.get("local_ref") or "", "summary": row.get("description") or "", "tags": SiteRepository.decode_json(row.get("tags_json"), []), "segments": [{"id": segment["id"], "start": segment["start_ms"] / 1000, "end": segment["end_ms"] / 1000, "title": segment["title"], "summary": segment["summary"], "kind": segment["segment_type"]} for segment in row.get("segments", [])]}

    @staticmethod
    def _faq(row: dict[str, Any]) -> dict[str, Any]:
        actions = SiteRepository.decode_json(row.get("actions_json"), [])
        video_action = next((action for action in actions if action.get("type") in {"seek_video", "open_video"}), {})
        return {"id": row["intent"], "question": row["question"], "answer": row["answer"], "target": row.get("target_section"), "videoId": video_action.get("video_id"), "seekTo": (video_action.get("time_ms") or 0) / 1000 if video_action else None}

    @staticmethod
    def _link(row: dict[str, Any]) -> dict[str, Any]:
        return {"label": row["label"], "value": row["value"], "href": row["url"], "visibility": row["visibility"]}

    @staticmethod
    def _source(row: dict[str, Any]) -> dict[str, Any]:
        metadata = SiteRepository.decode_json(row.get("metadata_json"), {})
        kind = row["source_type"] if row["source_type"] in {"document", "video", "transcript", "website"} else "document"
        return {"title": row["title"], "kind": kind, "location": row["location"], "status": "indexed" if row["ingest_status"] == "indexed" else "reference-only", "summary": metadata.get("summary", "")}

    @staticmethod
    def _diary(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "date": row["entry_date"],
            "title": row["title"],
            "mood": row.get("mood") or "",
            "weather": row.get("weather") or "",
            "location": row.get("location") or "",
            "summary": row["summary"],
            "body": row["body"],
            "tags": SiteRepository.decode_json(row.get("tags_json"), []),
            "links": SiteRepository.decode_json(row.get("links_json"), []),
            "highlights": SiteRepository.decode_json(row.get("highlights_json"), []),
            "pinned": bool(row.get("is_pinned")),
        }

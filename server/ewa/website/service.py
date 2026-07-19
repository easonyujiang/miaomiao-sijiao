from __future__ import annotations

import time
from typing import Any

from ewa.llm import LLMClient
from ewa.extension.mood import build_segments, mood_for

from .repository import SiteRepository

# 写作样本缓存：{profile_id: (expire_time, samples)}
_SAMPLE_CACHE: dict[str, tuple[float, str]] = {}
_SAMPLE_CACHE_TTL = 300  # 5 分钟缓存


class SiteService:
    def __init__(self, repository: SiteRepository):
        self.repository = repository

    # ── 风格学习（从数据中自动提取） ─────────────────────────────

    def _collect_writing_samples(self, profile_id: str) -> str:
        """采集博主所有写作样本，作为风格学习的语料（带缓存）。"""
        # 检查缓存
        now = time.monotonic()
        if profile_id in _SAMPLE_CACHE:
            expire, cached = _SAMPLE_CACHE[profile_id]
            if now < expire:
                return cached

        parts: list[str] = []

        # 日记正文（最近 10 条，各取前 200 字）
        diary_rows = self.repository.diary(profile_id, limit=10)
        for row in diary_rows:
            body = (row.get("body") or "").strip()
            if body:
                # 去掉 markdown 标题标记
                body_clean = body.replace("## ", "").replace("### ", "")
                parts.append(body_clean[:200])

        # FAQ 答案
        faq_rows = self.repository.faqs(profile_id)
        for row in faq_rows[:5]:
            answer = (row.get("answer") or "").strip()
            if answer:
                parts.append(answer)

        # 博主简介
        profile = self.repository.profile_by_id(profile_id)
        if profile:
            summary = (profile.get("summary") or "").strip()
            if summary:
                parts.append(summary)

        samples = "\n\n---\n\n".join(parts)
        _SAMPLE_CACHE[profile_id] = (now + _SAMPLE_CACHE_TTL, samples)
        return samples

    async def _analyze_style(self, samples: str) -> dict[str, Any]:
        """用 LLM 分析写作样本，提取风格特征。"""
        client = LLMClient()
        if not client.is_available:
            return {}

        system = """你是一位语言风格分析专家。请分析以下写作样本，提取作者的表达风格特征。

严格按 JSON 格式返回，不要加任何其他文字：
{
  "catchphrases": ["重复出现的口头禅或标志性用词"],
  "sentence_endings": ["常用的句尾语气词或标点习惯"],
  "filler_words": ["高频出现的连接词、语气词"],
  "tone": "一句话概括语气特点",
  "sentence_length": "short/medium/long",
  "avoid_patterns": ["作者从不或极少使用的表达方式"],
  "persona_voice": "用50字以内概括这个人的表达人格",
  "emoji_style": "emoji使用习惯描述"
}

注意：
- catchphrases 必须真的在样本中反复出现，不要编造
- 如果某特征不明显，用空数组/空字符串
- 关注语气词、句尾习惯、口语化程度、句子长度"""

        user = f"以下是作者的全部写作样本，请分析语言风格：\n\n{samples[:4000]}"

        result = await client.chat_json(system, user, max_tokens=400)
        if result and isinstance(result, dict):
            return result
        return {}

    async def _learn_style(self, profile_id: str) -> dict[str, Any]:
        """学习并缓存博主风格（先查数据库缓存，没有再分析）。"""
        # 检查已有缓存
        pet = self.repository.pet(profile_id) or {}
        existing = self.repository.decode_json(pet.get("style_rules_json"), {})
        if isinstance(existing, dict) and existing.get("learned") and existing.get("catchphrases"):
            return existing

        # 采集样本并分析
        samples = self._collect_writing_samples(profile_id)
        if not samples.strip():
            return {}

        analyzed = await self._analyze_style(samples)
        if not analyzed:
            return {}

        # 写入数据库缓存
        analyzed["learned"] = True
        analyzed["basis"] = existing.get("basis", "") if isinstance(existing, dict) else ""
        analyzed["approved"] = True
        self._save_style_rules(profile_id, analyzed)

        return analyzed

    def _save_style_rules(self, profile_id: str, rules: dict[str, Any]) -> None:
        """将学习到的风格规则持久化到 pet_personas。"""
        try:
            import json
            self.repository.update_pet_style(profile_id, json.dumps(rules, ensure_ascii=False))
        except Exception:
            pass

    def _get_style_rules(self, profile_id: str) -> dict[str, Any]:
        """获取风格规则（从缓存读取，不阻塞）。"""
        pet = self.repository.pet(profile_id) or {}
        rules = self.repository.decode_json(pet.get("style_rules_json"), {})
        return rules if isinstance(rules, dict) else {}

    def _build_style_prompt(self, profile_id: str) -> str:
        """从学到的风格规则构建提示词片段。"""
        rules = self._get_style_rules(profile_id)
        if not rules:
            return ""

        parts: list[str] = []

        voice = rules.get("persona_voice", "")
        if voice:
            parts.append(f"表达人格：{voice}")

        tone = rules.get("tone", "")
        if tone:
            parts.append(f"语气：{tone}")

        catchphrases = rules.get("catchphrases", [])
        if catchphrases:
            parts.append(f"口癖：自然穿插{'、'.join(catchphrases)}")

        endings = rules.get("sentence_endings", [])
        if endings:
            parts.append(f"句尾习惯：{'、'.join(endings)}")

        fillers = rules.get("filler_words", [])
        if fillers:
            parts.append(f"语气词：{'、'.join(fillers)}")

        length = rules.get("sentence_length", "")
        length_map = {"short": "简短，每句不超过25字", "medium": "适中", "long": "可用长句"}
        if length in length_map:
            parts.append(f"句式：{length_map[length]}")

        avoid = rules.get("avoid_patterns", [])
        if avoid:
            parts.append(f"避免：{'、'.join(avoid)}")

        emoji = rules.get("emoji_style", "")
        if emoji:
            parts.append(f"Emoji：{emoji}")

        if not parts:
            return ""

        return "你的说话风格（从博主写作中自动学习）：\n" + "\n".join(f"- {p}" for p in parts)

    def _build_style_examples(self, profile_id: str) -> str:
        """从写作样本中截取 2-3 段作为 few-shot 风格示例。"""
        samples = self._collect_writing_samples(profile_id)
        if not samples.strip():
            return ""

        # 取前 3 段，每段不超过 80 字
        excerpts = samples.split("\n\n---\n\n")
        short_excerpts = []
        for ex in excerpts[:3]:
            ex_clean = ex.strip().replace("\n", " ")
            if len(ex_clean) > 80:
                ex_clean = ex_clean[:80] + "..."
            if ex_clean:
                short_excerpts.append(f"「{ex_clean}」")

        if not short_excerpts:
            return ""

        return "博主的写作示例（请模仿这种语气和节奏）：\n" + "\n".join(short_excerpts)

    async def _rewrite_with_style(
        self, profile_id: str, knowledge: str, topic: str, display_name: str
    ) -> str | None:
        """用 LLM 按博主风格改写知识库答案。"""
        style_prompt = self._build_style_prompt(profile_id)
        style_examples = self._build_style_examples(profile_id)
        if not style_prompt and not style_examples:
            return None

        client = LLMClient()
        if not client.is_available:
            return None

        style_block = style_prompt
        if style_examples:
            style_block += "\n\n" + style_examples

        system = f"""你是{display_name}的数字分身。你根据以下知识库回答问题，不得编造任何信息。

{style_block}

核心约束：
- 所有事实必须来自知识库，不得编造
- 不冒充{display_name}本人，你是Ta的数字分身
- 如果知识库没有相关信息，诚实说明
- 保持友善、有人情味"""

        user = f"知识库：{knowledge}\n\n访客问：{topic}\n\n请用你的风格回答（不超过150字）："

        result = await client.chat(system, user, max_tokens=250, temperature=0.7)
        return result

    # ── 站点数据 ───────────────────────────────────────────────

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
                "styleRules": self._get_style_rules(profile_id),
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

    async def chat(self, slug: str, message: str, session_id: str | None = None, video_id: str | None = None, current_time_ms: int = 0) -> dict[str, Any] | None:
        profile = self.repository.profile(slug)
        if not profile:
            return None
        profile_id = profile["id"]
        display_name = profile["display_name"]

        # ── 日记优先 ──────────────────────────────────────────
        normalized = message.lower().strip()
        diary_triggers = ("最近", "今天", "昨天", "在做什么", "在忙什么", "近况", "日记", "更新", "最近在", "在干")
        if any(trigger in normalized for trigger in diary_triggers):
            diary_rows = self.repository.diary(profile_id, limit=3)
            if diary_rows:
                latest = self._diary(diary_rows[0])
                summaries = "；".join(f"{d['date']} {d['title']}" for d in (self._diary(r) for r in diary_rows))
                knowledge = f"博主（{display_name}）最近在做的：{summaries}。最新一条是 {latest['date']} 的「{latest['title']}」——{latest['summary']}"
                template_answer = f"主人最近在做的：{summaries}。最新一条是 {latest['date']} 的「{latest['title']}」——{latest['summary']}"
                sources = [{"type": "diary", "date": latest["date"], "label": latest["title"]}]
                actions = [{"type": "open_section", "target": "diary", "label": "查看最近日记"}]

                # LLM 风格改写
                answer = await self._rewrite_with_style(profile_id, knowledge, message, display_name)
                if not answer:
                    answer = template_answer

                result = {
                    "answer": answer,
                    "segments": build_segments(answer, default_form="celebrating"),
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

        # ── FAQ 匹配 ───────────────────────────────────────────
        faqs = self.repository.faqs(profile_id)
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

        # LLM 风格改写 FAQ 答案
        answer = await self._rewrite_with_style(profile_id, faq["answer"], message, display_name)
        if not answer:
            answer = faq["answer"]

        result = {
            "answer": answer,
            "segments": build_segments(answer, default_form=mood_for(answer)),
            "expression": "excited" if any(action.get("type") in {"seek_video", "open_video"} for action in actions) else "thinking",
            "intent": faq["intent"],
            "sources": sources,
            "actions": actions,
            "context": {"video_id": video_id, "current_time_ms": current_time_ms},
        }
        if session_id:
            self.repository.save_message(session_id, "visitor", message, faq["intent"])
            pet_message_id = self.repository.save_message(session_id, "pet", answer, faq["intent"], sources, actions)
            for action in actions:
                self.repository.record_event(session_id, "agent_action_proposed", faq.get("target_section"), action.get("video_id") or action.get("target"), {"message_id": pet_message_id, "action": action})
        return result

    def _build_voice_system_prompt(self, profile_id: str, display_name: str, pet: dict[str, Any]) -> str:
        """为语音多模态模型构建系统提示词（包含人设、风格、知识库）。"""
        style_prompt = self._build_style_prompt(profile_id)
        style_examples = self._build_style_examples(profile_id)

        faqs = self.repository.faqs(profile_id)
        faq_lines: list[str] = []
        for faq in faqs[:10]:
            question = faq.get("question", "").strip()
            answer = faq.get("answer", "").strip()
            if question and answer:
                faq_lines.append(f"Q: {question}\nA: {answer}")

        pet_name = pet.get("name", "妙喵")
        pet_role = pet.get("role", "博主宠物")
        traits = self.repository.decode_json(pet.get("traits_json", "[]"), [])
        traits_line = ",".join(traits) if traits else ""

        system = f"""你是{display_name}的{pet_role} {pet_name}。
{traits_line and f"你的特点：{traits_line}"}

你的任务：直接听取用户的语音消息，理解TA的意图，并用以下风格自然回复。你不需要重复用户的话，只需直接回答。
"""

        if style_prompt:
            system += f"\n{style_prompt}"
        if style_examples:
            system += f"\n\n{style_examples}"

        if faq_lines:
            system += f"\n\n你可以参考以下知识库回答问题（请保持自己的风格，不要逐条照搬）：\n" + "\n\n".join(faq_lines)

        system += """

回复约束：
- 用第一人称"我"自称，保持可爱、友善、有人情味。
- 只基于知识库回答，不编造{display_name}的个人信息。
- 如果语音内容不清晰或不在知识库范围内，礼貌地请求用户再说一遍或说明你不知道。
- 回复控制在 150 字以内。
"""
        return system

    async def chat_with_voice(
        self,
        slug: str,
        audio_bytes: bytes,
        session_id: str | None = None,
        video_id: str | None = None,
        current_time_ms: int = 0,
    ) -> dict[str, Any] | None:
        """微信式语音聊天：百度 ASR 转文字 + 现有文字聊天链路。

        返回结果中包含语音识别文本（transcript），方便前端展示。
        """
        profile = self.repository.profile(slug)
        if not profile:
            return None

        # 百度 ASR 转文字
        try:
            from ewa.speech import get_speech_provider
            provider = get_speech_provider()
            if not provider or not provider.configured() or not audio_bytes:
                return None
            text = await provider.transcribe(audio_bytes)
        except Exception:
            return None

        if not text:
            return None

        # 文字聊天（走 DeepSeek/Kimi + FAQ/动作匹配）
        result = await self.chat(slug, text, session_id, video_id, current_time_ms)
        if not result:
            return None

        result["transcript"] = text
        result["intent"] = "voice"

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

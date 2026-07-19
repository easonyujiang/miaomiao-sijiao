from __future__ import annotations

import re
import time
from typing import Any

from ewa.llm import LLMClient

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

    @staticmethod
    def _is_video_query(message: str) -> bool:
        """判断用户是否在询问某条视频/内容讲了什么（关键词快路径）。

        注意保持高精度：裸"内容/介绍/是什么"这类词误触发面太大，
        没命中时会走 _classify_intent 的 LLM 兜底分类，不怕漏。
        """
        normalized = message.lower().strip()
        query_triggers = {
            "讲了什么", "关于什么", "主要内容", "讲什么", "说了什么", "讲了啥", "说了啥",
            "讲的什么", "讲的啥", "什么内容", "什么看法", "怎么看", "怎么理解",
            "什么观点", "如何评价", "总结一下", "概括一下", "梳理一下",
        }
        return any(t in normalized for t in query_triggers)

    async def _classify_intent(self, message: str, video_id: str | None) -> str:
        """关键词未命中时，用 LLM 做意图分类。

        返回 "video_query" / "diary" / "community" / "other"。LLM 不可用时返回 "other"，
        调用方自然回落到 FAQ 分支。
        """
        client = LLMClient()
        if not client.is_available:
            return "other"

        system = """你是意图分类器。判断用户消息的意图，只输出 JSON。
意图定义：
- video_query：想了解某个视频的内容、讲了什么、看法、评价、观点、总结
- diary：想问博主最近在做什么、近况、动态、日记
- community：想找网站上的相关讨论、帖子、社区话题
- other：其他（问候、关于博主本人、项目、联系方式等）
只输出：{"intent": "video_query|diary|community|other"}"""

        context = f"\n（用户当前正在观看视频：{video_id}）" if video_id else ""
        result = await client.chat_json(system, f"用户消息：{message}{context}", max_tokens=40, timeout=8)
        intent = (result or {}).get("intent", "other")
        return intent if intent in {"video_query", "diary", "community", "other"} else "other"

    @staticmethod
    def _is_community_query(message: str) -> bool:
        """判断用户是否在找网站上的讨论/帖子（关键词快路径）。"""
        triggers = ("相关讨论", "的讨论", "帖子", "社区", "有人聊", "讨论区")
        return any(t in message for t in triggers)

    @staticmethod
    def _extract_first_time_ms(text: str) -> int | None:
        """从文本中提取第一个 [mm:ss] 时间戳，返回毫秒。"""
        m = re.search(r"\[(\d{1,3}):(\d{2})\]", text)
        if not m:
            return None
        return (int(m.group(1)) * 60 + int(m.group(2))) * 1000

    @staticmethod
    def _extract_video_keyword(message: str) -> str | None:
        """从消息中提取用于视频模糊查询的关键字。"""
        # 优先提取 BV 号
        m = re.search(r"\bBV[A-Za-z0-9]{8,12}\b", message)
        if m:
            return m.group(0).upper()

        # 去掉常见问句前缀/后缀
        text = message.strip()
        prefixes = ["妙喵", "请问", "问一下", "我想知道", "告诉我", "帮我查"]
        for prefix in prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()

        text = re.sub(r"[？?！!。]+\s*$", "", text)

        # 去掉触发词和通用词（保留可能的标题/ID 片段）
        noise_phrases = [
            "讲了什么", "关于什么", "主要内容", "讲什么", "说了什么", "是什么",
            "这个视频", "那期视频", "这期视频", "视频", "内容", "讲了啥", "说了啥",
            "介绍一下", "给我讲", "跟我说", "描述一下", "概括一下", "总结一下",
            "你有什么看法", "什么看法", "你怎么看", "怎么看", "怎么理解", "你觉得",
            "如何评价", "评价一下", "什么观点", "的观点", "聊聊", "讲讲", "梳理一下",
            "有没有相关", "相关讨论", "的讨论", "讨论区", "讨论", "帖子", "社区",
            "有人聊过", "有人聊", "有没有", "关于",
        ]
        for phrase in noise_phrases:
            text = text.replace(phrase, "")

        text = re.sub(r"\s+", "", text)
        return text if text else None

    async def _summarize_video(
        self, profile_id: str, video: dict[str, Any], message: str, display_name: str
    ) -> str | None:
        """用 LLM 对视频字幕做摘要，回答用户问题。"""
        subtitle_text = self.repository.get_subtitle_text(video["id"])
        if not subtitle_text:
            return None

        style_prompt = self._build_style_prompt(profile_id)
        style_examples = self._build_style_examples(profile_id)
        style_block = style_prompt
        if style_examples:
            style_block += "\n\n" + style_examples

        client = LLMClient()
        if not client.is_available:
            return f"视频《{video['title']}》的字幕内容已有记录，但当前 LLM 服务不可用，无法生成摘要。"

        system = f"""你是{display_name}的数字分身妙喵。请根据下面的视频字幕，回答用户关于该视频内容的问题。
{style_block}

核心约束（必须严格遵守）：
- 只允许使用字幕里实际出现的信息，禁止编造字幕外的人物、案例、数据
- 字幕每行开头是真实时间戳 [mm:ss]，引用具体片段时必须使用这些时间戳，禁止虚构时间点
- 回答中至少引用一个 [mm:ss] 时间戳（挑最关键的知识点位置），方便用户点击跳转
- 用户问"看法/观点/评价"时，基于字幕实际讲到的内容表达，不要引入字幕外的例子
- 保持简洁、口语化、有博主个人色彩，像博主本人在聊天，不要写成百科词条
- 如果用户问题在字幕里没有答案，诚实说明
- 控制在 200 字以内"""

        user = f"""视频标题：{video['title']}
视频简介：{video.get('description') or video.get('summary', '')}

字幕内容（[mm:ss] 为真实时间戳）：
{subtitle_text[:5000]}

用户问：{message}

请回答："""

        return await client.chat(system, user, max_tokens=300, temperature=0.6)

    async def _answer_video_query(
        self,
        profile_id: str,
        display_name: str,
        message: str,
        session_id: str | None = None,
        video_id: str | None = None,
        current_time_ms: int = 0,
    ) -> dict[str, Any] | None:
        """处理视频模糊查询。"""
        keyword = self._extract_video_keyword(message)
        if keyword:
            candidates = self.repository.search_videos(profile_id, keyword, limit=5)
        elif video_id:
            # 没提取到关键词但带着当前视频上下文（如"这个视频讲了什么"）：直接总结当前视频
            current = self.repository.video(video_id)
            candidates = [current] if current else []
        else:
            return None
        if not candidates:
            return None

        # 如果当前视频在候选列表中，优先用它回答
        target = next((v for v in candidates if v["id"] == video_id), candidates[0])
        answer = await self._summarize_video(profile_id, target, message, display_name)
        if not answer:
            return {
                "answer": f"抱歉，我找到了视频《{target['title']}》，但还没有它的字幕，没法回答内容。",
                "expression": "confused",
                "intent": "video_query",
                "sources": [{"type": "video", "video_id": target["id"], "label": target["title"]}],
                "actions": [{"type": "seek_video", "video_id": target["id"], "time_ms": 0, "label": "▶ 跳转到视频"}],
                "context": {"video_id": video_id, "current_time_ms": current_time_ms},
            }

        # 摘要里引用的第一个 [mm:ss] 作为跳转目标，让按钮落到具体知识点
        seek_ms = self._extract_first_time_ms(answer) or 0
        sources = [{"type": "video", "video_id": target["id"], "label": target["title"]}]
        jump_label = f"▶ 跳到 {seek_ms // 60000}:{seek_ms // 1000 % 60:02d}" if seek_ms else "▶ 跳转到视频"
        actions = [{"type": "seek_video", "video_id": target["id"], "time_ms": seek_ms, "label": jump_label}]

        if len(candidates) > 1:
            # 如果匹配到多个，追加相关推荐动作
            for v in candidates[1:3]:
                actions.append({"type": "seek_video", "video_id": v["id"], "time_ms": 0, "label": f"相关：{v['title']}"})

        result = {
            "answer": answer,
            "expression": "excited",
            "intent": "video_query",
            "sources": sources,
            "actions": actions,
            "context": {"video_id": video_id, "current_time_ms": current_time_ms},
        }
        if session_id:
            self.repository.save_message(session_id, "visitor", message, "video_query")
            self.repository.save_message(session_id, "pet", answer, "video_query", sources, actions)
        return result

    async def _answer_community_query(
        self,
        profile_id: str,
        display_name: str,
        message: str,
        session_id: str | None = None,
        video_id: str | None = None,
        current_time_ms: int = 0,
    ) -> dict[str, Any] | None:
        """处理"有没有相关讨论/帖子"：检索社区话题并给出跳转按钮。"""
        keyword = self._extract_video_keyword(message)
        if not keyword or len(keyword) < 2:
            return None

        topics = self.repository.search_community_topics(profile_id, keyword, limit=3)
        if not topics:
            return None

        topic_lines = "；".join(f"《{t['title']}》（{t['reply_count']} 条回复）" for t in topics)
        knowledge = f"网站社区里与用户问题相关的讨论有：{topic_lines}。"
        answer = await self._rewrite_with_style(profile_id, knowledge, message, display_name)
        if not answer:
            answer = f"喵～帮你找到了 {len(topics)} 条相关讨论：{topic_lines}。点下面按钮直达帖子～"

        actions = [
            {"type": "open_topic", "topic_id": t["id"], "label": f"💬 {t['title'][:12]}"}
            for t in topics
        ]
        actions.append({"type": "open_section", "target": "community", "label": "查看全部讨论"})

        result = {
            "answer": answer,
            "expression": "excited",
            "intent": "community",
            "sources": [{"type": "topic", "topic_id": t["id"], "label": t["title"]} for t in topics],
            "actions": actions,
            "context": {"video_id": video_id, "current_time_ms": current_time_ms},
        }
        if session_id:
            self.repository.save_message(session_id, "visitor", message, "community")
            self.repository.save_message(session_id, "pet", answer, "community", result["sources"], actions)
        return result

    async def chat(self, slug: str, message: str, session_id: str | None = None, video_id: str | None = None, current_time_ms: int = 0) -> dict[str, Any] | None:
        profile = self.repository.profile(slug)
        if not profile:
            return None
        profile_id = profile["id"]
        display_name = profile["display_name"]

        # ── 意图判断：关键词快路径 + LLM 兜底分类 ───────────────
        normalized = message.lower().strip()
        diary_triggers = ("最近", "今天", "昨天", "在做什么", "在忙什么", "近况", "日记", "更新", "最近在", "在干")
        is_diary_keyword = any(trigger in normalized for trigger in diary_triggers)

        if self._is_video_query(message):
            intent = "video_query"
        elif is_diary_keyword:
            intent = "diary"
        elif self._is_community_query(message):
            intent = "community"
        else:
            intent = await self._classify_intent(message, video_id)

        # ── 视频模糊查询 ────────────────────────────────────────
        if intent == "video_query":
            video_result = await self._answer_video_query(
                profile_id, display_name, message, session_id, video_id, current_time_ms
            )
            if video_result:
                return video_result

        # ── 社区讨论检索 ────────────────────────────────────────
        if intent == "community":
            community_result = await self._answer_community_query(
                profile_id, display_name, message, session_id, video_id, current_time_ms
            )
            if community_result:
                return community_result

        # ── 日记优先 ──────────────────────────────────────────
        if is_diary_keyword or intent == "diary":
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

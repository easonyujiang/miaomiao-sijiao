from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Iterable


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _decode(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


class SiteRepository:
    """SQLite repository for the creator site.

    Connections are short-lived so FastAPI requests can safely use the repository
    without sharing sqlite connection objects across worker threads.
    """

    def __init__(self, db_path: Path, schema_path: Path):
        self.db_path = db_path
        self.schema_path = schema_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        schema = self.schema_path.read_text(encoding="utf-8")
        with self._connect() as connection:
            connection.executescript(schema)
            self._ensure_columns(connection)
            self._seed(connection)

    @staticmethod
    def _ensure_columns(connection: sqlite3.Connection) -> None:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(faqs)")}
        if "sources_json" not in columns:
            connection.execute("ALTER TABLE faqs ADD COLUMN sources_json TEXT NOT NULL DEFAULT '[]'")
        if "actions_json" not in columns:
            connection.execute("ALTER TABLE faqs ADD COLUMN actions_json TEXT NOT NULL DEFAULT '[]'")

    def _seed(self, connection: sqlite3.Connection) -> None:
        profile = (
            "profile_ashley",
            "ashley",
            "钟笑咪",
            "ZXM",
            "AI 应用开发者 · 校园创业者 · 黑客松组织者 · 创作者",
            "浙江 · 宁波",
            "宁波大学阳明学院 · 大一升大二 · 暑假北京实习准备中",
            "写代码，也写故事；做产品，也做梦。",
            "我是钟笑咪。白天写代码、做 Agent。我相信文字、影像和代码都是同一种东西——把转瞬即逝的瞬间留下来。所以这个网站不只是一张名片，也是一本一直在写的日记：今天在做什么、想了什么、看见了什么风。我把它们都放在自己手里，因为记忆要握在自己手里，才不会被时间偷走。",
            _json(["AI Agent", "视频重构", "创作者工具", "Flutter", "AI 黑客松", "校园创业"]),
        )
        connection.execute(
            """
            INSERT INTO profiles
              (id, slug, display_name, initials, role, location, status, tagline, summary, tags_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              display_name=excluded.display_name, initials=excluded.initials,
              role=excluded.role, location=excluded.location, status=excluded.status,
              tagline=excluded.tagline, summary=excluded.summary, tags_json=excluded.tags_json,
              updated_at=CURRENT_TIMESTAMP
            """,
            profile,
        )

        connection.execute(
            """
            INSERT INTO pet_personas
              (id, profile_id, name, role, greeting, traits_json, style_rules_json, safety_rules_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name, role=excluded.role, greeting=excluded.greeting,
              traits_json=excluded.traits_json, style_rules_json=excluded.style_rules_json,
              safety_rules_json=excluded.safety_rules_json, updated_at=CURRENT_TIMESTAMP
            """,
            (
                "pet_miaomiao",
                "profile_ashley",
                "妙喵",
                "博主宠物、视频私教与内容向导",
                "你好，我是妙喵，笑咪的数字分身。你可以问主人是谁，也可以直接问某条视频讲了什么、最近在忙什么，我会带你跳到对应片段。",
                _json(["有博主个人色彩", "先回答再带路", "能定位视频片段", "不冒充本人", "只使用有依据资料", "记得主人最近在做什么"]),
                _json({"basis": "直接、重视实际复用、用具体场景解释抽象想法、相信记忆要握在自己手里"}),
                _json({"no_impersonation": True, "public_sources_only": True, "admit_unknown": True}),
            ),
        )

        projects = [
            (
                "miaomiao-creator-agent", "profile_ashley", "miaomiao-creator-agent",
                "妙喵：博主与粉丝的互动 Agent", "抖音黑客松当前方案",
                "把博主的视频库、公开信息与表达风格做成一只宠物 Agent。它既能陪聊，也能教学、推荐其他视频，并把播放器拉到准确片段。",
                "个人网站是首个验证端点，最终形态是可复用到不同视频博主的互动站与平台能力。",
                _json(["博主 Agent", "粉丝互动", "视频 RAG", "时间轴工具"]), 1, 1,
            ),
            (
                "ai-tutorial-demo", "profile_ashley", "ai-tutorial-demo", "AI 教程助手 (a-igent)",
                "已完成 Demo 闭环",
                "输入教程视频链接，自动完成关键帧抽取、AI 步骤解析，并在 Android 真机通过悬浮层和无障碍能力逐步引导操作。",
                "已验证“视频 → 结构化步骤 → 悬浮引导 → 用户操作确认”；OCR 后端已具备，前端精确定位仍待接入。",
                _json(["Flutter", "FastAPI", "OpenAI Vision", "EasyOCR"]), 1, 2,
            ),
            (
                "cline-memory-hub", "profile_ashley", "cline-memory-hub", "Cline 跨平台 AI 记忆中枢",
                "已上线运行",
                "跨 Trae/Claude/Codex/Cline/Cursor 多个 AI 平台的共享记忆系统，自部署在阿里云 ECS，通过 API 让不同 Agent 读写同一份记忆。",
                "本地快照 + 云端 SQLite 双层存储，自动同步脚本每 2 小时回写，已积累 68 个记忆文件、2.21MB。",
                _json(["Node.js", "阿里云 ECS", "SQLite", "多 Agent"]), 1, 4,
            ),
            (
                "xianshu-game", "profile_ashley", "xianshu-game", "《献书》· 东晋历史 AI 互动叙事游戏",
                "MVP 完成",
                "东晋历史题材 AI 互动叙事游戏，包含 40+ AI 视频片段、11 种结局、30+ 交互节点。",
                "用 AI 视频生成 + 分支叙事结构还原历史场景，玩家选择决定人物命运走向。",
                _json(["AI 视频生成", "互动叙事", "历史题材", "RunwayML"]), 1, 5,
            ),
            (
                "subnet-darkflow", "profile_ashley", "subnet-darkflow", "Subnet：暗流",
                "游戏设计完成",
                "基于 Bittensor 的非完全信息博弈策略游戏，玩家在去中心化网络中争夺算子与信任。",
                "已完成游戏机制设计与博弈树分析，进入原型实现阶段。",
                _json(["Bittensor", "策略博弈", "非完全信息", "游戏设计"]), 0, 6,
            ),
            (
                "song-zhiqiu", "profile_ashley", "song-zhiqiu", "宋知秋 · 人物创作",
                "持续创作",
                "梦中少女宋知秋的人物设定、剧本、分镜与 AI 立绘，是笑咪的创作核心与精神镜像。",
                "用 AI 立绘、剧本与互动游戏构建人物，对抗遗忘、保存记忆。",
                _json(["AI 立绘", "人物设定", "剧本", "分镜"]), 0, 7,
            ),
            (
                "ningbo-hackathon", "profile_ashley", "ningbo-hackathon", "宁波企业定制化 AI 黑客松大赛",
                "发起人 & 执行方负责人",
                "面向宁波企业的定制化 AI 黑客松大赛，作为发起人和执行方负责人统筹全流程。",
                "覆盖赛题设计、参赛招募、技术导师、评审与落地对接。",
                _json(["黑客松组织", "执行方", "AI 赛事", "宁波"]), 0, 8,
            ),
            (
                "aigc-workshop", "profile_ashley", "aigc-workshop", "AIGC Workshop 课程体系",
                "合作中",
                "与刺猬星球平台合作的 AIGC 课程体系，从入门到实战的完整教学路径。",
                "覆盖提示词、AI 视频、AI 应用开发等多个主题模块。",
                _json(["AIGC 课程", "刺猬星球", "教学体系"]), 0, 9,
            ),
            (
                "emerge-community", "profile_ashley", "emerge-community", "Emerge甬现 · 高校 AI 创新社群",
                "运营中",
                "运营面向高校学生的 AI 创新社群，组织分享、共学和项目孵化。",
                "持续招募与共学活动，连接校园与产业。",
                _json(["高校社群", "AI 共学", "宁波大学", "运营"]), 0, 10,
            ),
            (
                "vibe-ppt", "profile_ashley", "vibe-ppt", "vibe_ppt · AI PPT 自动生成",
                "MVP 完成",
                "通过提示词与模板自动生成 PPT 的工具，覆盖选题、大纲、配图与排版。",
                "已能根据主题一次性产出可演示的初稿。",
                _json(["AI 生成", "PPT", "提示词", "模板"]), 0, 11,
            ),
            (
                "resume-parser", "profile_ashley", "resume-parser", "猎头简历智能解析系统",
                "MVP 完成",
                "基于 LLM 的猎头简历解析系统，从非结构化简历抽取结构化字段并打分。",
                "已能识别教育、经历、技能等核心字段并输出结构化结果。",
                _json(["LLM", "简历解析", "结构化抽取"]), 0, 12,
            ),
        ]
        connection.executemany(
            """
            INSERT INTO projects
              (id, profile_id, slug, name, stage, summary, body, tags_json, is_featured, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name, stage=excluded.stage, summary=excluded.summary,
              body=excluded.body, tags_json=excluded.tags_json,
              is_featured=excluded.is_featured, sort_order=excluded.sort_order,
              updated_at=CURRENT_TIMESTAMP
            """,
            projects,
        )

        sources = [
            ("source_tech_pdf", "document", "AI Tutorial Demo 技术说明文档", "assets/a-igent/tech-doc.pdf", "indexed", "已提取架构、视频理解、OCR、悬浮层和能力边界。"),
            ("source_intro_pdf", "document", "AI 教程助手项目名称与简介", "assets/a-igent/project-intro.pdf", "indexed", "确认早期定位、目标人群和教程执行化体验。"),
            ("source_demo_video", "video", "关闭设备动作方向权限演示", "assets/a-igent/demo.mp4", "indexed", "26.8 秒竖屏演示，已切成六个时间片段。"),
            ("source_direction", "transcript", "视频信息转化及 AI 应用方向讨论", "本次对话提供的微信录音文字稿", "indexed", "端点验证、博主宠物、视频私教和粉丝对话方向。"),
            ("source_tracks", "document", "抖音精选赛题信息", "本次对话提供的赛题原文", "indexed", "以赛道二内容重构为主。"),
            ("source_zero", "website", "zero-to-website-psi.vercel.app", "https://zero-to-website-psi.vercel.app/", "reference_only", "当前环境无法连接，未把内容写入事实库。"),
        ]
        connection.executemany(
            """
            INSERT INTO knowledge_sources
              (id, profile_id, source_type, title, location, ingest_status, metadata_json)
            VALUES (?, 'profile_ashley', ?, ?, ?, ?, json_object('summary', ?))
            ON CONFLICT(id) DO UPDATE SET
              title=excluded.title, location=excluded.location,
              ingest_status=excluded.ingest_status, metadata_json=excluded.metadata_json,
              updated_at=CURRENT_TIMESTAMP
            """,
            sources,
        )

        videos = [
            (
                "device-motion-permission-demo", "source_demo_video", "local",
                "AI 教程助手：关闭设备动作方向权限",
                "展示 AI 教程助手用悬浮高亮与步骤气泡引导用户关闭设备动作方向权限。",
                "/ai-tutorial-demo.mp4", "assets/a-igent/demo.mp4",
                26817, "manual", _json(["手机教程", "悬浮引导", "五步操作", "端点样例"]),
            ),
            (
                "product-direction-transcript", "source_direction", "transcript",
                "视频信息转化及 AI 应用方向讨论",
                "形成从视频复用、博主数字宠物、一对一私教，到博主与粉丝长期互动站的产品方向。",
                None, None, 0, "manual", _json(["产品决策", "博主分身", "私教", "粉丝互动"]),
            ),
        ]
        connection.executemany(
            """
            INSERT INTO videos
              (id, profile_id, source_id, platform, title, description, source_url, local_ref,
               duration_ms, transcript_status, tags_json)
            VALUES (?, 'profile_ashley', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              title=excluded.title, description=excluded.description, source_url=excluded.source_url,
              local_ref=excluded.local_ref, duration_ms=excluded.duration_ms,
              transcript_status=excluded.transcript_status, tags_json=excluded.tags_json,
              updated_at=CURRENT_TIMESTAMP
            """,
            videos,
        )

        segments = [
            ("s1", "device-motion-permission-demo", 0, 4000, "hook", "选择教程", "在 AI 教程助手中选择解析结果并开始演示。"),
            ("s2", "device-motion-permission-demo", 4000, 9000, "step", "进入隐私保护", "打开手机系统设置中的隐私保护页面。"),
            ("s3", "device-motion-permission-demo", 9000, 14000, "step", "进入其他权限", "向下滑动并点击“其他权限”。"),
            ("s4", "device-motion-permission-demo", 14000, 19000, "step", "打开设备动作权限", "在权限列表中进入“获取设备动作与方向”权限。"),
            ("s5", "device-motion-permission-demo", 19000, 23000, "step", "打开更多菜单", "点击页面右上角的三个点。"),
            ("s6", "device-motion-permission-demo", 23000, 27000, "highlight", "完成关闭", "点击“全部拒绝”，完成操作。"),
            ("d1", "product-direction-transcript", 0, 0, "knowledge", "内容不是总结，而是复用", "目标是把视频信息转为可直接使用的知识与技能。"),
            ("d2", "product-direction-transcript", 0, 0, "knowledge", "对内分析，对外教学", "对创作者是分析师和教练，对粉丝是有人味的老师与生活搭子。"),
            ("d3", "product-direction-transcript", 0, 0, "highlight", "宠物是博主入口", "宠物读取博主授权内容，以博主认可的个人色彩回答并导航视频。"),
        ]
        connection.executemany(
            """
            INSERT INTO video_segments
              (id, video_id, start_ms, end_ms, segment_type, title, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              start_ms=excluded.start_ms, end_ms=excluded.end_ms,
              segment_type=excluded.segment_type, title=excluded.title,
              summary=excluded.summary, updated_at=CURRENT_TIMESTAMP
            """,
            segments,
        )

        faqs = [
            ("faq_who", "你在做什么？", "主人是钟笑咪，宁波大学阳明学院的学生。她在做妙喵：把博主的视频、公开信息和表达风格变成一只可聊天、可教学、可导航视频的宠物 Agent。这个个人网站只是第一阶段验证端点。她最近还在准备暑假北京实习。", "who", "about", ["你是谁", "做什么", "主人", "钟笑咪", "笑咪"], [], [{"type": "open_section", "target": "about", "label": "认识博主"}], 1),
            ("faq_goal", "最终产品是什么？", "最终不是个人简历站，而是每个视频博主都能拥有的互动站。粉丝可以与宠物聊天、围绕视频追问、跳到具体片段，并继续发现博主的其他内容。", "goal", "product-path", ["最终", "产品", "博主", "粉丝"], [], [{"type": "open_section", "target": "product-path", "label": "查看产品路径"}], 2),
            ("faq_permission", "怎么关闭设备动作权限？", "演示视频的路径是：隐私保护 → 其他权限 → 获取设备动作与方向 → 右上角三个点 → 全部拒绝。我可以直接带你到关键步骤。", "permission", "videos", ["权限", "设置", "关闭", "摇一摇", "动作方向"], [{"type": "video_segment", "video_id": "device-motion-permission-demo", "start_ms": 9000, "label": "进入其他权限"}], [{"type": "seek_video", "video_id": "device-motion-permission-demo", "time_ms": 9000, "label": "跳到 0:09"}], 3),
            ("faq_video", "妙喵怎么理解视频？", "视频先被拆成转写、时间片段、步骤、知识点和高光片段。回答时先检索当前视频，再检索博主全量视频库，最后返回答案、依据和播放器动作。", "video", "videos", ["视频", "片段", "进度条", "时间轴", "理解"], [{"type": "video", "video_id": "device-motion-permission-demo", "label": "演示视频"}], [{"type": "open_section", "target": "videos", "label": "查看视频结构"}], 4),
            ("faq_related", "为什么要做博主宠物？", "视频仍是最有吸引力的信息载体，但用户需要的不只是看完，而是直接复用、追问和与内容背后的人建立关系。妙喵把这三件事接在同一个入口里。", "related", "videos", ["为什么", "博主宠物", "数字分身", "关系"], [{"type": "video", "video_id": "product-direction-transcript", "label": "产品讨论文稿"}], [{"type": "open_video", "video_id": "product-direction-transcript", "time_ms": 0, "label": "打开产品讨论"}], 5),
            ("faq_projects", "有哪些已完成项目？", "目前确认的项目包括妙喵博主互动 Agent、已跑通闭环的 AI 教程助手，以及跨平台 AI 记忆中枢。", "project", "projects", ["项目", "作品", "经历", "做过"], [], [{"type": "open_section", "target": "projects", "label": "查看项目"}], 6),
            ("faq_contact", "怎么联系你？", "主人邮箱是 zhongxiaomi06@gmail.com，GitHub 是 zhongxiaomi06-sudo。合作可以发邮件，或在 GitHub 找到她的更多项目。", "contact", "contact", ["联系", "合作", "邮箱", "微信", "github", "邮件"], [], [{"type": "open_section", "target": "contact", "label": "查看联系入口"}], 7),
            ("faq_diary", "最近在做什么？", "主人最近在准备暑假北京实习，同时推进妙喵 Agent 的端点验证。每天的更新她会写在 /diary 里，我可以告诉你最近这几天她在忙什么。", "diary", "diary", ["最近", "今天", "昨天", "在做什么", "在忙什么", "日记", "近况", "更新"], [], [{"type": "open_section", "target": "diary", "label": "查看最近日记"}], 8),
            ("faq_school", "主人在哪个学校？", "主人在宁波大学阳明学院读金融工程，已经转专业成功。目前大一结束即将大二，计划提前一年在 2028 年毕业。", "school", "about", ["学校", "大学", "宁波大学", "阳明学院", "金融工程", "专业"], [], [{"type": "open_section", "target": "about", "label": "认识博主"}], 9),
        ]
        connection.executemany(
            """
            INSERT INTO faqs
              (id, profile_id, question, answer, intent, target_section, keywords_json,
               sources_json, actions_json, sort_order)
            VALUES (?, 'profile_ashley', ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              question=excluded.question, answer=excluded.answer, intent=excluded.intent,
              target_section=excluded.target_section, keywords_json=excluded.keywords_json,
              sources_json=excluded.sources_json, actions_json=excluded.actions_json,
              sort_order=excluded.sort_order, updated_at=CURRENT_TIMESTAMP
            """,
            [(row[0], row[1], row[2], row[3], row[4], _json(row[5]), _json(row[6]), _json(row[7]), row[8]) for row in faqs],
        )

        links = [
            ("link_email", "邮箱", "zhongxiaomi06@gmail.com", "mailto:zhongxiaomi06@gmail.com", "email", 1),
            ("link_github", "GitHub", "zhongxiaomi06-sudo", "https://github.com/zhongxiaomi06-sudo", "social", 2),
            ("link_blog", "数字记忆 Blog", "zhongxiaomi06-sudo.github.io", "https://zhongxiaomi06-sudo.github.io/my-memory/blog/", "website", 3),
        ]
        connection.executemany(
            """
            INSERT INTO profile_links
              (id, profile_id, label, value, url, link_type, sort_order)
            VALUES (?, 'profile_ashley', ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              label=excluded.label, value=excluded.value, url=excluded.url,
              link_type=excluded.link_type, sort_order=excluded.sort_order,
              updated_at=CURRENT_TIMESTAMP
            """,
            links,
        )

        diary_entries = [
            (
                "diary_20260629", "profile_ashley", "2026-06-29",
                "把数字名片跑通，先以自己为端点验证",
                "focused", "多云", "浙江 · 宁波",
                "今天专注把个人网站从静态介绍页升级成持续更新的数字名片，并新增了日记模块。",
                "## 今天在做什么\n\n把数据结构文档完整落地，新增 `diary_entries` 表，让数字名片从静态介绍页变成持续在更新的人。\n\n关键改动：\n- schema 加 `diary_entries` 表与索引\n- 后端 repository/service/api 加 diary CRUD\n- 用真实数据替换 seed 中的占位（姓名、邮箱、学校、12 个项目）\n- 准备加 `/diary` 前端页面\n\n## 为什么\n\n妙喵被问『最近在做什么』时，目前只能回退到 FAQ。有了日记，她可以直接回答『昨天主人在准备北京实习面试』这种问题，让博主不再是一张静态名片，而是『持续在更新的人』。\n\n## 下一步\n\n前端 `/diary` 页面 + 首页时间线片段。",
                _json(["数字名片", "日记模块", "妙喵", "端点验证"]),
                _json([{"type": "project", "id": "miaomiao-creator-agent", "label": "妙喵 Agent"}, {"type": "project", "id": "cline-memory-hub", "label": "Cline 记忆中枢"}]),
                _json(["schema 加 diary_entries 表", "后端 CRUD 完成", "seed 数据真实化"]),
                "public", 1, 1,
            ),
            (
                "diary_20260628", "profile_ashley", "2026-06-28",
                "和 codex 梳理妙喵 Agent 的开发文档与数据结构",
                "excited", "晴", "浙江 · 宁波",
                "和 codex 把赛道二开发文档和数据结构文档重写成个人网站数字名片版，架构围绕我的网站展开。",
                "## 今天在做什么\n\n和 codex 一起重写了两份文档：\n- 《妙喵私教-赛道二开发文档》\n- 《个人网站数字名片-数据结构》\n\n核心收敛：**个人网站只是端点验证，最终产品是为每位视频博主生成一只宠物 Agent**。\n\n三模式共享一只猫：视频问答导览、视频私教、陪聊互动。不做成三个割裂页面。\n\n## 关键决策\n\n- 站里有博主桌宠「妙喵」，承接互动/问答/导流/记忆\n- 沉淀博主全部可展示数据\n- 数据分四层：公开 / 半公开 / 私域 / 受控\n\n## 想法\n\nLee Robinson 风格的个人站 + 桌宠 + 互动区，是真正可跑通的真实结构。",
                _json(["妙喵", "开发文档", "数据结构", "赛道二", "codex"]),
                _json([{"type": "document", "label": "开发文档", "url": "/docs"}, {"type": "project", "id": "miaomiao-creator-agent", "label": "妙喵 Agent"}]),
                _json(["重写两份文档", "确定端点验证路线", "确定四层数据分层"]),
                "public", 0, 2,
            ),
            (
                "diary_20260622", "profile_ashley", "2026-06-22",
                "复习量化金融与 Python，准备北京实习面试",
                "focused", "雨", "浙江 · 宁波",
                "今天主要复习量化金融和 Python/FastAPI，准备即将到来的北京实习面试。",
                "## 今天在做什么\n\n- 上午：复习量化金融基础，重点过 portfolio optimization 和 time series\n- 下午：刷 Python/FastAPI 题，准备实习面试的技术栈补齐\n- 晚上：整理 Cline 记忆中枢的同步脚本\n\n## 想法\n\n短期目标是大二修完全部学分 + 大三字节实习。今天复习的时候意识到，量化金融和 AI 应用开发其实是同一种思维方式——都是在不确定中找模式。\n\nCline 记忆中枢现在已经有 68 个文件，2.21MB，是我跨平台工作的真正底座。",
                _json(["量化金融", "Python", "FastAPI", "北京实习", "面试准备"]),
                _json([{"type": "project", "id": "cline-memory-hub", "label": "Cline 记忆中枢"}]),
                _json(["复习 portfolio optimization", "刷 FastAPI 题", "整理同步脚本"]),
                "public", 0, 3,
            ),
            (
                "diary_20260615", "profile_ashley", "2026-06-15",
                "《献书》互动叙事游戏 MVP 收尾",
                "proud", "晴", "浙江 · 宁波",
                "今天把《献书》的 MVP 收尾，40+ AI 视频片段和 11 种结局全部跑通。",
                "## 今天在做什么\n\n《献书》东晋历史 AI 互动叙事游戏的 MVP 收尾。\n\n- 40+ AI 视频片段全部生成完毕\n- 11 种结局分支验证通过\n- 30+ 交互节点测试稳定\n\n## 想法\n\n用 AI 视频生成还原历史场景，玩家选择决定人物命运走向。这其实和我做妙喵的逻辑是通的——让内容不再只是被看，而是被『复用』和『对话』。\n\n宋知秋也是这条线上的：用 AI 立绘、剧本、互动游戏构建人物，对抗遗忘。**记忆就是一切**。",
                _json(["献书", "AI 视频", "互动叙事", "东晋", "宋知秋"]),
                _json([{"type": "project", "id": "xianshu-game", "label": "《献书》"}, {"type": "project", "id": "song-zhiqiu", "label": "宋知秋"}]),
                _json(["40+ 视频片段完成", "11 种结局验证", "30+ 交互节点测试"]),
                "public", 0, 4,
            ),
            (
                "diary_20260610", "profile_ashley", "2026-06-10",
                "宁波黑客松筹备 + Emerge甬现社群运营",
                "tired", "多云", "浙江 · 宁波大学",
                "今天统筹宁波企业定制化 AI 黑客松的赛题设计，同时运营 Emerge甬现高校社群。",
                "## 今天在做什么\n\n双线工作：\n\n- 上午：宁波企业定制化 AI 黑客松的赛题设计、参赛招募方案\n- 下午：Emerge甬现高校 AI 创新社群的共学活动组织\n- 晚上：和刺猬星球对接 AIGC Workshop 课程内容\n\n## 想法\n\n作为发起人和执行方负责人统筹黑客松，覆盖赛题设计、参赛招募、技术导师、评审与落地对接——这是真正的项目执行训练。\n\n社群运营让我更理解『创作者需要什么』，这其实是妙喵 Agent 的真实需求来源。",
                _json(["黑客松", "Emerge甬现", "社群运营", "AIGC Workshop", "宁波大学"]),
                _json([{"type": "project", "id": "ningbo-hackathon", "label": "宁波黑客松"}, {"type": "project", "id": "emerge-community", "label": "Emerge甬现"}, {"type": "project", "id": "aigc-workshop", "label": "AIGC Workshop"}]),
                _json(["赛题设计完成", "共学活动组织", "刺猬星球对接"]),
                "public", 0, 5,
            ),
            (
                "diary_20260601", "profile_ashley", "2026-06-01",
                "转专业成功，金融工程，目标 2028 提前毕业",
                "proud", "晴", "浙江 · 宁波大学",
                "今天确认转专业到金融工程成功，下一步是大二修完全部学分，目标 2028 年提前一年毕业。",
                "## 今天在做什么\n\n- 上午：办理转专业手续，确认进入金融工程\n- 下午：规划大二课程，目标修完全部学分\n- 晚上：更新数字记忆 about.json\n\n## 关键决策\n\n短期：北京实习面试准备 + 技术栈补齐\n中期：大二修完全部学分 + 大三字节实习\n长期：大学毕业创业 → 援助非洲\n\n## 想法\n\n转专业到金融工程，是因为它和量化、和 AI 都是『在不确定中找模式』。提前一年毕业是为了把时间留给真正重要的事——创业和创造。\n\n记忆要握在自己手里。GitHub 私有仓库 + 本地 clone，才是我自己的。",
                _json(["转专业", "金融工程", "宁波大学", "提前毕业", "2028"]),
                _json([{"type": "project", "id": "emerge-community", "label": "Emerge甬现"}]),
                _json(["转专业成功", "大二课程规划", "更新 about.json"]),
                "public", 0, 6,
            ),
        ]
        connection.executemany(
            """
            INSERT INTO diary_entries
              (id, profile_id, entry_date, title, mood, weather, location, summary, body,
               tags_json, links_json, highlights_json, visibility, is_pinned, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              title=excluded.title, mood=excluded.mood, weather=excluded.weather,
              location=excluded.location, summary=excluded.summary, body=excluded.body,
              tags_json=excluded.tags_json, links_json=excluded.links_json,
              highlights_json=excluded.highlights_json, is_pinned=excluded.is_pinned,
              sort_order=excluded.sort_order, updated_at=CURRENT_TIMESTAMP
            """,
            diary_entries,
        )

    def _fetch_all(self, query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(query, tuple(params)).fetchall()]

    def _fetch_one(self, query: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(query, tuple(params)).fetchone()
            return dict(row) if row else None

    def profile(self, slug: str) -> dict[str, Any] | None:
        return self._fetch_one("SELECT * FROM profiles WHERE slug = ?", (slug,))

    def profile_by_id(self, profile_id: str) -> dict[str, Any] | None:
        return self._fetch_one("SELECT * FROM profiles WHERE id = ?", (profile_id,))

    def pet(self, profile_id: str) -> dict[str, Any] | None:
        return self._fetch_one("SELECT * FROM pet_personas WHERE profile_id = ? AND is_active = 1", (profile_id,))

    def update_pet_style(self, profile_id: str, style_rules_json: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE pet_personas SET style_rules_json = ?, updated_at = CURRENT_TIMESTAMP WHERE profile_id = ?",
                (style_rules_json, profile_id),
            )

    def projects(self, profile_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("SELECT * FROM projects WHERE profile_id = ? AND visibility = 'public' ORDER BY is_featured DESC, sort_order", (profile_id,))

    def diary(self, profile_id: str, limit: int = 30, offset: int = 0) -> list[dict[str, Any]]:
        return self._fetch_all(
            "SELECT * FROM diary_entries WHERE profile_id = ? AND visibility = 'public' ORDER BY is_pinned DESC, entry_date DESC, sort_order ASC LIMIT ? OFFSET ?",
            (profile_id, limit, offset),
        )

    def diary_by_date(self, profile_id: str, entry_date: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "SELECT * FROM diary_entries WHERE profile_id = ? AND entry_date = ? AND visibility = 'public'",
            (profile_id, entry_date),
        )

    def faqs(self, profile_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("SELECT * FROM faqs WHERE profile_id = ? AND visibility = 'public' ORDER BY sort_order", (profile_id,))

    def links(self, profile_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("SELECT * FROM profile_links WHERE profile_id = ? AND visibility = 'public' ORDER BY sort_order", (profile_id,))

    def sources(self, profile_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("SELECT * FROM knowledge_sources WHERE profile_id = ? ORDER BY created_at", (profile_id,))

    def videos(self, profile_id: str) -> list[dict[str, Any]]:
        videos = self._fetch_all("SELECT * FROM videos WHERE profile_id = ? AND visibility = 'public' ORDER BY created_at", (profile_id,))
        for video in videos:
            video["segments"] = self._fetch_all("SELECT * FROM video_segments WHERE video_id = ? ORDER BY start_ms, id", (video["id"],))
        return videos

    def video(self, video_id: str) -> dict[str, Any] | None:
        video = self._fetch_one("SELECT * FROM videos WHERE id = ? AND visibility = 'public'", (video_id,))
        if video:
            video["segments"] = self._fetch_all("SELECT * FROM video_segments WHERE video_id = ? ORDER BY start_ms, id", (video_id,))
        return video

    def create_session(self, slug: str, anonymous_key: str, source: str, landing_path: str) -> dict[str, str] | None:
        profile = self.profile(slug)
        if not profile:
            return None
        visitor_id = f"visitor_{uuid.uuid5(uuid.NAMESPACE_URL, anonymous_key).hex}"
        session_id = f"session_{uuid.uuid4().hex}"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO visitors (id, anonymous_key, first_source)
                VALUES (?, ?, ?)
                ON CONFLICT(anonymous_key) DO UPDATE SET last_seen_at=CURRENT_TIMESTAMP
                """,
                (visitor_id, anonymous_key, source),
            )
            connection.execute(
                "INSERT INTO visitor_sessions (id, visitor_id, profile_id, source, landing_path) VALUES (?, ?, ?, ?, ?)",
                (session_id, visitor_id, profile["id"], source, landing_path),
            )
        return {"session_id": session_id, "visitor_id": visitor_id}

    def record_event(self, session_id: str, event_type: str, section_id: str | None, target_id: str | None, payload: dict[str, Any]) -> str:
        event_id = f"event_{uuid.uuid4().hex}"
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO visitor_events (id, session_id, event_type, section_id, target_id, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, session_id, event_type, section_id, target_id, _json(payload)),
            )
        return event_id

    def save_message(self, session_id: str, role: str, content: str, intent: str | None = None, sources: list[Any] | None = None, actions: list[Any] | None = None) -> str:
        message_id = f"message_{uuid.uuid4().hex}"
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversation_messages (id, session_id, role, content, intent, sources_json, actions_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (message_id, session_id, role, content, intent, _json(sources or []), _json(actions or [])),
            )
        return message_id

    def update_progress(self, visitor_id: str, video_id: str, position_ms: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO viewer_video_progress (visitor_id, video_id, last_position_ms)
                VALUES (?, ?, ?)
                ON CONFLICT(visitor_id, video_id) DO UPDATE SET
                  last_position_ms=excluded.last_position_ms, updated_at=CURRENT_TIMESTAMP
                """,
                (visitor_id, video_id, max(0, position_ms)),
            )

    def public_stats(self, profile_id: str) -> dict[str, int]:
        with self._connect() as connection:
            return {
                "videos": connection.execute("SELECT count(*) FROM videos WHERE profile_id = ?", (profile_id,)).fetchone()[0],
                "segments": connection.execute("SELECT count(*) FROM video_segments s JOIN videos v ON v.id=s.video_id WHERE v.profile_id = ?", (profile_id,)).fetchone()[0],
                "projects": connection.execute("SELECT count(*) FROM projects WHERE profile_id = ?", (profile_id,)).fetchone()[0],
                "sources": connection.execute("SELECT count(*) FROM knowledge_sources WHERE profile_id = ?", (profile_id,)).fetchone()[0],
            }

    @staticmethod
    def decode_json(value: str | None, default: Any) -> Any:
        return _decode(value, default)

"""社区种子数据

往 SQLite 社区表写入演示话题和回复。

使用方式:
    python scripts/seed_community.py [--profile profile_ashley]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from pathlib import Path

SEED_TOPICS = [
    {
        "title": "正当防卫的构成要件 — 罗翔刑法精讲",
        "content": "张三深夜回家误伤物业工人，是否构成正当防卫？本视频讲解正当防卫的五个核心要件，配套闯关答题助你掌握知识点。",
        "category": "showcase",
        "author_name": "罗翔说刑法",
        "tags": ["刑法", "正当防卫", "闯关答题"],
    },
    {
        "title": "假想防卫和防卫过当有什么区别？",
        "content": "看完罗翔老师的正当防卫视频后，对假想防卫和防卫过当的概念有些混淆，能详细解释一下两者的区别吗？",
        "category": "question",
        "author_name": "法学萌新",
        "tags": ["刑法", "正当防卫", "假想防卫"],
    },
    {
        "title": "AI Agent 端点验证全流程演示",
        "content": "从视频上传、知识库构建到宠物问答的完整流程展示。包含视频片段导航、FAQ 匹配和 LLM 风格改写三个核心环节。",
        "category": "showcase",
        "author_name": "钟笑咪",
        "tags": ["Agent", "视频 RAG", "妙喵"],
    },
    {
        "title": "视频字幕分段的准确率怎么提高到 92% 的？",
        "content": "看到分享中提到关键帧检测 + OCR 字幕提取 + 转写文本多模态分段，具体是怎么实现的？关键帧检测用的什么算法？",
        "category": "question",
        "author_name": "AI 开发者小林",
        "tags": ["字幕", "多模态", "分段算法"],
    },
    {
        "title": "闯关答题模式对学习效果有帮助吗？",
        "content": "课程闯关答题的设计思路是「看视频 → 答题 → 反馈 → 跳回视频片段」，大家觉得这种学习闭环有效吗？有什么改进建议？",
        "category": "discussion",
        "author_name": "教育技术研究生",
        "tags": ["闯关答题", "学习闭环", "教育技术"],
    },
    {
        "title": "《献书》互动叙事游戏演示",
        "content": "东晋历史题材 AI 互动叙事游戏实机演示，展示 4 个关键选择节点和对应的 AI 生成视频片段。",
        "category": "showcase",
        "author_name": "钟笑咪",
        "tags": ["献书", "AI 视频", "互动叙事"],
    },
    {
        "title": "Cline 跨平台 AI 记忆中枢架构分享",
        "content": "分享在 Trae/Claude/Codex/Cursor 多个 AI 平台间搭建共享记忆系统的经验。本地快照 + 云端 SQLite 双层存储，自动同步。",
        "category": "showcase",
        "author_name": "钟笑咪",
        "tags": ["记忆中枢", "多 Agent", "SQLite"],
    },
    {
        "title": "从校园到黑客松：AI 创业踩坑记录",
        "content": "作为宁波大学大一学生，分享参与黑客松、运营社群、做产品的真实经历和思考。希望能帮助到同样在探索的同学。",
        "category": "discussion",
        "author_name": "钟笑咪",
        "tags": ["创业", "黑客松", "校园"],
    },
]

SEED_REPLIES = [
    # replies for topic 0 (正当防卫)
    {"topic_idx": 0, "author_name": "法学萌新", "content": "这个视频把正当防卫的五个要件讲得很清楚！特别是「防卫时机」那部分，以前一直搞不懂。"},
    {"topic_idx": 0, "author_name": "罗翔说刑法", "content": "谢谢！时机要件确实是考试重点，建议结合案例反复理解。"},
    {"topic_idx": 0, "author_name": "法考二战人", "content": "闯关答题太有用了！第一题那个张三误伤物业工人的案例，答完之后印象特别深。"},
    # replies for topic 1 (假想防卫)
    {"topic_idx": 1, "author_name": "刑法课代表", "content": "假想防卫：客观上不存在不法侵害，但行为人误以为存在；防卫过当：客观上存在不法侵害，但防卫行为超过了必要限度。核心区别在于「侵害是否真实存在」。"},
    {"topic_idx": 1, "author_name": "法学萌新", "content": "原来如此！那假想防卫如果致人重伤，怎么定性？"},
    {"topic_idx": 1, "author_name": "刑法课代表", "content": "一般按过失致人重伤罪处理，因为行为人主观上没有犯罪故意。"},
    # replies for topic 2 (Agent演示)
    {"topic_idx": 2, "author_name": "视频创作者阿杰", "content": "视频片段导航功能太实用了！能详细说说怎么做的时间轴分段吗？"},
    {"topic_idx": 2, "author_name": "钟笑咪", "content": "目前是用 Whisper 做语音转写，然后让 LLM 根据转写文本自动识别知识点边界，再映射到视频时间戳。准确率大概在 85% 左右。"},
    # replies for topic 4 (闯关答题)
    {"topic_idx": 4, "author_name": "教育技术研究生", "content": "学习闭环的设计很合理。建议增加「错题回顾」功能，让学习者可以重做错过的题目。"},
    {"topic_idx": 4, "author_name": "钟笑咪", "content": "好建议！已经加到 roadmap 了，会支持「错题本 + 重做」功能。"},
    # replies for topic 5 (献书)
    {"topic_idx": 5, "author_name": "游戏策划阿文", "content": "东晋历史题材选得好！市面上三国太多，东晋的 AI 互动游戏还是第一次见。"},
    {"topic_idx": 5, "author_name": "钟笑咪", "content": "谢谢！立绘用的是 Midjourney + Stable Diffusion 组合，服装和场景参考了大量东晋出土文物。"},
]


def seed(profile_id: str, db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    # check if already seeded
    count = conn.execute("SELECT COUNT(*) FROM community_topics WHERE profile_id = ?", (profile_id,)).fetchone()[0]
    if count > 0:
        print(f"[SKIP] Already {count} topics for {profile_id}")
        conn.close()
        return

    now_topics: list[tuple] = []
    topic_ids: list[str] = []
    for t in SEED_TOPICS:
        tid = f"topic_{uuid.uuid4().hex[:12]}"
        topic_ids.append(tid)
        now_topics.append((
            tid, profile_id, t["title"], t["content"], t["category"],
            t["author_name"], json.dumps(t["tags"], ensure_ascii=False),
            0, 0, 0, 0, 0, "2026-07-15T10:00:00", "2026-07-15T10:00:00",
        ))

    conn.executemany(
        """INSERT INTO community_topics
           (id, profile_id, title, content, category, author_name, tags_json,
            view_count, reply_count, like_count, is_pinned, is_resolved,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        now_topics,
    )

    now_replies: list[tuple] = []
    reply_counts: dict[int, int] = {}
    for r in SEED_REPLIES:
        rid = f"reply_{uuid.uuid4().hex[:12]}"
        tid = topic_ids[r["topic_idx"]]
        now_replies.append((rid, tid, None, r["author_name"], r["content"], "2026-07-15T12:00:00"))
        reply_counts[r["topic_idx"]] = reply_counts.get(r["topic_idx"], 0) + 1

    conn.executemany(
        """INSERT INTO community_replies
           (id, topic_id, parent_reply_id, author_name, content, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        now_replies,
    )

    for idx, cnt in reply_counts.items():
        tid = topic_ids[idx]
        conn.execute(
            "UPDATE community_topics SET reply_count = ? WHERE id = ?",
            (cnt, tid),
        )

    conn.commit()
    conn.close()

    print(f"[OK] Seeded {len(now_topics)} topics, {len(now_replies)} replies for {profile_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="社区种子数据")
    parser.add_argument("--profile", default="profile_ashley")
    parser.add_argument("--db", default="data/site.db", help="SQLite 路径")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    db_path = project_root / args.db
    if not db_path.exists():
        print(f"[ERR] DB not found: {db_path}")
        return

    seed(args.profile, db_path)


if __name__ == "__main__":
    main()

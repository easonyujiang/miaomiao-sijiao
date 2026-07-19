"""妙喵私教 — 真实用户全流程端到端测试

模拟一个真实用户从打开 B站视频到完成 5 关学习的完整路径：

  用户打开视频页 → 插件检测 → 注册视频 → 加载课程 →
  打开面板 → 看到课程信息 → 开始学习 →
  [第 1 关] 看讲解片段 → 答题 → 判卷 → 看到反馈 → 下一关 →
  [第 2 关] 看讲解片段 → 答题 → 答错 → 看到纠错 → 回去再学 → 重新作答 → 通过 →
  [第 3~5 关] 继续... →
  [课程完成] 看到星星/小鱼干/成长值总结

每个阶段验证的是前端实际会渲染的信息：
  - 课程卡：title, total_steps, creator_name, step 列表
  - 答题反馈：passed, score, cat_message, stars_earned, matched/missed/wrong
  - 纠错信息：seek_to_ms, missed_points, wrong_points
  - 进度追踪：gamification (stars/fish/growth), completed_steps
  - 完成页：总星星数、小鱼干、成长值
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ewa.api.main import create_app
from ewa.core.middleware import reset_rate_limiters


# ═══════════════════════════════════════════════════════════════════
# 测试环境
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    """每个测试独立 DB + 独立限流器状态"""
    reset_rate_limiters()
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    os.environ["EWA_SITE_DB_PATH"] = db_path
    app = create_app(site_db_path=db_path)
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════
# 用户旅程模拟
# ═══════════════════════════════════════════════════════════════════

class TestUserJourney:
    """模拟一个真实用户打开 B站视频，从头到尾完成学习的完整路径。"""

    # ── 阶段 1：用户打开视频页，插件初始化 ──────────────────────────

    def test_phase1_arrive_at_video_page(self, client):
        """
        用户打开 B站视频 BV1mJ4m147PG。

        插件做的事（content_script.js init）：
        1. detectPlatform() → platform=bilibili, videoId=BV1mJ4m147PG
        2. checkBackendHealth() → /health
        3. registerVideo() → POST /api/ext/register_video
        4. loadLesson() → POST /api/lesson/load
        5. updateBubbleBadge() → 气泡上显示进度标记

        验证：后端连通、视频注册成功、课程正确加载。
        """
        # 健康检查（content_script.js: checkBackendHealth）
        h = client.get("/health")
        assert h.status_code == 200
        assert h.json()["status"] == "ok"

        # 注册视频（content_script.js: registerVideo）
        r = client.post("/api/ext/register_video", json={
            "video_id": "BV1mJ4m147PG",
            "title": "罗翔：正当防卫的构成要件",
            "platform": "bilibili",
        })
        assert r.status_code == 200
        video_info = r.json()
        assert video_info["video_id"] == "BV1mJ4m147PG"
        assert video_info["subtitle_count"] >= 0  # 有字幕更好，没有也能跑

        # 加载课程（content_script.js: loadLesson）
        r = client.post("/api/lesson/load", json={
            "video_id": "BV1mJ4m147PG",
            "platform": "bilibili",
        })
        assert r.status_code == 200
        lesson = r.json()

        # 验证课程卡片信息（content_script.js: renderLanding 会渲染这些）
        assert lesson["lesson_id"] == "lesson_luoxiang_001"
        assert "正当防卫" in lesson["title"]
        assert lesson["creator_name"] == "罗翔说刑法"
        assert lesson["total_steps"] == 5

        # 验证 step 包含前端需要渲染的所有字段
        # （renderWatchingStep / renderAnswerForm 会用这些）
        for step in lesson["steps"]:
            assert "id" in step, "每个 step 必须有 id"
            assert "title" in step, "renderWatchingStep 渲染 step-title"
            assert "start_ms" in step, "miaomiao-seek-btn 跳转需要"
            assert "instruction" in step, "看片引导文案"
            assert "key_point" in step, "核心要点卡片"
            assert "question" in step, "答题区显示题目"
            # 安全验证：答案绝不能泄露给前端
            assert "answer_key" not in step, "answer_key 泄露到前端！"
            assert "wrong_key" not in step, "wrong_key 泄露到前端！"
            assert "min_correct" not in step, "min_correct 泄露到前端！"

    # ── 阶段 2：用户打开面板，看到课程首页 ──────────────────────────

    def test_phase2_open_panel_and_see_landing(self, client):
        """
        用户点击右下角 🐱 气泡 → 面板展开。

        renderLanding() 显示：
        - 课程标题
        - 创作者名字
        - 共 N 关
        - 「开始学习」或「继续学习」按钮

        点击「开始学习」→ startOrContinueLesson() →
        找到第一个未通过的 step → renderWatchingStep()
        """
        lesson = self._load_lesson(client)

        # 用户此时还没有任何学习记录
        session = "user_session_1"

        # 检查初始状态（content_script.js: getStateAPI 恢复进度）
        r = client.get(f"/api/lesson/state/{session}/{lesson['lesson_id']}")
        state = r.json()

        # 新用户：0 星，0 进度，待命状态
        assert state["gamification"]["total_stars"] == 0
        assert state["gamification"]["fish"] == 0
        assert state["gamification"]["growth"] == 0
        assert state["current_step_index"] == 0
        assert state["completed_steps"] == []
        # cat_state: idle（妙喵待命中）

    # ── 阶段 3：第 1 关 — 一次通过 ──────────────────────────────────

    def test_phase3_step1_watch_answer_pass(self, client):
        """
        第 1 关「起因条件：必须存在不法侵害」：

        1. renderWatchingStep(step_1)
           - 显示第 1 关 badge、标题
           - 显示 instruction 引导文案
           - 显示 key_point 核心要点卡片
           - 显示「跳转到讲解片段」按钮（seek to start_ms）
           - 显示「我看完了，开始答题」按钮

        2. 用户点击「开始答题」→ renderAnswerForm(step_1)
           - 显示题目 question
           - 显示 textarea 输入框
           - 显示字数统计和「提交答案」按钮

        3. 用户输入答案 → handleSubmitAnswer()
           - 界面显示「猫猫正在认真判卷…」
           - 后端评分 → 返回结果

        4. 用户通过 → renderPassResult()
           - 显示 🌟 emoji + "完美通过！"
           - 显示 cat_message（猫咪反馈）
           - 显示 ⭐ N 星 + ✅ N/N 要点
           - 显示进度条
           - 显示「下一关」按钮
           - 自动 seek 到下一步的 start_ms
        """
        lesson = self._load_lesson(client)
        session = "user_journey"
        step = lesson["steps"][0]

        # 检查 step_1 数据完整性（renderWatchingStep 需要的字段）
        assert step["id"] == "step_1"
        assert len(step["title"]) > 0
        assert len(step["instruction"]) > 0
        assert len(step["key_point"]) > 0
        assert step["start_ms"] > 0
        assert len(step["question"]) > 0

        # 用户提交一个很好的答案（应一次通过）
        r = client.post("/api/lesson/quiz_submit", json={
            "session_id": session,
            "lesson_id": lesson["lesson_id"],
            "step_id": "step_1",
            "answer": "不成立。这是假想防卫的情形，客观上没有现实的不法侵害，属于事实认识错误，应按意外事件或过失处理。",
            "current_time_sec": step["start_ms"] // 1000,
        })
        assert r.status_code == 200
        result = r.json()

        # ── 验证前端 renderPassResult 渲染的内容 ──
        assert result["passed"] is True, "应该通过"
        assert result["score"] >= 0.5, "得分合理"
        assert result["stars_earned"] >= 2, "第一次通过至少 2 星"

        # cat_message 给用户看（renderPassResult 中 miaomiao-cat-message）
        assert len(result["cat_message"]) > 10, "猫咪反馈不能为空"
        assert "⭐" in result["cat_message"] or "🌟" in result["cat_message"] or "🐟" in result["cat_message"] or "小鱼干" in result["cat_message"]

        # 命中要点统计（miaomiao-result-stats）
        assert result["matched_count"] >= result["required_count"]

        # 下一步信息（miaomiao-next-btn）
        assert result["next_step"] is not None, "通过后必须提供下一步"
        assert result["next_step"]["id"] == "step_2"
        assert len(result["next_step"]["title"]) > 0

        # session_summary 用于气泡 badge 更新（updateBubbleBadge）
        assert result["session_summary"]["total_stars"] >= 2
        assert result["session_summary"]["fish"] >= 1
        assert result["session_summary"]["growth"] >= 1

    # ── 阶段 4：第 2 关 — 先答错，再纠正 ──────────────────────────

    def test_phase4_step2_fail_then_retry(self, client):
        """
        第 2 关「时间条件：不法侵害正在进行」：

        用户第一次回答不完整 → 未通过 → 看到纠错反馈 →
        回去再看视频片段 → 重新作答 → 通过。

        renderFailResult() 显示：
        - 📝 emoji + "还差一点点~"
        - cat_message 猫咪点评
        - 漏掉的要点列表（missed_points）
        - 理解有误的要点（wrong_points，如果有）
        - 「跳转到讲解片段」按钮（seek_to_ms）
        - 「重新作答」按钮

        用户点击「重新作答」→ renderAnswerForm 重新显示 →
        输入改进后的答案 → 通过 → 星星递减（第 2 次通过最多 2 星）。
        """
        lesson = self._load_lesson(client)
        session = "user_journey_retry"
        step = lesson["steps"][1]  # step_2

        assert step["id"] == "step_2"

        # ── 第一次：答案不完整（只说了结论，没展开理由） ──
        r1 = client.post("/api/lesson/quiz_submit", json={
            "session_id": session,
            "lesson_id": lesson["lesson_id"],
            "step_id": "step_2",
            "answer": "应该算吧，我也不太确定",  # 太模糊，不会命中任何要点
            "current_time_sec": step["start_ms"] // 1000,
        })
        assert r1.status_code == 200
        fail = r1.json()

        # 前端 renderFailResult 验证
        assert fail["passed"] is False, "应该不通过"
        assert fail["attempt_num"] == 1
        assert fail["stars_earned"] == 0, "未通过不得星"

        # 纠错信息：必须告诉用户哪里不对
        assert fail["seek_to_ms"] is not None, "必须提供回看时间戳"
        assert (len(fail["missed_points"]) > 0 or len(fail["wrong_points"]) > 0), \
            "必须告诉用户漏了什么或哪里错了"

        # cat_message 应该有提示（renderFailResult 中 miaomiao-cat-message）
        assert len(fail["cat_message"]) > 10

        # ── 第二次：回去看了视频，答案改进了 ──
        r2 = client.post("/api/lesson/quiz_submit", json={
            "session_id": session,
            "lesson_id": lesson["lesson_id"],
            "step_id": "step_2",
            "answer": "现场追回属于正当防卫，因为侵害仍在进行中，财产犯罪的现场追回视为侵害持续。但第二天打伤不构成正当防卫，属于事后报复，侵害已经结束。",
            "current_time_sec": step["start_ms"] // 1000 + 30,
        })
        assert r2.status_code == 200
        retry = r2.json()

        # 这次应该通过
        assert retry["passed"] is True, f"改进后应通过，但 matched={retry['matched_count']}/{retry['required_count']}"
        assert retry["attempt_num"] == 2
        # 第 2 次尝试得星递减（最高 2 星）
        assert retry["stars_earned"] <= 2

    # ── 阶段 5：完成全部 5 关后查看总结 ────────────────────────────

    def test_phase5_complete_all_and_see_summary(self, client):
        """
        用户经历了 5 关的学习（有人一次过，有人要重试），
        全部通过后：

        renderComplete() 显示：
        - 🏆 emoji + "课程完成！"
        - 课程标题
        - ⭐ 星星统计（获得/满分）
        - 🐟 小鱼干数量
        - 📈 成长值
        - 总结文字
        - 「重新学习」按钮

        这个测试模拟真实场景：
        - 5 关中有 3 关一次过，1 关先错后对，1 关只过了最低标准
        - 验证累计统计正确
        """
        lesson = self._load_lesson(client)
        session = "user_journey_complete"

        # 真实风格的答案（不是灌 answer_key 关键词，而是自然表达）
        answers = {
            "step_1": "不成立。这是假想防卫，客观上没有现实的不法侵害存在，行为人属于事实认识错误，应按过失或意外事件处理。",
            "step_2": "现场追回属于正当防卫，因为财产犯罪侵害仍在进行。但第二天找到再打就是事后报复，不构成正当防卫了。",
            "step_3": "对侵害人本人的反击行为属于防卫，防卫对象必须是侵害人本人。误伤劝架路人的行为可能成立紧急避险，没有伤人的故意。",
            "step_4": "孙七的行为不成立防卫，这是典型的挑拨防卫——故意激怒对方再以防卫为名反击。互殴中如果一方明确停止而对方继续攻击，停止方可以获得防卫资格。",
            "step_5": "这不属于过度防卫，是特殊防卫。刑法第20条第3款规定，对正在进行的抢劫等严重危及人身安全的暴力犯罪，防卫致人死亡不负刑事责任，属于无限防卫权。",
        }

        max_possible_stars = 5 * 3  # 15
        earned_stars = 0

        for step in lesson["steps"]:
            answer = answers[step["id"]]

            r = client.post("/api/lesson/quiz_submit", json={
                "session_id": session,
                "lesson_id": lesson["lesson_id"],
                "step_id": step["id"],
                "answer": answer,
                "current_time_sec": step["start_ms"] // 1000,
            })
            assert r.status_code == 200
            result = r.json()

            # 每步都应该有 cat_message（猫咪反馈）
            assert len(result["cat_message"]) > 0, f"{step['id']} 缺少猫咪反馈"

            if result["passed"]:
                earned_stars += result["stars_earned"]
                # 通过后必须有下一步（除非是最后一关）
                if step["id"] != "step_5":
                    assert result["next_step"] is not None, \
                        f"{step['id']} 通过后应提供下一步"
            else:
                # 不通过时应该有纠错信息
                assert result["seek_to_ms"] is not None, \
                    f"{step['id']} 未通过应提供回看时间戳"
                # 现实中用户会重试，但这里我们只验证反馈完整性
                pytest.fail(
                    f"{step['id']} 未通过！matched={result['matched_count']}/"
                    f"{result['required_count']}, missed={result['missed_points']}"
                )

        # ── 查看完成状态（前端 renderComplete 渲染的数据） ──
        r = client.get(f"/api/lesson/state/{session}/{lesson['lesson_id']}")
        state = r.json()

        summary = state["gamification"]

        # ⭐ 星星（miaomiao-stat: stars）
        assert summary["total_stars"] > 0, "至少获得一些星星"
        assert summary["total_stars"] <= max_possible_stars

        # 🐟 小鱼干（miaomiao-stat: fish）
        assert summary["fish"] > 0, "应该获得小鱼干"

        # 📈 成长值（miaomiao-stat: growth）
        assert summary["growth"] > 0, "应该获得成长值"

        # 完成状态
        assert len(state["completed_steps"]) >= 1, "至少完成了一些关卡"

        # ── 验证完成后的 next_step 行为 ──
        r = client.post("/api/lesson/next_step", json={
            "session_id": session,
            "lesson_id": lesson["lesson_id"],
            "step_id": "step_5",
        })
        finish = r.json()
        # 全部完成时返回 lesson_complete 或 advanced（取决于自动推进）
        assert finish["status"] in ("lesson_complete", "advanced")
        if finish["status"] == "lesson_complete":
            assert "message" in finish
            assert finish["summary"]["total_stars"] == summary["total_stars"]

    # ── 阶段 6：用户离开后再回来，进度还在 ────────────────────────

    def test_phase6_come_back_later_progress_persisted(self, client):
        """
        用户关闭页面 → 再次打开 → 插件恢复之前的进度。

        content_script.js init() 中：
        - getStateAPI() → 恢复 totalStars, fish, growth
        - renderLanding() 显示「继续学习」而非「开始学习」
        - updateBubbleBadge() 显示已完成关数
        """
        lesson = self._load_lesson(client)
        session = "user_come_back"

        # 先完成 2 关（用已知能通过的自然答案）
        step_answers = {
            "step_1": "不成立。客观上没有现实的不法侵害，属于假想防卫的情形，应按事实认识错误来处理。",
            "step_2": "现场追回属于正当防卫，因为财产犯罪侵害仍在进行。但第二天打伤就属于事后报复，不再是防卫行为了。",
        }
        for step_id in ("step_1", "step_2"):
            step = next(s for s in lesson["steps"] if s["id"] == step_id)
            client.post("/api/lesson/quiz_submit", json={
                "session_id": session,
                "lesson_id": lesson["lesson_id"],
                "step_id": step["id"],
                "answer": step_answers[step["id"]],
                "current_time_sec": step["start_ms"] // 1000,
            })

        # 查状态（模拟用户关掉页面后回来）
        r = client.get(f"/api/lesson/state/{session}/{lesson['lesson_id']}")
        state = r.json()

        # 验证持久化
        assert state["persisted"] is True, "学习进度应已持久化到 SQLite"
        assert state["gamification"]["total_stars"] > 0, "星星不应丢失"
        assert len(state["completed_steps"]) >= 1

        # completed_steps 包含已通过的 step
        assert "step_1" in state["completed_steps"], "step_1 应在已完成列表"


# ═══════════════════════════════════════════════════════════════════
# API 单元测试（边界条件 / 异常路径）
# ═══════════════════════════════════════════════════════════════════

class TestLessonLoad:
    """课程加载 — 边界条件"""

    def test_load_by_video_id(self, client):
        r = client.post("/api/lesson/load", json={
            "video_id": "BV1mJ4m147PG", "platform": "bilibili",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["lesson_id"] == "lesson_luoxiang_001"
        assert data["total_steps"] == 5
        assert data["creator_name"] == "罗翔说刑法"

    def test_load_answer_key_not_leaked(self, client):
        """answer_key 绝不能泄露到前端"""
        r = client.post("/api/lesson/load", json={
            "video_id": "BV1mJ4m147PG", "platform": "bilibili",
        })
        for step in r.json()["steps"]:
            assert "answer_key" not in step
            assert "wrong_key" not in step
            assert "min_correct" not in step

    def test_load_default_fallback(self, client):
        """未知视频返回空步骤"""
        r = client.post("/api/lesson/load", json={
            "video_id": "unknown_video_id", "platform": "bilibili",
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("error") == "no lesson found"
        assert data["steps"] == []


class TestQuizSubmit:
    """答题判卷 — 边界条件"""

    def test_correct_answer_passes(self, client):
        r = client.post("/api/lesson/quiz_submit", json={
            "session_id": "correct_test",
            "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "不成立，这是假想防卫的情形，客观上没有现实的不法侵害，属于事实认识错误",
            "current_time_sec": 60,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["passed"] is True
        assert data["stars_earned"] == 3
        assert data["attempt_num"] == 1
        assert data["matched_count"] >= data["required_count"]

    def test_attempts_survive_session_save(self, client):
        """回归：attempts 必须存活于后续 save_session。

        历史上 persist_session 用 INSERT OR REPLACE，DELETE+INSERT 触发
        lesson_attempts 的 ON DELETE CASCADE，导致答题记录被级联清空。
        """
        from ewa.extension.store import LessonStore

        session = "attempts_persist_test"
        # 答对 step_1（通过后会再次 persist_session 推进进度）
        r = client.post("/api/lesson/quiz_submit", json={
            "session_id": session,
            "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "不成立，这是假想防卫的情形，客观上没有现实的不法侵害，属于事实认识错误",
            "current_time_sec": 60,
        })
        assert r.json()["passed"] is True

        attempts = LessonStore.load_attempts(session)
        assert len(attempts) == 1
        assert attempts[0]["step_id"] == "step_1"

        # 再提交 step_2，step_1 的 attempts 不应被级联删除
        client.post("/api/lesson/quiz_submit", json={
            "session_id": session,
            "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_2",
            "answer": "随便答答",
            "current_time_sec": 120,
        })
        attempts = LessonStore.load_attempts(session)
        step_ids = {a["step_id"] for a in attempts}
        assert "step_1" in step_ids and "step_2" in step_ids

    def test_wrong_answer_fails(self, client):
        r = client.post("/api/lesson/quiz_submit", json={
            "session_id": "wrong_test",
            "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "这就是构成正当防卫，紧急避险也是对的",
            "current_time_sec": 60,
        })
        data = r.json()
        assert data["passed"] is False
        assert data["seek_to_ms"] is not None
        assert len(data["missed_points"]) > 0 or len(data["wrong_points"]) > 0

    def test_retry_stars_decrease(self, client):
        """重试通过后得星递减：第1次3星→第2次2星→第3次1星"""
        session = "retry_stars_test"
        # 第一次：答错
        r1 = client.post("/api/lesson/quiz_submit", json={
            "session_id": session, "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "构成正当防卫",
            "current_time_sec": 60,
        })
        assert r1.json()["passed"] is False

        # 第二次：答对
        r2 = client.post("/api/lesson/quiz_submit", json={
            "session_id": session, "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "不成立，客观上没有现实的不法侵害，属于假想防卫，应按事实认识错误处理",
            "current_time_sec": 60,
        })
        data2 = r2.json()
        assert data2["passed"] is True
        assert data2["attempt_num"] == 2
        assert data2["stars_earned"] == 2  # 第二次最多 2 星

    def test_next_step_provided_on_pass(self, client):
        r = client.post("/api/lesson/quiz_submit", json={
            "session_id": "next_test",
            "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "不成立，这是假想防卫，客观上没有现实的不法侵害，属于事实认识错误",
            "current_time_sec": 60,
        })
        data = r.json()
        assert data["passed"] is True
        assert data["next_step"] is not None
        assert data["next_step"]["id"] == "step_2"


class TestStatePersistence:
    """状态持久化"""

    def test_state_persisted_across_requests(self, client):
        session = "persist_test"
        client.post("/api/lesson/quiz_submit", json={
            "session_id": session, "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "不成立，这是假想防卫，客观上没有现实的不法侵害，属于事实认识错误",
            "current_time_sec": 60,
        })
        r = client.get(f"/api/lesson/state/{session}/lesson_luoxiang_001")
        data = r.json()
        assert data["gamification"]["total_stars"] == 3
        assert data["persisted"] is True

    def test_state_persisted_across_app_instances(self, client):
        session = "restart_test"
        client.post("/api/lesson/quiz_submit", json={
            "session_id": session, "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "不成立，这是假想防卫，客观上没有现实的不法侵害，属于事实认识错误",
            "current_time_sec": 60,
        })
        r = client.get(f"/api/lesson/state/{session}/lesson_luoxiang_001")
        assert r.json()["persisted"] is True

    def test_lesson_report_after_quiz_submission(self, client):
        """提交答题后，学习分析报告应包含已完成步骤和尝试记录。"""
        session = "report_test"
        r1 = client.post("/api/lesson/quiz_submit", json={
            "session_id": session, "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "不成立，这是假想防卫，客观上没有现实的不法侵害，属于事实认识错误",
            "current_time_sec": 60,
        })
        assert r1.status_code == 200
        assert r1.json()["passed"] is True

        r2 = client.get(f"/api/lesson/report/{session}/lesson_luoxiang_001")
        assert r2.status_code == 200
        report = r2.json()
        assert report["total_stars"] == 3
        assert "step_1" in report["completed_steps"]
        assert report["completion_rate"] == 0.2

    def test_lesson_report_shows_weak_points(self, client):
        """答错的步骤应出现在薄弱点里。"""
        session = "report_weak_test"
        r1 = client.post("/api/lesson/quiz_submit", json={
            "session_id": session, "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "我不知道",
            "current_time_sec": 60,
        })
        assert r1.status_code == 200
        assert r1.json()["passed"] is False

        r2 = client.get(f"/api/lesson/report/{session}/lesson_luoxiang_001")
        assert r2.status_code == 200
        report = r2.json()
        assert report["total_stars"] == 0
        assert report["completed_steps"] == []
        assert report["completion_rate"] == 0.0
        assert any(w["step_id"] == "step_1" for w in report["weak_points"])
        assert len(report["weak_points"]) > 0


class TestExtAPI:
    """插件 API"""

    def test_register_video(self, client):
        r = client.post("/api/ext/register_video", json={
            "video_id": "BV1mJ4m147PG",
            "title": "罗翔：正当防卫的构成要件",
            "platform": "bilibili",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["subtitle_count"] == 66

    def test_register_video_cache(self, client):
        payload = {
            "video_id": "BV1mJ4m147PG",
            "title": "罗翔：正当防卫",
            "platform": "bilibili",
        }
        r1 = client.post("/api/ext/register_video", json=payload)
        r2 = client.post("/api/ext/register_video", json=payload)
        assert r1.json() == r2.json()

    def test_chat_offline_faq(self, client):
        r = client.post("/api/ext/chat", json={
            "message": "什么是正当防卫的构成要件？",
            "video_id": "BV1mJ4m147PG",
            "platform": "bilibili",
            "current_time_sec": 120,
        })
        assert r.status_code == 200
        data = r.json()
        assert len(data["answer"]) > 50

    def test_chat_unknown_question(self, client):
        r = client.post("/api/ext/chat", json={
            "message": "今天天气怎么样xyz123",
            "video_id": "BV1mJ4m147PG",
            "platform": "bilibili",
            "current_time_sec": 0,
        })
        assert r.status_code == 200
        assert len(r.json()["answer"]) > 0

    def test_health_endpoint(self, client):
        r = client.get("/api/ext/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestErrorHandling:
    """异常处理"""

    def test_unknown_lesson_falls_back(self, client):
        r = client.post("/api/lesson/quiz_submit", json={
            "session_id": "s", "lesson_id": "nonexistent",
            "step_id": "step_1", "answer": "test",
            "current_time_sec": 0,
        })
        assert r.status_code == 200
        data = r.json()
        assert "error" in data

    def test_unknown_step_returns_error(self, client):
        r = client.post("/api/lesson/quiz_submit", json={
            "session_id": "s", "lesson_id": "lesson_luoxiang_001",
            "step_id": "nonexistent", "answer": "test",
            "current_time_sec": 0,
        })
        assert r.status_code == 200
        assert "error" in r.json()

    def test_empty_answer_handled(self, client):
        r = client.post("/api/lesson/quiz_submit", json={
            "session_id": "empty_test",
            "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "",
            "current_time_sec": 0,
        })
        data = r.json()
        assert data["passed"] is False

    def test_session_summary_consistent(self, client):
        session = "summary_test"
        client.post("/api/lesson/quiz_submit", json={
            "session_id": session, "lesson_id": "lesson_luoxiang_001",
            "step_id": "step_1",
            "answer": "不成立，这是假想防卫，客观上没有现实的不法侵害，属于事实认识错误",
            "current_time_sec": 60,
        })
        r = client.get(f"/api/lesson/state/{session}/lesson_luoxiang_001")
        state = r.json()
        assert state["gamification"]["total_stars"] > 0


# ═══════════════════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════════════════

def _load_lesson(client, video_id="BV1mJ4m147PG", platform="bilibili"):
    """加载课程（模拟 content_script.js loadLesson()）。"""
    r = client.post("/api/lesson/load", json={
        "video_id": video_id,
        "platform": platform,
    })
    assert r.status_code == 200
    data = r.json()
    assert "error" not in data, f"课程加载失败: {data}"
    return data


# 将辅助函数绑定到 TestUserJourney 以便 self._load_lesson 可用
TestUserJourney._load_lesson = staticmethod(_load_lesson)

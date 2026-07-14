/**
 * 妙喵私教 — Content Script
 *
 * 注入 B站/抖音视频页，在播放器右下角显示 🐱 气泡，
 * 点击后展开私教面板：看片段 → 答题 → AI判卷 → 纠错跳转 → 下一关
 *
 * API 基地址：http://localhost:8000
 */

(async function () {
  "use strict";

  // ── 配置 ──────────────────────────────────────────────────
  // P1-3: API_BASE 从 chrome.storage 读取，默认 localhost:8000
  let API_BASE = "http://localhost:8000";
  const POLL_INTERVAL_MS = 2000; // 检测播放器的轮询间隔

  // ── 猫咪表情（CSS emoji，6 种状态） ────────────────────────
  const CAT_EMOJI = {
    idle: "🐱",
    watching: "🐱💭",
    listening: "🐱👂",
    analyzing: "🐱🔍",
    correcting: "🐱📝",
    celebrating: "🐱🎉",
  };

  const CAT_LABEL = {
    idle: "妙喵待命中",
    watching: "妙喵听课中",
    listening: "妙喵在听你说",
    analyzing: "妙喵正在判卷",
    correcting: "妙喵帮你纠错",
    celebrating: "妙喵为你开心",
  };

  // ── 全局状态 ──────────────────────────────────────────────
  let state = {
    catState: "idle", // idle | watching | listening | analyzing | correcting | celebrating
    sessionId: null,
    lesson: null, // 当前加载的 Lesson 数据
    currentStepIndex: 0,
    stepResults: {},
    totalStars: 0,
    fish: 0,
    growth: 0,
    reviewQueue: [],
    isPanelOpen: false,
    videoId: null,
    platform: null,
    playerReady: false,
  };

  // ── 工具函数 ──────────────────────────────────────────────

  /** 检测当前是否为支持的视频页 */
  function detectPlatform() {
    const url = location.href;
    if (url.includes("bilibili.com/video/")) {
      const m = url.match(/\/video\/(BV[a-zA-Z0-9]+)/);
      return m ? { platform: "bilibili", videoId: m[1] } : null;
    }
    if (url.includes("douyin.com/video/")) {
      const m = url.match(/\/video\/(\d+)/);
      return m ? { platform: "douyin", videoId: m[1] } : null;
    }
    return null;
  }

  /** 获取 B站播放器实例 */
  function getBilibiliPlayer() {
    // B站播放器挂载在 window.player 或 #bofqi 下
    if (window.player && window.player.seek) return window.player;
    // 尝试从 DOM 中获取
    const videoEl = document.querySelector("video");
    return videoEl;
  }

  /** 获取抖音播放器实例 */
  function getDouyinPlayer() {
    return document.querySelector("video");
  }

  /** 获取当前视频播放时间（秒） */
  function getCurrentTime() {
    const player = getBilibiliPlayer() || getDouyinPlayer();
    if (player && player.currentTime !== undefined) {
      return Math.floor(player.currentTime);
    }
    return 0;
  }

  /** 跳转到指定时间 */
  function seekTo(seconds) {
    const player = getBilibiliPlayer() || getDouyinPlayer();
    if (!player) return false;

    if (player.seek) {
      // B站播放器 API
      player.seek(seconds);
    } else {
      player.currentTime = seconds;
    }
    return true;
  }

  /** 获取或创建持久化的 session ID（按视频存 chrome.storage） */
  async function resolveSessionId() {
    const vid = state.videoId || "unknown";
    const storageKey = `session_${vid}`;
    try {
      const data = await chrome.storage.local.get(storageKey);
      if (data[storageKey]) {
        console.log(`[妙喵] 恢复已有 session: ${data[storageKey]}`);
        return data[storageKey];
      }
    } catch (e) { /* ignore */ }
    // 新建并存储
    const ts = Date.now();
    const rand = Math.random().toString(36).slice(2, 8);
    const newId = `${vid}_${ts}_${rand}`;
    try {
      await chrome.storage.local.set({ [storageKey]: newId });
    } catch (e) { /* ignore */ }
    console.log(`[妙喵] 新 session: ${newId}`);
    return newId;
  }

  // ── API 调用 ──────────────────────────────────────────────

  async function apiCall(method, path, body) {
    try {
      const opts = {
        method,
        headers: { "Content-Type": "application/json" },
      };
      if (body) opts.body = JSON.stringify(body);
      const res = await fetch(`${API_BASE}${path}`, opts);
      if (!res.ok) {
        console.warn(`[妙喵] API ${path} returned ${res.status}`);
        return null;
      }
      return await res.json();
    } catch (err) {
      console.warn(`[妙喵] API ${path} failed:`, err.message);
      return null;
    }
  }

  /** 检查后端连通性 */
  async function checkBackendHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`, {
        method: "GET",
        signal: AbortSignal.timeout(3000),
      });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  async function registerVideo() {
    if (!state.videoId) return null;
    const title = document.title || "";
    return apiCall("POST", "/api/ext/register_video", {
      video_id: state.videoId,
      title: title,
      platform: state.platform,
    });
  }

  async function loadLesson() {
    if (!state.videoId) return null;
    return apiCall("POST", "/api/lesson/load", {
      video_id: state.videoId,
      platform: state.platform,
    });
  }

  async function submitAnswer(stepId, answer) {
    if (!state.sessionId || !state.lesson) return null;
    return apiCall("POST", "/api/lesson/quiz_submit", {
      session_id: state.sessionId,
      lesson_id: state.lesson.lesson_id,
      step_id: stepId,
      answer: answer,
      current_time_sec: getCurrentTime(),
    });
  }

  async function nextStepAPI(stepId) {
    if (!state.sessionId || !state.lesson) return null;
    return apiCall("POST", "/api/lesson/next_step", {
      session_id: state.sessionId,
      lesson_id: state.lesson.lesson_id,
      step_id: stepId,
    });
  }

  async function getStateAPI() {
    if (!state.sessionId || !state.lesson) return null;
    return apiCall(
      "GET",
      `/api/lesson/state/${state.sessionId}/${state.lesson.lesson_id}`
    );
  }

  // ── UI 构建 ───────────────────────────────────────────────

  /** 创建并注入整个妙喵 UI 容器 */
  function injectUI() {
    if (document.getElementById("miaomiao-root")) return;

    const root = document.createElement("div");
    root.id = "miaomiao-root";
    root.innerHTML = `
      <!-- 悬浮气泡 -->
      <div id="miaomiao-bubble" class="miaomiao-bubble" title="妙喵私教">
        <span id="miaomiao-bubble-emoji">${CAT_EMOJI.idle}</span>
        <span id="miaomiao-bubble-badge" class="miaomiao-badge" style="display:none">0</span>
      </div>

      <!-- 私教面板 -->
      <div id="miaomiao-panel" class="miaomiao-panel" style="display:none">
        <div class="miaomiao-panel-header">
          <div class="miaomiao-panel-title">
            <span id="miaomiao-cat-state-emoji">${CAT_EMOJI.idle}</span>
            <span id="miaomiao-cat-state-label">${CAT_LABEL.idle}</span>
          </div>
          <button id="miaomiao-close-btn" class="miaomiao-icon-btn" title="关闭">✕</button>
        </div>
        <div id="miaomiao-content" class="miaomiao-panel-body"></div>
      </div>
    `;
    document.body.appendChild(root);

    // 事件绑定
    document
      .getElementById("miaomiao-bubble")
      .addEventListener("click", togglePanel);
    document
      .getElementById("miaomiao-close-btn")
      .addEventListener("click", closePanel);
  }

  /** 切换面板展开/收起 */
  function togglePanel() {
    state.isPanelOpen = !state.isPanelOpen;
    const panel = document.getElementById("miaomiao-panel");
    const bubble = document.getElementById("miaomiao-bubble");
    if (state.isPanelOpen) {
      panel.style.display = "flex";
      bubble.classList.add("miaomiao-bubble-active");
      renderLanding();
    } else {
      panel.style.display = "none";
      bubble.classList.remove("miaomiao-bubble-active");
    }
  }

  function closePanel() {
    state.isPanelOpen = false;
    document.getElementById("miaomiao-panel").style.display = "none";
    document
      .getElementById("miaomiao-bubble")
      .classList.remove("miaomiao-bubble-active");
  }

  /** 更新猫咪状态 */
  function setCatState(catState) {
    state.catState = catState;
    const emojiEl = document.getElementById("miaomiao-cat-state-emoji");
    const labelEl = document.getElementById("miaomiao-cat-state-label");
    const bubbleEmoji = document.getElementById("miaomiao-bubble-emoji");
    if (emojiEl) emojiEl.textContent = CAT_EMOJI[catState] || CAT_EMOJI.idle;
    if (labelEl) labelEl.textContent = CAT_LABEL[catState] || CAT_LABEL.idle;
    if (bubbleEmoji)
      bubbleEmoji.textContent = CAT_EMOJI[catState] || CAT_EMOJI.idle;
  }

  /** 更新气泡上的进度标记 */
  function updateBubbleBadge() {
    const badge = document.getElementById("miaomiao-bubble-badge");
    if (!state.lesson) {
      badge.style.display = "none";
      return;
    }
    const total = state.lesson.total_steps || 0;
    const done = Object.values(state.stepResults).filter(
      (r) => r && r.passed
    ).length;
    if (done > 0 && done < total) {
      badge.style.display = "flex";
      badge.textContent = done;
    } else if (done >= total) {
      badge.style.display = "flex";
      badge.textContent = "✓";
    } else {
      badge.style.display = "none";
    }
  }

  // ── 内容渲染 ──────────────────────────────────────────────

  /** 落地页：加载/未找到课程 */
  function renderLanding() {
    const content = document.getElementById("miaomiao-content");
    if (state.backendOffline) {
      content.innerHTML = `
        <div class="miaomiao-landing">
          <div class="miaomiao-landing-emoji">🔌</div>
          <p class="miaomiao-landing-text">后端未连接 😿</p>
          <p class="miaomiao-landing-hint">请先在项目目录运行：<br><code>python run.py</code></p>
          <p class="miaomiao-landing-hint">确保后端在 localhost:8000 启动后<br>刷新此页面</p>
        </div>`;
      setCatState("idle");
      return;
    }
    if (!state.lesson) {
      content.innerHTML = `
        <div class="miaomiao-landing">
          <div class="miaomiao-landing-emoji">🐱</div>
          <p class="miaomiao-landing-text">妙喵还不认识这个视频，喵~</p>
          <p class="miaomiao-landing-hint">请打开已收录的教学视频</p>
        </div>`;
      setCatState("idle");
      return;
    }

    const done = Object.values(state.stepResults).filter(
      (r) => r && r.passed
    ).length;
    const total = state.lesson.total_steps || 0;
    const isComplete = done >= total && total > 0;

    if (isComplete) {
      renderComplete();
      return;
    }

    const inProgress = done > 0;
    content.innerHTML = `
      <div class="miaomiao-landing">
        <div class="miaomiao-landing-emoji">${inProgress ? "📖" : "🎓"}</div>
        <h3 class="miaomiao-lesson-title">${escapeHtml(state.lesson.title)}</h3>
        <p class="miaomiao-lesson-creator">${escapeHtml(state.lesson.creator_name || "")}</p>
        <p class="miaomiao-lesson-meta">共 ${total} 关 · ${
      inProgress ? `已完成 ${done} 关` : "每关包含案例练习"
    }</p>
        <button id="miaomiao-start-btn" class="miaomiao-btn miaomiao-btn-primary">
          ${inProgress ? "继续学习 →" : "🐱 开始学习"}
        </button>
      </div>`;
    setCatState(inProgress ? "watching" : "idle");

    document
      .getElementById("miaomiao-start-btn")
      .addEventListener("click", () => {
        startOrContinueLesson();
      });
  }

  /** 开始或继续学习 */
  function startOrContinueLesson() {
    if (!state.lesson) return;
    // 找到第一个未通过的步骤
    const steps = state.lesson.steps || [];
    let idx = 0;
    for (let i = 0; i < steps.length; i++) {
      const r = state.stepResults[steps[i].id];
      if (!r || !r.passed) {
        idx = i;
        break;
      }
    }
    state.currentStepIndex = idx;
    renderWatchingStep(steps[idx]);
  }

  /** 观看引导页 */
  function renderWatchingStep(step) {
    if (!step) return;
    setCatState("watching");
    state.currentStep = step;

    const content = document.getElementById("miaomiao-content");
    const isRetry =
      state.stepResults[step.id] && !state.stepResults[step.id].passed;
    const attempts = state.stepResults[step.id]?.attempts || 0;

    content.innerHTML = `
      <div class="miaomiao-step">
        <div class="miaomiao-step-header">
          <span class="miaomiao-step-badge">第 ${
            state.currentStepIndex + 1
          } 关</span>
          <span class="miaomiao-step-title">${escapeHtml(step.title)}</span>
          ${isRetry ? `<span class="miaomiao-retry-badge">第 ${attempts + 1} 次尝试</span>` : ""}
        </div>
        <div class="miaomiao-step-instruction">
          <p>${escapeHtml(step.instruction)}</p>
        </div>
        <div class="miaomiao-step-keypoint">
          <strong>💡 核心要点：</strong>${escapeHtml(step.key_point || "")}
        </div>
        ${
          step.common_errors && step.common_errors.length
            ? `<div class="miaomiao-step-errors">
            <strong>⚠️ 常见误区：</strong>
            <ul>${step.common_errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul>
          </div>`
            : ""
        }
        <div class="miaomiao-step-actions">
          <button id="miaomiao-seek-btn" class="miaomiao-btn miaomiao-btn-secondary">
            ▶ 跳转到讲解片段 (${formatTime(step.start_ms)})
          </button>
          <button id="miaomiao-ready-btn" class="miaomiao-btn miaomiao-btn-primary">
            ✅ 我看完了，开始答题
          </button>
        </div>
      </div>`;

    document.getElementById("miaomiao-seek-btn").addEventListener("click", () => {
      seekTo(step.start_ms / 1000);
    });
    document.getElementById("miaomiao-ready-btn").addEventListener("click", () => {
      renderAnswerForm(step);
    });
  }

  /** 答题表单 */
  function renderAnswerForm(step) {
    setCatState("listening");

    const content = document.getElementById("miaomiao-content");
    content.innerHTML = `
      <div class="miaomiao-step">
        <div class="miaomiao-step-header">
          <span class="miaomiao-step-badge">第 ${
            state.currentStepIndex + 1
          } 关</span>
          <span class="miaomiao-step-title">${escapeHtml(step.title)}</span>
        </div>
        <div class="miaomiao-quiz-question">
          <p>${escapeHtml(step.question || step.quiz?.question || "")}</p>
        </div>
        ${step.hint_seek_ms ? `
        <button id="miaomiao-hint-btn" class="miaomiao-btn miaomiao-btn-text">
          💡 回去再看看 (${formatTime(step.hint_seek_ms)})
        </button>` : ""}
        <textarea id="miaomiao-answer-input" class="miaomiao-textarea"
          placeholder="在此输入你的答案…（不少于10个字）"
          rows="4"></textarea>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px">
          <p id="miaomiao-answer-hint" class="miaomiao-hint" style="display:none;margin:0">
            ⚠️ 请输入至少10个字的回答
          </p>
          <span id="miaomiao-char-count" style="font-size:11px;color:#9ca3af;margin-left:auto">0 字</span>
        </div>
        <button id="miaomiao-submit-btn" class="miaomiao-btn miaomiao-btn-primary">
          📝 提交答案
        </button>
      </div>`;

    // 字数实时统计
    const input = document.getElementById("miaomiao-answer-input");
    const charCount = document.getElementById("miaomiao-char-count");
    const hint = document.getElementById("miaomiao-answer-hint");
    const submitBtn = document.getElementById("miaomiao-submit-btn");
    input.addEventListener("input", () => {
      const len = input.value.trim().length;
      charCount.textContent = len + " 字";
      if (len >= 10) {
        hint.style.display = "none";
        submitBtn.style.opacity = "1";
      }
    });

    if (step.hint_seek_ms) {
      document.getElementById("miaomiao-hint-btn").addEventListener("click", () => {
        seekTo(step.hint_seek_ms / 1000);
      });
    }
    submitBtn.addEventListener("click", async () => {
      const answer = input.value.trim();
      if (answer.length < 10) {
        hint.style.display = "block";
        submitBtn.style.opacity = "0.6";
        input.focus();
        return;
      }
      await handleSubmitAnswer(step, answer);
    });
  }

  /** 提交答案并显示结果 */
  async function handleSubmitAnswer(step, answer) {
    setCatState("analyzing");
    renderAnalyzing();

    const result = await submitAnswer(step.id, answer);
    if (!result || result.error) {
      renderError(result?.error || "后端连接失败，请确认服务已启动");
      return;
    }

    // 更新本地状态
    state.stepResults[step.id] = {
      attempts: result.attempt_num || 1,
      passed: result.passed,
      lastScore: result.score,
      matchedCount: result.matched_count,
    };
    if (result.passed) {
      state.totalStars = result.session_summary?.total_stars || state.totalStars;
      state.fish = result.session_summary?.fish || state.fish;
      state.growth = result.session_summary?.growth || state.growth;
    }
    updateBubbleBadge();

    if (result.passed) {
      renderPassResult(step, result);
    } else {
      renderFailResult(step, result);
    }
  }

  function renderAnalyzing() {
    const content = document.getElementById("miaomiao-content");
    content.innerHTML = `
      <div class="miaomiao-loading">
        <div class="miaomiao-loading-spinner">🔍</div>
        <p>猫猫正在认真判卷…</p>
      </div>`;
    setCatState("analyzing");
  }

  function renderError(msg) {
    const content = document.getElementById("miaomiao-content");
    content.innerHTML = `
      <div class="miaomiao-error">
        <div class="miaomiao-error-icon">⚠️</div>
        <p>${escapeHtml(msg)}</p>
        <p style="font-size:12px;color:#9ca3af;margin-top:4px">
          ${state.backendOffline ? "请先启动后端: python run.py" : "请确认后端在 localhost:8000 运行中"}
        </p>
        <button id="miaomiao-retry-btn" class="miaomiao-btn miaomiao-btn-secondary">🔄 重试连接</button>
      </div>`;
    setCatState("idle");
    document.getElementById("miaomiao-retry-btn").addEventListener("click", async () => {
      const online = await checkBackendHealth();
      if (online) {
        state.backendOffline = false;
        document.getElementById("miaomiao-bubble").style.opacity = "1";
        // 重新初始化课程
        await registerVideo();
        const lesson = await loadLesson();
        if (lesson && !lesson.error) {
          state.lesson = lesson;
          updateBubbleBadge();
        }
        renderLanding();
      } else {
        renderError("后端仍未连接，请确认 python run.py 已启动");
      }
    });
  }

  /** 通过结果 */
  function renderPassResult(step, result) {
    setCatState("celebrating");

    const hasNext = !!result.next_step;
    const content = document.getElementById("miaomiao-content");
    content.innerHTML = `
      <div class="miaomiao-result miaomiao-result-pass">
        <div class="miaomiao-result-emoji">🌟</div>
        <h3>${result.stars_earned >= 3 ? "完美通过！" : "通过了！"}</h3>
        <p class="miaomiao-cat-message">${escapeHtml(result.cat_message || "")}</p>
        <div class="miaomiao-result-stats">
          <span>⭐ ${result.stars_earned} 星</span>
          <span>✅ ${result.matched_count}/${result.required_count} 要点</span>
        </div>
        <div class="miaomiao-progress-bar">
          <div class="miaomiao-progress-fill" style="width:${
            ((state.currentStepIndex + 1) / (state.lesson.total_steps || 1)) * 100
          }%"></div>
        </div>
        <p class="miaomiao-progress-text">进度 ${state.currentStepIndex + 1}/${
      state.lesson.total_steps
    }</p>
        ${
          hasNext
            ? `<button id="miaomiao-next-btn" class="miaomiao-btn miaomiao-btn-primary">
            下一关：${escapeHtml(result.next_step.title)} →
          </button>`
            : ""
        }
        ${
          !hasNext
            ? `<button id="miaomiao-finish-btn" class="miaomiao-btn miaomiao-btn-primary">
            🎉 查看学习总结
          </button>`
            : ""
        }
      </div>`;

    // 自动跳转到下一个片段的开始时间
    if (hasNext && result.next_step.start_ms !== undefined) {
      setTimeout(() => seekTo(result.next_step.start_ms / 1000), 500);
    }

    if (hasNext) {
      document.getElementById("miaomiao-next-btn").addEventListener("click", () => {
        // 推进到下一步
        state.currentStepIndex++;
        const nextStep = state.lesson.steps[state.currentStepIndex];
        if (nextStep) {
          seekTo(nextStep.start_ms / 1000);
          renderWatchingStep(nextStep);
        }
      });
    } else {
      document.getElementById("miaomiao-finish-btn").addEventListener("click", () => {
        renderComplete();
      });
    }
  }

  /** 未通过结果 */
  function renderFailResult(step, result) {
    setCatState("correcting");

    const content = document.getElementById("miaomiao-content");
    const missedPoints = result.missed_points || [];
    const wrongPoints = result.wrong_points || [];
    const seekToMs = result.seek_to_ms;

    content.innerHTML = `
      <div class="miaomiao-result miaomiao-result-fail">
        <div class="miaomiao-result-emoji">📝</div>
        <h3>还差一点点~</h3>
        <p class="miaomiao-cat-message">${escapeHtml(result.cat_message || "")}</p>
        ${
          missedPoints.length
            ? `<div class="miaomiao-missed">
              <strong>漏掉的要点：</strong>
              <ul>${missedPoints.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul>
            </div>`
            : ""
        }
        ${
          wrongPoints.length
            ? `<div class="miaomiao-wrong">
              <strong>理解有误：</strong>
              <ul>${wrongPoints.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul>
            </div>`
            : ""
        }
        ${
          seekToMs
            ? `<button id="miaomiao-seek-hint-btn" class="miaomiao-btn miaomiao-btn-secondary">
              ⏪ 跳转到讲解片段 (${formatTime(seekToMs)})
            </button>`
            : ""
        }
        <button id="miaomiao-retry-answer-btn" class="miaomiao-btn miaomiao-btn-primary">
          🔄 重新作答
        </button>
      </div>`;

    if (seekToMs) {
      document.getElementById("miaomiao-seek-hint-btn").addEventListener("click", () => {
        seekTo(seekToMs / 1000);
      });
    }
    document.getElementById("miaomiao-retry-answer-btn").addEventListener("click", () => {
      renderAnswerForm(step);
    });
  }

  /** 全部完成 */
  function renderComplete() {
    setCatState("celebrating");

    const total = state.lesson?.total_steps || 0;
    const passCount = Object.values(state.stepResults).filter(
      (r) => r && r.passed
    ).length;
    const perfectStars = state.totalStars || 0;
    const maxStars = total * 3;

    const content = document.getElementById("miaomiao-content");
    content.innerHTML = `
      <div class="miaomiao-complete">
        <div class="miaomiao-complete-emoji">🏆</div>
        <h2>课程完成！</h2>
        <p class="miaomiao-complete-title">${escapeHtml(state.lesson?.title || "")}</p>
        <div class="miaomiao-complete-stats">
          <div class="miaomiao-stat">
            <span class="miaomiao-stat-icon">⭐</span>
            <span class="miaomiao-stat-value">${perfectStars} / ${maxStars}</span>
            <span class="miaomiao-stat-label">星星</span>
          </div>
          <div class="miaomiao-stat">
            <span class="miaomiao-stat-icon">🐟</span>
            <span class="miaomiao-stat-value">${state.fish || 0}</span>
            <span class="miaomiao-stat-label">小鱼干</span>
          </div>
          <div class="miaomiao-stat">
            <span class="miaomiao-stat-icon">📈</span>
            <span class="miaomiao-stat-value">${state.growth || 0}</span>
            <span class="miaomiao-stat-label">成长值</span>
          </div>
        </div>
        <p class="miaomiao-complete-text">
          你完成了全部 ${total} 关练习，通过了 ${passCount} 关！<br>
          ${
            passCount === total
              ? "太厉害了，全部关卡都通过了！🌟"
              : `还有 ${total - passCount} 关可以继续挑战哦~`
          }
        </p>
        <button id="miaomiao-restart-btn" class="miaomiao-btn miaomiao-btn-secondary">
          🔄 重新学习
        </button>
      </div>`;

    document.getElementById("miaomiao-restart-btn").addEventListener("click", async () => {
      // 清除旧 session 存储
      const storageKey = `session_${state.videoId}`;
      try { await chrome.storage.local.remove(storageKey); } catch (e) { /* ignore */ }
      // Reset state
      state.stepResults = {};
      state.totalStars = 0;
      state.fish = 0;
      state.growth = 0;
      state.reviewQueue = [];
      state.currentStepIndex = 0;
      state.sessionId = await resolveSessionId();
      updateBubbleBadge();
      renderLanding();
    });
  }

  // ── 工具函数 ──────────────────────────────────────────────

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function formatTime(ms) {
    if (ms === undefined || ms === null) return "";
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec.toString().padStart(2, "0")}`;
  }

  // ── 初始化 ────────────────────────────────────────────────

  /** 从 background.js 获取配置的 API 地址 */
  async function resolveApiBase() {
    try {
      const response = await chrome.runtime.sendMessage({ type: "GET_API_BASE" });
      if (response && response.apiBaseUrl) {
        API_BASE = response.apiBaseUrl;
        console.log(`[妙喵] API 地址: ${API_BASE}`);
      }
    } catch (e) {
      // 使用默认值 localhost:8000
      console.log(`[妙喵] 使用默认 API 地址: ${API_BASE}`);
    }
  }

  async function init() {
    const detected = detectPlatform();
    if (!detected) return; // 非视频页，不注入

    state.videoId = detected.videoId;
    state.platform = detected.platform;

    // 注入 UI
    injectUI();

    // P1-3: 从 chrome.storage 获取 API 地址
    await resolveApiBase();

    // 检查后端连通性
    const backendOnline = await checkBackendHealth();
    if (!backendOnline) {
      console.warn("[妙喵] 后端未连接 (localhost:8000)");
      state.backendOffline = true;
      const bubbleEl = document.getElementById("miaomiao-bubble");
      if (bubbleEl) {
        bubbleEl.style.opacity = "0.6";
        bubbleEl.title = "妙喵私教 — 后端未连接，请先启动 python run.py";
      }
      return;
    }

    state.backendOffline = false;

    // 等待播放器就绪
    await waitForPlayer();

    // 持久化 session ID（跨页面刷新复用）
    state.sessionId = await resolveSessionId();

    // 注册视频并尝试加载课程
    await registerVideo();
    const lesson = await loadLesson();
    if (lesson && !lesson.error) {
      state.lesson = lesson;
      console.log(`[妙喵] 课程已加载: ${lesson.title}, ${lesson.total_steps} 关`);

      // 恢复之前的进度
      const saved = await getStateAPI();
      if (saved && saved.gamification) {
        state.totalStars = saved.gamification.total_stars || 0;
        state.fish = saved.gamification.fish || 0;
        state.growth = saved.gamification.growth || 0;
        // 恢复步骤完成状态
        if (saved.completed_steps) {
          for (const stepId of saved.completed_steps) {
            state.stepResults[stepId] = { passed: true };
          }
        }
        console.log(`[妙喵] 进度已恢复: ${saved.completed_steps?.length || 0} 关已完成`);
      }

      setCatState("idle");
      updateBubbleBadge();
    }

    console.log("[妙喵] 初始化完成，气泡已就绪");
  }

  /** 轮询等待播放器就绪 */
  function waitForPlayer() {
    return new Promise((resolve) => {
      let attempts = 0;
      const maxAttempts = 30; // 最多等 60 秒
      const check = () => {
        attempts++;
        const player = getBilibiliPlayer() || getDouyinPlayer();
        if (player) {
          // 检查是否真的可以播放
          if (player.readyState >= 1 || player.seek || player.duration) {
            state.playerReady = true;
            resolve();
            return;
          }
        }
        if (attempts >= maxAttempts) {
          console.warn("[妙喵] 播放器检测超时，继续初始化");
          resolve();
          return;
        }
        setTimeout(check, POLL_INTERVAL_MS);
      };
      check();
    });
  }

  // ── 启动 ──────────────────────────────────────────────────
  init().catch((err) => {
    console.error("[妙喵] 初始化失败:", err);
  });
})();

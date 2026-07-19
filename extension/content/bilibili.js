/**
 * 妙喵私教 — B站内容脚本
 * 注入 bilibili.com/video/* 页面
 * 复用与抖音脚本相同的核心逻辑，直接读取B站字幕
 */

const API_BASE = "http://8.130.190.169:8000";
const PLATFORM = "bilibili";

let state = {
  open: false,
  videoId: null,
  videoTitle: null,
  catState: "idle",
  lessonId: null,
  sessionId: null,
  currentStep: null,
  lessonMode: false,
};

// ── 猫状态动画 + 音效（购置方案 §四）────────────────────
const CAT_LOTTIE_FILES = {
  idle: "cat-lovely.json",
  watching: "cat-playing.json",
  analyzing: "cat-loading.json",
  celebrating: "cat-dance.json",
  failed: "cat-sad.json",
  reward: "cat-eating-fish.json",
  levelup: "cat-dance.json",
};
let catLottieAnim = null;
let bubbleLottieAnim = null;
let panelOpenedOnce = false;

function setCatState(s) {
  state.catState = s;
  const container = document.getElementById("mm-cat-lottie");
  const bubble = document.getElementById("mm-bubble-lottie");
  if (typeof lottie === "undefined") return;
  const file = CAT_LOTTIE_FILES[s];
  if (!file) return;
  const path = chrome.runtime.getURL("lottie/" + file);
  if (container) {
    if (catLottieAnim) { catLottieAnim.destroy(); catLottieAnim = null; }
    catLottieAnim = lottie.loadAnimation({
      container, renderer: "svg", loop: true, autoplay: true, path,
    });
  }
  if (bubble) {
    if (bubbleLottieAnim) { bubbleLottieAnim.destroy(); bubbleLottieAnim = null; }
    bubbleLottieAnim = lottie.loadAnimation({
      container: bubble, renderer: "svg", loop: true, autoplay: true, path,
    });
  }
}

function fireConfetti(times = 1) {
  if (typeof confetti === "undefined") return;
  confetti({ particleCount: 80, origin: { y: 0.8 } });
  for (let i = 1; i < times; i++) {
    setTimeout(() => confetti({ particleCount: 60, origin: { y: 0.7 } }), 250 * i);
  }
}

// 星星逐颗点亮（每颗 200ms + badge 音，购置方案 §4.3）
function lightStars(container, stars) {
  const row = document.createElement("div");
  row.className = "mm-stars";
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
  for (let i = 0; i < 3; i++) {
    const s = document.createElement("span");
    s.textContent = "☆";
    row.appendChild(s);
    if (i < stars) {
      setTimeout(() => {
        s.textContent = "⭐";
        MiaoSound.play("badge");
      }, 200 * (i + 1));
    }
  }
}

function getVideo() {
  return document.querySelector("video");
}

function getCurrentTime() {
  const v = getVideo();
  return v ? Math.floor(v.currentTime) : 0;
}

function seekTo(seconds) {
  const v = getVideo();
  if (!v) return;
  MiaoSound.play("seek");
  v.currentTime = seconds;
  v.play();
}

function extractBvid() {
  const m = location.pathname.match(/\/(BV\w+)/i);
  return m ? m[1] : null;
}

function extractTitle() {
  const el =
    document.querySelector(".video-title") ||
    document.querySelector("h1.title") ||
    document.querySelector('meta[property="og:title"]');
  return el
    ? (el.getAttribute?.("content") || el.textContent || "").trim()
    : "";
}

async function fetchWithTimeout(url, opts = {}, ms = 5000) {
  try {
    const resp = await chrome.runtime.sendMessage({
      type: "FETCH",
      url,
      options: opts,
      timeout: ms,
    });
    if (resp.error) throw new Error(resp.error);
    return {
      ok: resp.ok,
      status: resp.status,
      json: () => Promise.resolve(JSON.parse(resp.text)),
    };
  } catch (e) {
    throw e;
  }
}

async function registerVideo(bvid, title) {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/ext/register_video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: bvid, title, platform: PLATFORM }),
    });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

async function loadLesson(videoId) {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/lesson/load`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, platform: PLATFORM }),
    }, 5000);
    return res.ok ? await res.json() : null;
  } catch { return null; }
}

async function submitQuiz(answer, stepId) {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/lesson/quiz_submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        lesson_id: state.lessonId,
        step_id: stepId,
        answer,
        current_time_sec: getCurrentTime(),
      }),
    }, 10000);
    return res.ok ? await res.json() : null;
  } catch { return null; }
}

function startSession(lessonData) {
  state.lessonId = lessonData.lesson_id;
  state.sessionId = "session_" + Date.now();
  state.lessonMode = true;
  state.currentStep = lessonData.steps[0];

  // 切换快捷按钮到练习模式
  const qa = document.getElementById("mm-quick-actions");
  if (qa) qa.innerHTML = `
    <button class="mm-quick-btn" data-action="quiz_submit">提交答案</button>
    <button class="mm-quick-btn" data-action="hint">给我提示</button>
    <button class="mm-quick-btn" data-action="free_chat">自由问答</button>
  `;
  // 重新绑定
  document.querySelectorAll(".mm-quick-btn").forEach(btn => {
    btn.addEventListener("click", () => handleLessonAction(btn.dataset.action));
  });

  // 开始第一步
  showLessonStep(state.currentStep);
}

function showLessonStep(step) {
  state.currentStep = step;
  setCatState("watching");
  const v = getVideo();
  if (v) { v.currentTime = step.start_ms / 1000; v.play(); }
  appendMessage(
    `📚 第 ${step.id.replace("step_", "")} 关：${step.title}\n\n${step.instruction}\n\n看到 ${formatTime(step.end_ms / 1000)} 后，妙喵会出题考你～`,
    "cat"
  );
  // 监控到达 end_ms 时自动出题
  scheduleQuiz(step);
}

let quizTimer = null;
let quizCheckInterval = null;
function scheduleQuiz(step) {
  clearTimeout(quizTimer);
  if (quizCheckInterval) { clearInterval(quizCheckInterval); quizCheckInterval = null; }
  quizCheckInterval = setInterval(() => {
    const current = getCurrentTime() * 1000;
    if (current >= step.end_ms) {
      clearInterval(quizCheckInterval);
      quizCheckInterval = null;
      promptQuiz(step);
    }
  }, 2000);
}

function promptQuiz(step) {
  const v = getVideo();
  if (v) v.pause();
  appendMessage(`⏸️ 先暂停一下！\n\n📝 ${step.question}\n\n把答案打在输入框发给我，支持口语化回答～`, "cat");
  // 设置标记：下次 send 是答题
  state.pendingQuizStep = step;
  const input = document.getElementById("mm-input");
  if (input) input.placeholder = "输入你的答案...";
}

async function handleLessonAction(action) {
  if (action === "quiz_submit") {
    const input = document.getElementById("mm-input");
    const answer = input?.value?.trim();
    if (!answer) { appendMessage("先写个答案再提交哦 :3", "cat"); return; }
    await submitAndShow(answer, state.currentStep);
  } else if (action === "hint") {
    if (state.currentStep?.hint_seek_ms != null) {
      seekTo(state.currentStep.hint_seek_ms / 1000);
      appendMessage(`🔍 帮你跳到 ${formatTime(state.currentStep.hint_seek_ms / 1000)} 看关键片段`, "cat");
    }
  } else if (action === "free_chat") {
    state.pendingQuizStep = null;
    const input = document.getElementById("mm-input");
    if (input) input.placeholder = "问妙喵...";
    appendMessage("切换到自由问答模式，尽管问吧！", "cat");
  }
}

async function submitAndShow(answer, step) {
  showTyping();
  const result = await submitQuiz(answer, step.id);
  removeTyping();
  if (!result) { appendMessage("提交失败，检查一下后端是否在运行", "cat"); return; }

  // 判卷结果：音效 + 状态猫 + 撒花/星星（购置方案 §4.3）
  if (result.passed) {
    const stars = typeof result.stars === "number" ? result.stars : 0;
    MiaoSound.play(stars >= 3 ? "perfect" : "pass");
    setCatState("celebrating");
    fireConfetti();
    if (stars > 0) lightStars(document.getElementById("mm-messages"), stars);
  } else {
    MiaoSound.play("fail");
    setCatState("failed");
  }

  const input = document.getElementById("mm-input");
  if (input) { input.value = ""; input.placeholder = "问妙喵..."; }
  state.pendingQuizStep = null;

  // 显示妙喵评价
  const c = document.getElementById("mm-messages");
  const div = document.createElement("div");
  div.className = "mm-msg mm-cat";
  div.textContent = result.cat_message;
  if (result.seek_to_ms != null && !result.passed) {
    const ts = document.createElement("div");
    ts.className = "mm-timestamp-ref";
    ts.textContent = `⏪ 跳回 ${formatTime(result.seek_to_ms / 1000)} 再看一遍`;
    ts.addEventListener("click", () => seekTo(result.seek_to_ms / 1000));
    div.appendChild(ts);
  }
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;

  // 通过了 → 找下一步
  if (result.passed && result.next_step) {
    setTimeout(() => {
      appendMessage(`🌟 太棒了！准备好进入下一关了吗？`, "cat");
      const btn = document.createElement("button");
      btn.className = "mm-quick-btn";
      btn.textContent = "→ 继续下一关";
      btn.style.margin = "8px auto";
      btn.addEventListener("click", () => {
        btn.remove();
        showLessonStep(result.next_step);
      });
      c.appendChild(btn);
      c.scrollTop = c.scrollHeight;
    }, 800);
  } else if (result.passed && !result.next_step) {
    setTimeout(() => {
      appendMessage("🎉 全部通关！罗翔老师的正当防卫精讲你已掌握，小鱼干满满！", "cat");
      setCatState("levelup");
      MiaoSound.play("levelup");
      fireConfetti(3);
    }, 800);
  }
}

// ── 语音输入 ─────────────────────────────────────────────
let voiceRecording = false;

function setVoiceState(text, active = false) {
  const el = document.getElementById("mm-voice-state");
  if (!el) return;
  el.textContent = text;
  el.classList.toggle("mm-voice-active", active);
}

function handleVoiceStart() {
  if (!MiaoVoice || !MiaoVoice.isSupported()) {
    appendMessage("浏览器不支持录音", "cat");
    return;
  }
  voiceRecording = true;
  setVoiceState("正在听…", true);
  const mic = document.getElementById("mm-mic");
  if (mic) mic.classList.add("mm-listening");
  MiaoVoice.start((blob, err) => {
    voiceRecording = false;
    setVoiceState("", false);
    if (mic) mic.classList.remove("mm-listening");
    if (err || !blob) {
      appendMessage(err ? `录音失败：${err}` : "没有录制到声音", "cat");
      return;
    }
    void handleVoiceSubmit(blob);
  });
}

function handleVoiceStop() {
  if (voiceRecording && MiaoVoice) {
    MiaoVoice.stop();
  }
}

async function handleVoiceSubmit(blob) {
  const input = document.getElementById("mm-input");
  if (input) input.placeholder = "识别中…";
  appendMessage("🎤 识别中…", "user");

  const res = await MiaoVoice.upload(blob, API_BASE);
  // 移除 "识别中…" 临时消息
  const tempMsg = document.querySelector(".mm-msg.mm-user:last-child");
  if (tempMsg && tempMsg.textContent === "🎤 识别中…") tempMsg.remove();

  if (!res.ok || !res.text) {
    appendMessage(res.text ? `没有听清：${res.error}` : "语音没有识别到内容，请再说一遍", "cat");
    if (input) input.placeholder = state.pendingQuizStep ? "输入你的答案..." : "问妙喵...";
    return;
  }

  appendMessage(res.text, "user");

  if (state.pendingQuizStep) {
    await submitAndShow(res.text, state.pendingQuizStep);
  } else {
    await sendMessage(res.text);
  }
}

async function chat(message, videoId, currentTimeSec) {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/api/ext/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          video_id: videoId,
          platform: PLATFORM,
          current_time_sec: currentTimeSec,
        }),
      },
      15000,
    );
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

function buildUI() {
  if (document.getElementById("miaomiao-root")) return;
  const root = document.createElement("div");
  root.id = "miaomiao-root";
  root.innerHTML = `
    <div id="mm-panel">
      <div id="mm-header">
        <div id="mm-cat-lottie" style="width:36px;height:36px;flex:0 0 36px"></div>
        <span id="mm-header-title">妙喵私教 · B站版</span>
        <span id="mm-state-badge">准备中</span>
        <button id="mm-site" title="访问个人网站">🏠</button>
        <button id="mm-mute" title="音效开关">🔊</button>
        <button id="mm-close">✕</button>
      </div>
      <div id="mm-video-info">正在识别视频...</div>
      <div id="mm-messages"></div>
      <div id="mm-quick-actions">
        <button class="mm-quick-btn" data-action="explain">讲解当前片段</button>
        <button class="mm-quick-btn" data-action="quiz">出一道题</button>
        <button class="mm-quick-btn" data-action="replay">回到关键点</button>
      </div>
      <div id="mm-input-area">
        <div id="mm-voice-state"></div>
        <input id="mm-input" type="text" placeholder="问妙喵..." />
        <button id="mm-mic" title="按住说话">🎤</button>
        <button id="mm-send">➤</button>
      </div>
    </div>
    <button id="mm-bubble" title="妙喵私教"><div id="mm-bubble-lottie"></div></button>
  `;
  document.body.appendChild(root);
  restorePetPos(root);
  bindEvents(root);
  MiaoPet.init(root, { setCatState, getCatState: () => state.catState });
}

// 桌宠拖拽：按住可拖动，松开距离 <5px 视为点击（小雅桌宠式交互）
const PET_SIZE = 84;
function enablePetDrag(root) {
  const bubble = root.querySelector("#mm-bubble");
  let dragging = false, moved = false, startX = 0, startY = 0, startLeft = 0, startTop = 0;
  bubble.addEventListener("pointerdown", (e) => {
    dragging = true; moved = false;
    startX = e.clientX; startY = e.clientY;
    const rect = root.getBoundingClientRect();
    startLeft = rect.left; startTop = rect.top;
    bubble.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  bubble.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX, dy = e.clientY - startY;
    if (!moved && Math.hypot(dx, dy) < 5) return;
    moved = true;
    const left = Math.min(Math.max(0, startLeft + dx), window.innerWidth - PET_SIZE);
    const top = Math.min(Math.max(0, startTop + dy), window.innerHeight - PET_SIZE);
    root.style.left = left + "px";
    root.style.top = top + "px";
    root.style.right = "auto";
    root.style.bottom = "auto";
    root.classList.toggle("mm-flip", top < 360);
  });
  bubble.addEventListener("pointerup", () => {
    if (!dragging) return;
    dragging = false;
    if (!moved) { togglePanel(); return; }
    const rect = root.getBoundingClientRect();
    try { chrome.storage.local.set({ mm_pet_pos: { left: rect.left, top: rect.top } }); } catch {}
  });
}

function restorePetPos(root) {
  try {
    chrome.storage.local.get("mm_pet_pos", (d) => {
      const p = d && d.mm_pet_pos;
      if (!p) return;
      const left = Math.min(Math.max(0, p.left), window.innerWidth - PET_SIZE);
      const top = Math.min(Math.max(0, p.top), window.innerHeight - PET_SIZE);
      root.style.left = left + "px";
      root.style.top = top + "px";
      root.style.right = "auto";
      root.style.bottom = "auto";
      root.classList.toggle("mm-flip", top < 360);
    });
  } catch {}
}

function bindEvents(root) {
  enablePetDrag(root);
  root.querySelector("#mm-close").addEventListener("click", () => togglePanel(false));
  root.querySelector("#mm-mute").addEventListener("click", () => {
    const muted = MiaoSound.toggleMute();
    root.querySelector("#mm-mute").textContent = muted ? "🔇" : "🔊";
  });
  root.querySelector("#mm-send").addEventListener("click", handleSend);
  root.querySelector("#mm-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  });

  const micBtn = root.querySelector("#mm-mic");
  if (micBtn) {
    micBtn.addEventListener("mousedown", handleVoiceStart);
    micBtn.addEventListener("mouseup", handleVoiceStop);
    micBtn.addEventListener("mouseleave", handleVoiceStop);
    micBtn.addEventListener("touchstart", (e) => { e.preventDefault(); handleVoiceStart(); });
    micBtn.addEventListener("touchend", (e) => { e.preventDefault(); handleVoiceStop(); });
  }

  root.querySelector("#mm-site")?.addEventListener("click", () => {
    const siteUrl = "https://miaomiao-cat.duckdns.org";
    const params = state.videoId ? `?video_id=${encodeURIComponent(state.videoId)}` : "";
    window.open(`${siteUrl}/community${params}`, "_blank");
  });

  root.querySelectorAll(".mm-quick-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const queries = {
        explain: "解释我当前在看的这段视频讲了什么",
        quiz: "针对这段内容给我出一道练习题",
        replay: "找到最重要的知识点，告诉我跳回哪里重看",
      };
      sendMessage(queries[btn.dataset.action] || btn.dataset.action);
    });
  });
}

function togglePanel(force) {
  const panel = document.getElementById("mm-panel");
  if (!panel) return;
  state.open = force !== undefined ? force : !state.open;
  panel.classList.toggle("mm-open", state.open);
  if (state.open && !panelOpenedOnce) {
    panelOpenedOnce = true;
    MiaoSound.play("meow");
  }
}

function appendMessage(text, role = "cat") {
  const c = document.getElementById("mm-messages");
  if (!c) return;
  const div = document.createElement("div");
  div.className = `mm-msg mm-${role}`;
  div.textContent = text;
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
}

function appendCatResponse(data) {
  const c = document.getElementById("mm-messages");
  if (!c) return;
  const div = document.createElement("div");
  div.className = "mm-msg mm-cat";
  div.textContent = data.answer || data.message || "";
  if (data.seek_to_sec != null) {
    const ts = document.createElement("div");
    ts.className = "mm-timestamp-ref";
    const fmt = formatTime(data.seek_to_sec);
    ts.textContent = `⏩ 跳到 ${fmt}`;
    ts.addEventListener("click", () => seekTo(data.seek_to_sec));
    div.appendChild(ts);
  }
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
}

function showTyping() {
  const c = document.getElementById("mm-messages");
  if (!c) return;
  MiaoSound.startThink();
  setCatState("analyzing");
  const el = document.createElement("div");
  el.className = "mm-typing";
  el.id = "mm-typing-indicator";
  el.innerHTML = "<span></span><span></span><span></span>";
  c.appendChild(el);
  c.scrollTop = c.scrollHeight;
}

function removeTyping() {
  document.getElementById("mm-typing-indicator")?.remove();
  MiaoSound.stopThink();
}

async function sendMessage(text) {
  if (!text.trim()) return;
  const input = document.getElementById("mm-input");
  if (input) input.value = "";
  appendMessage(text, "user");

  // 答题模式：发送即为提交
  if (state.pendingQuizStep) {
    await submitAndShow(text, state.pendingQuizStep);
    return;
  }

  showTyping();
  const result = await chat(text, state.videoId, getCurrentTime());
  removeTyping();
  if (!result) {
    appendMessage("连不上本地服务（localhost:8000），请先启动 `python run.py`", "cat");
    return;
  }
  appendCatResponse(result);
}

async function handleSend() {
  const input = document.getElementById("mm-input");
  await sendMessage(input?.value?.trim() || "");
}

async function onVideoDetected(bvid, title) {
  if (state.videoId === bvid) return;
  state.videoId = bvid;
  state.videoTitle = title;
  state.lessonMode = false;
  state.pendingQuizStep = null;
  document.getElementById("mm-video-info").textContent = `📹 ${title.slice(0, 40)}`;
  document.getElementById("mm-state-badge").textContent = "识别中...";
  document.getElementById("mm-messages").innerHTML = "";

  // 并行注册视频 + 检查是否有 lesson
  const [meta, lesson] = await Promise.all([
    registerVideo(bvid, title),
    loadLesson(bvid),
  ]);

  const badge = document.getElementById("mm-state-badge");
  MiaoPet.greet();
  if (lesson && lesson.lesson_id) {
    badge.textContent = "练习模式";
    appendMessage(
      `✨ 这是一节结构化课程：${lesson.title}\n共 ${lesson.total_steps} 关卡，妙喵会带你一步步学！\n\n准备好了吗？`,
      "cat"
    );
    // 显示开始按钮
    const c = document.getElementById("mm-messages");
    const btn = document.createElement("button");
    btn.className = "mm-quick-btn";
    btn.textContent = "🚀 开始学习！";
    btn.style.margin = "8px auto";
    btn.addEventListener("click", () => { btn.remove(); startSession(lesson); });
    c.appendChild(btn);
  } else if (meta) {
    badge.textContent = "已就绪";
    appendMessage(
      `找到啦！这条视频有 ${meta.subtitle_count ?? "?"} 句字幕。\n想让我讲解片段、出题练习，还是直接问问题？`,
      "cat"
    );
  } else {
    badge.textContent = "字幕加载中";
    appendMessage("视频已识别，字幕还在加载中，可以先问我问题 :3", "cat");
  }
}

function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function checkPage() {
  const bvid = extractBvid();
  if (!bvid || bvid === state.videoId) return;
  onVideoDetected(bvid, extractTitle());
}

function init() {
  buildUI();
  setCatState("idle");
  checkPage();
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(checkPage, 1500);
    }
  }).observe(document.body, { childList: true, subtree: true });
  setInterval(checkPage, 5000);

  chrome.runtime.onMessage?.addListener((req, _sender, sendResponse) => {
    if (req?.action === "summon") {
      togglePanel(true);
      MiaoPet.say("喵～我在这儿！", 3500, "celebrating");
      sendResponse({ ok: true });
    }
    return true;
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

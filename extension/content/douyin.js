/**
 * 妙喵私教 — 抖音内容脚本
 * 注入 douyin.com/video/* 页面
 */

const API_BASE = "http://localhost:8000";
const PLATFORM = "douyin";

// ── 状态 ────────────────────────────────────────────────
let state = {
  open: false,
  videoId: null,
  videoTitle: null,
  videoMeta: null,   // 从后端拿到的B站对应信息
  messages: [],
  catState: "idle",  // idle / watching / analyzing / correcting / celebrating
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

// ── DOM 工具 ─────────────────────────────────────────────
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

function extractDouyinVideoId() {
  const m = location.pathname.match(/\/video\/(\d+)/);
  return m ? m[1] : null;
}

function extractTitle() {
  // 抖音视频页标题在多个位置，优先取 og:title
  const og = document.querySelector('meta[property="og:title"]');
  if (og) return og.getAttribute("content") || "";
  const title = document.querySelector("title");
  return title ? title.textContent.replace(" - 抖音", "").trim() : "";
}

// ── 后端通信 ─────────────────────────────────────────────
async function fetchWithTimeout(url, opts = {}, timeoutMs = 5000) {
  try {
    const resp = await chrome.runtime.sendMessage({
      type: "FETCH",
      url,
      options: opts,
      timeout: timeoutMs,
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

async function registerVideo(videoId, title, platform) {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/ext/register_video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, title, platform }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
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
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// ── UI 构建 ─────────────────────────────────────────────
function buildUI() {
  if (document.getElementById("miaomiao-root")) return;

  const root = document.createElement("div");
  root.id = "miaomiao-root";
  root.innerHTML = `
    <div id="mm-panel">
      <div id="mm-header">
        <div id="mm-cat-lottie" style="width:36px;height:36px;flex:0 0 36px"></div>
        <span id="mm-header-title">妙喵私教</span>
        <span id="mm-state-badge">准备中</span>
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
  const panel = root.querySelector("#mm-panel");
  const closeBtn = root.querySelector("#mm-close");
  const input = root.querySelector("#mm-input");
  const sendBtn = root.querySelector("#mm-send");

  enablePetDrag(root);
  closeBtn.addEventListener("click", () => togglePanel(false));

  const muteBtn = root.querySelector("#mm-mute");
  muteBtn.addEventListener("click", () => {
    const muted = MiaoSound.toggleMute();
    muteBtn.textContent = muted ? "🔇" : "🔊";
  });

  sendBtn.addEventListener("click", handleSend);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  const micBtn = root.querySelector("#mm-mic");
  if (micBtn) {
    micBtn.addEventListener("mousedown", handleVoiceStart);
    micBtn.addEventListener("mouseup", handleVoiceStop);
    micBtn.addEventListener("mouseleave", handleVoiceStop);
    micBtn.addEventListener("touchstart", (e) => { e.preventDefault(); handleVoiceStart(); });
    micBtn.addEventListener("touchend", (e) => { e.preventDefault(); handleVoiceStop(); });
  }

  root.querySelectorAll(".mm-quick-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const queries = {
        explain: "解释我当前在看的这段视频讲了什么",
        quiz: "针对这段内容给我出一道练习题",
        replay: "找到最重要的知识点，告诉我跳回哪里重看",
      };
      sendMessage(queries[action] || action);
    });
  });
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
    if (input) input.placeholder = "问妙喵...";
    return;
  }

  appendMessage(res.text, "user");
  await sendMessage(res.text);
}

function togglePanel(forceOpen) {
  const panel = document.getElementById("mm-panel");
  if (!panel) return;
  state.open = forceOpen !== undefined ? forceOpen : !state.open;
  panel.classList.toggle("mm-open", state.open);
  if (state.open && !panelOpenedOnce) {
    panelOpenedOnce = true;
    MiaoSound.play("meow");
  }
}

// ── 消息处理 ─────────────────────────────────────────────
function appendMessage(text, role = "cat") {
  const container = document.getElementById("mm-messages");
  if (!container) return;

  const div = document.createElement("div");
  div.className = `mm-msg mm-${role}`;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendCatResponse(data) {
  const container = document.getElementById("mm-messages");
  if (!container) return;

  // 主回答
  const div = document.createElement("div");
  div.className = "mm-msg mm-cat";
  div.textContent = data.answer || data.message || "";

  // 时间戳引用按钮
  if (data.seek_to_sec != null) {
    const ts = document.createElement("div");
    ts.className = "mm-timestamp-ref";
    const fmt = formatTime(data.seek_to_sec);
    ts.textContent = `⏩ 跳到 ${fmt}`;
    ts.addEventListener("click", () => {
      seekTo(data.seek_to_sec);
      appendMessage(`已跳到 ${fmt}`, "cat");
    });
    div.appendChild(ts);
  }

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  const container = document.getElementById("mm-messages");
  if (!container) return null;
  MiaoSound.startThink();
  setCatState("analyzing");
  const el = document.createElement("div");
  el.className = "mm-typing";
  el.innerHTML = "<span></span><span></span><span></span>";
  el.id = "mm-typing-indicator";
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return el;
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
  const typing = showTyping();

  const result = await chat(text, state.videoId, getCurrentTime());
  removeTyping();

  if (!result) {
    appendMessage("连不上本地服务（localhost:8000），请先启动后端 `python run.py`", "cat");
    return;
  }
  appendCatResponse(result);
}

async function handleSend() {
  const input = document.getElementById("mm-input");
  const text = input?.value?.trim();
  if (!text) return;
  await sendMessage(text);
}

// ── 视频信息更新 ─────────────────────────────────────────
function updateStateBadge(text) {
  const badge = document.getElementById("mm-state-badge");
  if (badge) badge.textContent = text;
}

function updateVideoInfo(title) {
  const el = document.getElementById("mm-video-info");
  if (el) el.textContent = title ? `📹 ${title.slice(0, 40)}` : "未识别到视频";
}

async function onVideoDetected(videoId, title) {
  if (state.videoId === videoId) return;
  state.videoId = videoId;
  state.videoTitle = title;
  state.messages = [];

  updateVideoInfo(title);
  updateStateBadge("识别中...");
  MiaoPet.greet();

  const meta = await registerVideo(videoId, title, PLATFORM);
  state.videoMeta = meta;

  if (meta?.matched_bilibili) {
    updateStateBadge("已就绪");
    updateVideoInfo(`${title} (已匹配B站字幕)`);
    // 主动问候
    document.getElementById("mm-messages").innerHTML = "";
    appendMessage(
      `猫猫找到这期视频的完整字幕啦！\n` +
      `匹配到：${meta.matched_bilibili.title}\n` +
      `有 ${meta.matched_bilibili.subtitle_count} 句字幕可以用。\n\n` +
      `想让我讲解当前片段、出题练习，还是有什么具体问题？`,
      "cat"
    );
  } else {
    updateStateBadge("字幕缺失");
    appendMessage(
      `猫猫找到视频了，但还没有对应的字幕数据。\n` +
      `可以先问我问题，我会尽力根据视频标题回答 :3`,
      "cat"
    );
  }
}

// ── 页面监听 ─────────────────────────────────────────────
function checkPage() {
  const videoId = extractDouyinVideoId();
  if (!videoId || videoId === state.videoId) return;
  const title = extractTitle();
  onVideoDetected(videoId, title);
}

function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

// ── 初始化 ─────────────────────────────────────────────
function init() {
  buildUI();
  setCatState("idle");
  checkPage();

  // 监听 SPA 路由变化（抖音是 SPA）
  let lastUrl = location.href;
  const observer = new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(checkPage, 1500); // 等待页面渲染
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // 定期检查（保险）
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

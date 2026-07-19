/**
 * 妙喵私教 — 桌宠陪伴模块
 * 语录结构参考 VPet 虚拟桌宠模拟器 MOD 格式（SelectText/ClickText/LowText），
 * 好感度门槛 LikeMin 简化为 0 / 50 / 200 三档。
 * 暴露全局 MiaoPet，由内容脚本初始化。
 */
(function () {
  // ── 语录库 ─────────────────────────────────────────────
  const PHRASES = {
    // 时段问候
    greet: {
      morning: ["早上好喵！一日之计在于晨，刷一题提提神～", "早安喵！今天的学习目标定好了吗？"],
      afternoon: ["下午好喵～犯困的话起来喝口水再看！", "午后时光最适合学点硬知识喵"],
      evening: ["晚上好喵～学完这一段就可以安心休息啦", "晚自习时间到，妙喵陪你一起喵"],
      night: ["这么晚还在学？注意休息呀…但既然看了就看完这个知识点吧！", "深夜学习喵…我陪你，但别太晚哦"],
    },
    // 闲置唠叨（LowText 风格，学习向）
    idle: [
      "盯——看了这么久，要不要让我出一道题考考你？",
      "今天也要好好学习喵～",
      "起来动动啦！坐太久尾巴都要麻了~",
      "提醒喝水小助手：和我一起成为一天八杯水的人吧！",
      "学习是一种态度，而不是能力喵",
      "知识就是力量，但先理解这段视频才行呀！",
      "你学你的，我趴着陪你，不打扰～",
      "一直在刷视频？不如让我给你划划重点喵",
      "喵帕斯～有好好吃饭吗？有好好学习吗？",
      "今日运势：宜刷题，忌摸鱼 😼",
      "学完这段，奖励你摸我一下～",
      "这条路很远，但眼前的这个知识点很近！",
      "今天不学，明天变弱；今天学了，明天变强！",
      "不会的地方直接问我喵，别客气",
    ],
    // 摸头回应（ClickText 风格，按好感度分档）
    pat: {
      low: ["喵？", "干嘛啦，专心看视频喵", "好痒啊，别挠我啦！", "摸鱼不如摸我…啊不对，快去学习！"],
      mid: ["主人人～", "摸我可以，但题也要做哦", "喵呜～舒服舒服", "再摸一下…就一下哦，然后继续看"],
      high: ["主人大人～人家最喜欢～", "蹭蹭～学完这章给你表演后空翻（虚拟的）", "主人主人主人主人主人～", "偷看主人学习资料…咦，好认真！"],
    },
    // 选择对话（SelectText 风格：q=菜单项，replies 按 likeMin 取最高满足档，form=说话时猫形态）
    menu: [
      { q: "是不是偷偷摸鱼了？", form: "watching", replies: [
        { likeMin: 0, text: "没有喵没有喵" },
        { likeMin: 50, text: "我是正经私教，怎么可能摸鱼喵~" },
        { likeMin: 200, text: "摸鱼，最爽了喵（摊）…但你不许学我！" },
      ]},
      { q: "你有藏小鱼干吗？", form: "reward", replies: [
        { likeMin: 0, text: "啊这，妙喵不知道哟" },
        { likeMin: 50, text: "略略略，不告诉主人！" },
        { likeMin: 200, text: "其实…想留着等你全通关一起庆祝喵。" },
      ]},
      { q: "我学不动了…", form: "failed", replies: [
        { likeMin: 0, text: "累了就站起来喝口水，我等你回来喵" },
        { likeMin: 50, text: "坚持住！这一段看完我陪你一起休息" },
        { likeMin: 200, text: "主人已经很厉害了，歇5分钟，妙喵给你加油！" },
      ]},
      { q: "夸夸我！", form: "celebrating", replies: [
        { likeMin: 0, text: "主人今天也很努力喵！" },
        { likeMin: 50, text: "认真看视频的主人最帅了喵~" },
        { likeMin: 200, text: "主人是我的骄傲喵！全通关一定行！" },
      ]},
    ],
    urge: "收到！妙喵盯梢模式开启——这段时间不准摸鱼，看完我来出题！",
    quiet: "好喵…那我安静一会儿，想我了就摸摸我",
  };

  const LIKE_KEY = "mm_pet_like";
  const QUIET_KEY = "mm_pet_quiet_until";
  const PAT_COOLDOWN_MS = 3000;
  // 这些形态属于原学习流程（答题分析中/判卷结果），桌宠说话时不抢
  const FORM_PROTECTED = ["analyzing", "celebrating", "failed"];

  let like = 0;
  let quietUntil = 0;
  let lastPatAt = 0;
  let sayTimer = null;
  let menuHideTimer = null;
  let myForm = null;
  let hooks = {};
  let rootEl = null;

  function loadState() {
    try {
      chrome.storage.local.get([LIKE_KEY, QUIET_KEY], (d) => {
        like = (d && d[LIKE_KEY]) || 0;
        quietUntil = (d && d[QUIET_KEY]) || 0;
      });
    } catch {}
  }
  function saveLike() {
    try { chrome.storage.local.set({ [LIKE_KEY]: like }); } catch {}
  }

  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

  function greetCategory() {
    const h = new Date().getHours();
    if (h < 6) return "night";
    if (h < 12) return "morning";
    if (h < 14) return "afternoon";
    if (h < 18) return "afternoon";
    if (h < 22) return "evening";
    return "night";
  }

  // ── UI ─────────────────────────────────────────────────
  function ensureUI() {
    if (document.getElementById("mm-say")) return;
    const sayEl = document.createElement("div");
    sayEl.id = "mm-say";
    const menu = document.createElement("div");
    menu.id = "mm-pet-menu";
    menu.innerHTML = `
      <button data-act="pat">摸摸头</button>
      <button data-act="urge">督促我学习</button>
      ${PHRASES.menu.map((m, i) => `<button data-act="menu" data-i="${i}">${m.q}</button>`).join("")}
      <button data-act="quiet">安静一会儿</button>
    `;
    rootEl.appendChild(sayEl);
    rootEl.appendChild(menu);

    menu.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      const act = btn.dataset.act;
      if (act === "pat") doPat();
      else if (act === "urge") { like += 1; saveLike(); say(PHRASES.urge, 6000, "watching"); }
      else if (act === "menu") {
        like += 1; saveLike();
        const item = PHRASES.menu[Number(btn.dataset.i)];
        const eligible = item.replies.filter((r) => like >= r.likeMin);
        say(eligible[eligible.length - 1].text, 5000, item.form);
      }
      else if (act === "quiet") {
        quietUntil = Date.now() + 10 * 60 * 1000;
        try { chrome.storage.local.set({ [QUIET_KEY]: quietUntil }); } catch {}
        say(PHRASES.quiet, 3000, "idle");
      }
      hideMenu(400);
    });
    menu.addEventListener("mouseenter", () => clearTimeout(menuHideTimer));
    menu.addEventListener("mouseleave", () => hideMenu(300));
  }

  function say(text, ms = 4500, form = null) {
    const el = document.getElementById("mm-say");
    if (!el) return;
    clearTimeout(sayTimer);
    el.textContent = text;
    el.classList.add("mm-show");
    // 说话即变形；原流程形态（答题分析中/判卷）优先，桌宠不抢
    const cur = hooks.getCatState ? hooks.getCatState() : null;
    if (form && hooks.setCatState && !FORM_PROTECTED.includes(cur)) {
      myForm = form;
      hooks.setCatState(form);
    } else {
      myForm = null;
    }
    sayTimer = setTimeout(() => {
      el.classList.remove("mm-show");
      // 形态仍是我设的才回退，被原流程接管则不动
      if (myForm && hooks.getCatState && hooks.getCatState() === myForm) {
        hooks.setCatState("idle");
      }
      myForm = null;
    }, ms);
  }

  function showMenu() {
    const menu = document.getElementById("mm-pet-menu");
    if (!menu) return;
    clearTimeout(menuHideTimer);
    menu.classList.add("mm-show");
    rootEl.classList.add("mm-menu-open");
  }
  function hideMenu(ms = 0) {
    clearTimeout(menuHideTimer);
    const menu = document.getElementById("mm-pet-menu");
    if (!menu) return;
    const close = () => {
      menu.classList.remove("mm-show");
      rootEl.classList.remove("mm-menu-open");
    };
    if (ms <= 0) { close(); return; }
    menuHideTimer = setTimeout(close, ms);
  }

  function doPat() {
    const now = Date.now();
    if (now - lastPatAt < PAT_COOLDOWN_MS) return;
    lastPatAt = now;
    like += 1;
    saveLike();
    const tier = like >= 200 ? "high" : like >= 50 ? "mid" : "low";
    say(pick(PHRASES.pat[tier]), 3500, "celebrating");
    try { MiaoSound.play("meow"); } catch {}
  }

  // ── 对外接口 ───────────────────────────────────────────
  window.MiaoPet = {
    /** 由内容脚本在 buildUI 后调用；hooks: { setCatState } */
    init(root, h) {
      rootEl = root;
      hooks = h || {};
      loadState();
      ensureUI();
      const bubble = root.querySelector("#mm-bubble");
      // 悬停：说话 + 出菜单（“看这个猫的时候”）
      bubble.addEventListener("mouseenter", () => {
        if (Date.now() < quietUntil) { showMenu(); return; }
        const form = pick(["idle", "idle", "watching", "watching"]);
        say(pick(PHRASES.pat.low.concat(PHRASES.idle.slice(0, 4))), 3500, form);
        showMenu();
      });
      bubble.addEventListener("mouseleave", () => hideMenu(600));
      // 右键也出菜单（VPet 习惯）
      bubble.addEventListener("contextmenu", (e) => { e.preventDefault(); showMenu(); });
      // 闲置唠叨：每 50s 一次抽签，面板关着且未静音唠叨时才说
      setInterval(() => {
        if (Date.now() < quietUntil) return;
        const panel = document.getElementById("mm-panel");
        if (panel && panel.classList.contains("mm-open")) return;
        if (Math.random() < 0.55) say(pick(PHRASES.idle), 5000, pick(["idle", "idle", "watching", "watching"]));
      }, 50000);
    },
    /** 视频识别成功等时机调用：时段问候 */
    greet() {
      if (Date.now() < quietUntil) return;
      say(pick(PHRASES.greet[greetCategory()]), 5000, "watching");
    },
    say,
  };
})();

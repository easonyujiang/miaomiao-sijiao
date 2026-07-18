/**
 * 妙喵私教 — Service Worker
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("妙喵私教已安装");
});

// 代理 fetch 请求，绕过 HTTPS 页面对 HTTP localhost 的 CSP/mixed-content 限制
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "FETCH") {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), msg.timeout || 10000);
    fetch(msg.url, { ...msg.options, signal: controller.signal })
      .then(async (res) => {
        clearTimeout(timer);
        const text = await res.text();
        sendResponse({ ok: res.ok, status: res.status, text });
      })
      .catch((e) => {
        clearTimeout(timer);
        sendResponse({ error: e.message || String(e) });
      });
    return true; // keep sendResponse channel open for async
  }

  if (msg.type === "PING") {
    sendResponse({ status: "ok" });
  }
});

/**
 * 妙喵私教 — Service Worker
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("妙喵私教已安装");
});

// 监听来自 content script 的消息（保留扩展口）
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "PING") {
    sendResponse({ status: "ok" });
  }
});

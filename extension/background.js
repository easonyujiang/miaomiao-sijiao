/**
 * 妙喵私教 — Service Worker
 *
 * 负责：
 * - 监听扩展安装/更新事件
 * - 与 content_script 的消息传递
 * - 管理跨页面的视频学习状态（通过 chrome.storage）
 */

"use strict";

// ── 安装 / 更新 ────────────────────────────────────────────

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("[妙喵] 扩展已安装");
    // 设置默认配置
    chrome.storage.local.set({
      apiBaseUrl: "http://localhost:8000",
      version: chrome.runtime.getManifest().version,
    });
  } else if (details.reason === "update") {
    console.log(`[妙喵] 扩展已更新至 ${chrome.runtime.getManifest().version}`);
  }
});

// ── 消息处理 ───────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_API_BASE") {
    chrome.storage.local.get("apiBaseUrl", (data) => {
      sendResponse({ apiBaseUrl: data.apiBaseUrl || "http://localhost:8000" });
    });
    return true; // 异步响应
  }

  if (message.type === "SET_API_BASE") {
    chrome.storage.local.set({ apiBaseUrl: message.value }, () => {
      sendResponse({ success: true });
    });
    return true;
  }

  if (message.type === "SAVE_LESSON_PROGRESS") {
    // 跨页面持久化学习进度
    const key = `progress_${message.videoId}`;
    chrome.storage.local.set({ [key]: message.progress }, () => {
      sendResponse({ success: true });
    });
    return true;
  }

  if (message.type === "GET_LESSON_PROGRESS") {
    const key = `progress_${message.videoId}`;
    chrome.storage.local.get(key, (data) => {
      sendResponse({ progress: data[key] || null });
    });
    return true;
  }

  if (message.type === "LOG") {
    console.log(`[妙喵] ${message.level || "info"}:`, message.data);
    return false;
  }
});

// ── 网络请求代理（用于绕过某些 CORS 限制，可选） ─────────

// 当前主要通过 content_script 直接 fetch localhost，
// 因为 manifest 中已声明 host_permissions 含 localhost:8000。

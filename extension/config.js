/**
 * 妙喵私教 — 全局配置
 * 作为第一个 content script 注入，提供服务器地址配置
 */

var MiaoConfig = {
  DEFAULT_API_BASE: "http://8.130.190.169:8000",
  DEFAULT_SITE_URL: "http://8.130.190.169:8000",

  getApiBase(cb) {
    try {
      chrome.storage.sync.get(["api_base"], (res) => {
        cb((res && res.api_base) || MiaoConfig.DEFAULT_API_BASE);
      });
    } catch {
      cb(MiaoConfig.DEFAULT_API_BASE);
    }
  },

  getSiteUrl(cb) {
    try {
      chrome.storage.sync.get(["site_url", "api_base"], (res) => {
        cb((res && (res.site_url || res.api_base)) || MiaoConfig.DEFAULT_SITE_URL);
      });
    } catch {
      cb(MiaoConfig.DEFAULT_SITE_URL);
    }
  },
};

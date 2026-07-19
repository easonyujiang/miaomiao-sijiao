const SITE_URL = "https://miaomiao-cat.duckdns.org";
const FALLBACK_VIDEO_URL = "https://www.bilibili.com/video/BV1mJ4m147PG";

function closePopup() {
  window.close();
}

document.getElementById("mm-popup-summon").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  chrome.tabs.sendMessage(tab.id, { action: "summon" }).catch(() => {
    // 如果页面还没注入内容脚本，则打开示例视频
    chrome.tabs.create({ url: FALLBACK_VIDEO_URL });
  });
  closePopup();
});

document.getElementById("mm-popup-site").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab?.url || "";
  // 如果当前在B站/抖音视频页，尝试带上视频ID跳转到网站对应页面
  const bvid = url.match(/bilibili\.com\/video\/(BV\w+)/i)?.[1];
  const dyId = url.match(/douyin\.com\/video\/(\d+)/i)?.[1];
  let target = SITE_URL;
  if (bvid) {
    target = `${SITE_URL}/community?video_id=${bvid}`;
  } else if (dyId) {
    target = `${SITE_URL}/community?video_id=DY_${dyId}`;
  }
  chrome.tabs.create({ url: target });
  closePopup();
});

document.getElementById("mm-popup-cat").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  chrome.tabs.sendMessage(tab.id, { action: "summon" }).catch(() => {
    chrome.tabs.create({ url: FALLBACK_VIDEO_URL });
  });
  closePopup();
});

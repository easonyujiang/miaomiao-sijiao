document.getElementById("mm-popup-cat").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  // 向当前标签页发送召唤消息，内容脚本收到后会弹出桌宠气泡
  chrome.tabs.sendMessage(tab.id, { action: "summon" }).catch(() => {
    // 如果页面还没注入内容脚本，则打开B站示例视频
    chrome.tabs.create({ url: "https://search.bilibili.com/all?keyword=%E7%BD%97%E7%BF%94%20%E6%AD%A3%E5%BD%93%E9%98%B2%E5%8D%AB" });
  });
  window.close();
});

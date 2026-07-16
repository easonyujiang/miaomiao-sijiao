/**
 * 妙喵音效 —— howler 封装（插件端全局单例）
 * 静音偏好用 chrome.storage.local 持久化（与网站端 localStorage 各自独立）
 * 资产：extension/sounds/*.mp3（见《前端与音效购置方案》§1.2）
 */
const MiaoSound = (() => {
  const VOLUME = { pass: .7, perfect: .7, levelup: .7, fail: .4,
                   seek: .5, meow: .6, badge: .5, thinking: .15 };
  const howls = {};
  const files = { pass:'pass', perfect:'perfect', fail:'fail', seek:'seek',
                  meow:'meow', badge:'badge', levelup:'level-up', thinking:'thinking' };
  let muted = false, thinkingHowl = null;

  for (const [k, f] of Object.entries(files)) {
    howls[k] = new Howl({ src: [chrome.runtime.getURL(`sounds/${f}.mp3`)],
                          volume: VOLUME[k], loop: k === 'thinking' });
  }
  chrome.storage.local.get('miaomiao_muted').then(d => muted = !!d.miaomiao_muted);

  return {
    play(k)      { if (!muted) howls[k]?.play(); },
    startThink() { if (!muted && thinkingHowl == null) thinkingHowl = howls.thinking.play(); },
    stopThink()  { if (thinkingHowl != null) { howls.thinking.stop(thinkingHowl); thinkingHowl = null; } },
    toggleMute() { muted = !muted; chrome.storage.local.set({ miaomiao_muted: muted }); if (muted) this.stopThink(); return muted; },
    isMuted()    { return muted; },
  };
})();

# 妙喵私教 Chrome Extension

把教学视频变成一对一私教 — 注入 B站/抖音视频页，提供 AI 出题 + 判卷纠错。

## 加载方式

1. 打开 Chrome，访问 `chrome://extensions/`
2. 开启右上角 **「开发者模式」**
3. 点击 **「加载已解压的扩展程序」**
4. 选择 `extension/` 目录

## 使用流程

1. **启动后端**：`python run.py`（确保后端在 `localhost:8000`）
2. **打开视频**：访问 B站视频页（如 `BV1mJ4m147PG`）
3. **🐱 气泡出现**：播放器右下角自动显示妙喵气泡
4. **开始学习**：点击气泡 → 展开面板 → 点击「开始学习」
5. **5 关练习**：看片段 → 答题 → 判卷 → 纠错跳转 → 下一关

## 文件结构

```
extension/
├── manifest.json        # MV3 配置
├── content_script.js    # 注入视频页，显示气泡 + 答题面板
├── content_style.css    # 气泡 + 面板样式
├── background.js        # Service Worker（状态持久化）
├── assets/              # 图标
│   ├── cat-16.png
│   ├── cat-48.png
│   └── cat-128.png
└── README.md
```

## 支持的平台

- [x] B站 (bilibili.com/video/*)
- [ ] 抖音 (douyin.com/video/*) — 待适配

## 猫咪状态机

| 状态 | 图标 | 触发 |
|------|------|------|
| idle | 🐱 | 等待/初始 |
| watching | 🐱💭 | 引导观看片段 |
| listening | 🐱👂 | 等待作答 |
| analyzing | 🐱🔍 | 正在判卷 |
| correcting | 🐱📝 | 答错纠错中 |
| celebrating | 🐱🎉 | 通过/完成 |

## 调试

按 F12 打开 DevTools → Console，过滤 `[妙喵]` 查看日志。

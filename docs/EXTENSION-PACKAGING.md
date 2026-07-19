# Chrome 插件打包指导

本文档指导如何打包妙喵私教 Chrome 插件，用于发布到 Chrome Web Store 或手动安装。

当前插件支持：B站/抖音视频页注入、视频问答、课程闯关、语音输入。

## 目录

- [开发模式加载](#开发模式加载)
- [打包发布版](#打包发布版)
- [Chrome Web Store 发布](#chrome-web-store-发布)
- [修改后端地址](#修改后端地址)
- [插件文件结构](#插件文件结构)
- [常见问题](#常见问题)

---

## 开发模式加载

最简单的测试方式，无需打包：

1. 打开 Chrome，地址栏输入 `chrome://extensions/`
2. 右上角打开 **开发者模式**
3. 点击 **加载已解压的扩展程序**
4. 选择项目根目录下的 `extension/` 文件夹
5. 插件图标出现在浏览器工具栏

修改代码后，回到 `chrome://extensions/` 点击刷新按钮即可。

## 打包发布版

### 方式一：命令行打包

```bash
# Windows PowerShell:
Compress-Archive -Path "extension\*" -DestinationPath "miaomiao-extension.zip"

# Linux/macOS:
cd extension
zip -r ../miaomiao-extension.zip .
cd ..
```

### 方式二：Chrome 开发者打包

1. 在 `chrome://extensions/` 点击 **打包扩展程序**
2. 扩展程序根目录选择 `extension/`
3. 留空私钥（首次打包），点击确定
4. 生成 `extension.crx` 和 `extension.pem`

### 方式三：ZIP 直接上传 Chrome Web Store

Chrome Web Store 接受 `.zip` 格式，推荐使用方式一。

## Chrome Web Store 发布

### 前置条件

1. 注册 [Chrome Web Store 开发者账号](https://chrome.google.com/webstore/devconsole)（一次性注册费 $5）
2. 准备以下材料：
   - 插件 ZIP 包（不包含 `.crx` 或 `.pem`）
   - 128x128 图标（已有 `extension/assets/cat128.png`）
   - 至少一张截图（1280x800 或 640x400）
   - 描述文字（简短描述 + 详细描述）

### 发布步骤

1. 登录 [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. 点击 **New Item**
3. 上传 `miaomiao-extension.zip`
4. 填写商品信息：
   - **名称**: 妙喵私教
   - **简短描述**: 把教学视频变成一对一私教
   - **详细描述**: 在 B站/抖音视频页注入妙喵助手，支持视频问答、课程闯关、语音答题
   - **类别**: 教育
   - **语言**: 中文
5. 上传截图和图标
6. 设置隐私实践（本插件不收集用户数据）
7. 提交审核（通常 1-3 个工作日）

### 审核要点

Chrome Web Store 审核关注点：

- **最小权限原则**: 本插件仅申请 `storage` 和 `tabs` 权限，符合要求
- **主机权限**: 声明了 `douyin.com`、`bilibili.com`、远程服务器地址
- **数据使用**: 不收集、不传输用户数据到第三方；语音音频仅发送至自托管后端进行识别
- **内容安全**: 不涉及恶意代码或误导行为
- **麦克风权限**: 插件不直接申请 `audioCapture` 权限，通过页面 `getUserMedia` 在 B站/抖音页面内请求麦克风

## 修改后端地址

默认连接 `http://8.130.190.169:8000`（远程服务器）。如需改回本地或指向其他服务器：

### 修改步骤

1. 编辑 `extension/content/bilibili.js` 第 7 行：

```javascript
const API_BASE = "http://8.130.190.169:8000";
// 改为本地：
const API_BASE = "http://localhost:8000";
// 或改为其他服务器：
const API_BASE = "https://your-server.com";
```

2. 编辑 `extension/content/douyin.js` 第 6 行，同样修改。

3. 编辑 `extension/content/voice.js` 第 86 行，修改默认 `baseUrl`：

```javascript
upload(blob, baseUrl = "http://8.130.190.169:8000") {
```

4. 在 `manifest.json` 的 `host_permissions` 中添加对应域名：

```json
"host_permissions": [
    "https://www.douyin.com/*",
    "https://www.bilibili.com/*",
    "http://8.130.190.169:8000/*",
    "https://8.130.190.169/*",
    "https://miaomiao-cat.duckdns.org/*",
    "http://localhost:8000/*"
]
```

5. 重新打包 ZIP 并上传。

### 更优雅的方案（通过 popup 设置）

可以在 popup 中添加服务器地址设置，保存到 `chrome.storage.local`，content script 读取后使用。这属于功能增强，当前版本暂未实现。

## 插件文件结构

```
extension/
├── manifest.json          # 插件清单（MV3）
├── background.js          # Service Worker（代理 fetch 请求，含语音上传）
├── pet.js                 # 桌宠交互逻辑
├── sound.js               # 音效管理（howler.js 封装）
├── content/
│   ├── bilibili.js        # B站内容脚本（视频问答 + 课程闯关 + 语音）
│   ├── douyin.js          # 抖音内容脚本（视频问答 + 语音）
│   ├── voice.js           # 通用语音录制/上传工具
│   └── style.css          # 注入样式
├── lib/
│   ├── lottie_light.min.js  # Lottie 动画引擎（轻量版）
│   ├── howler.min.js        # 音频播放库
│   └── confetti.browser.js  # 撒花特效
├── lottie/                 # Lottie 动画 JSON 文件
│   ├── cat-lovely.json     # idle 状态
│   ├── cat-playing.json    # watching 状态
│   ├── cat-loading.json    # analyzing 状态
│   ├── cat-dance.json      # celebrating 状态
│   ├── cat-sad.json        # failed 状态
│   └── cat-eating-fish.json # reward 状态
├── sounds/                 # 音效文件（MP3）
├── popup/
│   ├── popup.html          # 弹出窗口
│   └── popup.js            # 弹出窗口逻辑
└── assets/
    ├── cat16.png           # 工具栏图标
    ├── cat48.png           # 扩展管理页图标
    └── cat128.png          # 商店图标
```

## 常见问题

### 插件加载后没有反应

1. 检查 `chrome://extensions/` 页面是否有错误提示
2. 确认后端服务是否运行在 `localhost:8000`
3. 打开开发者工具查看 Console 日志

### 后端连接不上

插件通过 `background.js` service worker 代理所有 HTTP 请求，绕过 HTTPS 页面对 HTTP 后端的混合内容限制。如果仍连接不上：

1. 确认后端运行：访问 `http://8.130.190.169:8000/health`（或你配置的地址）
2. 检查 `manifest.json` 中 `host_permissions` 是否包含后端域名
3. 检查 `extension/content/bilibili.js` / `douyin.js` / `voice.js` 中的 `API_BASE` 是否指向正确地址
4. 重新加载插件

### 语音输入无反应

1. 确认后端 `BAIDU_API_KEY` / `BAIDU_SECRET_KEY` 已配置且有效
2. 在 B站/抖音页面地址栏左侧允许麦克风权限
3. 检查 Console 是否有 `MediaRecorder` 不支持当前浏览器的报错
4. 确认后端 `/api/speech-to-text` 可访问

### 只想测试 B站 或 抖音其中一个

插件支持两个平台，可以同时工作。如果只想测试一个，可以在 `manifest.json` 中注释掉不需要的 content_scripts 条目：

```json
"content_scripts": [
    {
        "matches": ["https://www.bilibili.com/video/*"],
        "js": ["lib/howler.min.js", "lib/lottie_light.min.js", "lib/confetti.browser.js", "sound.js", "pet.js", "content/bilibili.js"],
        "css": ["content/style.css"],
        "run_at": "document_idle"
    }
    // 抖音的条目可以暂时注释掉
]
```

### 猫为什么是静态图而不是动画？

插件使用 `lottie_light.min.js` 加载 Lottie 动画。动画加载成功时显示动态猫；加载失败或浏览器不支持时，自动降级为 `assets/cat128.png` 静态猫图，保证用户始终能看到猫。

### 打包后体积过大

插件总大小主要来自：
- `lib/` 下的第三方库（lottie_light、howler、confetti）约 250KB
- `lottie/` 动画 JSON 文件约 100KB
- `sounds/` 音效 MP3 约 50KB
- `assets/` 图标和兜底猫图约 40KB

总大小通常在 450KB 以内，Chrome Web Store 无明显限制。

### 更新后用户如何升级

Chrome Web Store 发布新版本后，浏览器会自动更新（通常几小时内）。手动安装的插件需要用户重新加载。

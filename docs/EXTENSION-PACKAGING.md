# Chrome 插件打包指导

本文档指导如何打包妙喵私教 Chrome 插件，用于发布到 Chrome Web Store 或手动安装。

当前插件支持：B站/抖音视频页注入、视频问答、课程闯关、语音输入。**当前未上架**，日常测试直接用开发者模式加载 `extension/` 目录即可。

## 目录

- [开发模式加载](#开发模式加载)
- [插件配置](#插件配置)
- [修改后端地址](#修改后端地址)
- [打包发布版](#打包发布版)
- [Chrome Web Store 发布](#chrome-web-store-发布)
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

## 插件配置

### manifest（MV3）

`extension/manifest.json` 的关键声明：

- **permissions**：仅 `storage`、`tabs`，符合最小权限原则
- **host_permissions**：

```json
[
  "https://www.douyin.com/*",
  "https://www.bilibili.com/*",
  "http://8.130.190.169:8000/*"
]
```

- **background**：`background.js` service worker，代理所有 HTTP 请求（含语音上传）
- **content_scripts** 注入链（顺序即依赖顺序，`config.js` 必须最先）：

```
config.js                    # 服务器地址配置（MiaoConfig）
lib/howler.min.js            # 音频播放
lib/lottie_light.min.js      # Lottie 动画
lib/confetti.browser.js      # 撒花特效
sound.js                     # 音效管理（howler 封装）
pet.js                       # 桌宠交互
content/voice.js             # 语音录制/上传
content/bilibili.js          # 平台脚本（B站条目）
content/douyin.js            # 平台脚本（抖音条目）
```

注入时机 `document_idle`，样式统一走 `content/style.css`。

### 语音方案

- 录音在 B站/抖音页面内进行：这两个站点本身是 HTTPS，`getUserMedia` 在页面上下文中可用，插件**不需要 `audioCapture` 权限**
- 录好的音频经 `background.js` service worker 代理上传到 `/api/speech-to-text`（后端调用百度短语音识别），绕过 HTTPS 页面对 HTTP 后端的混合内容限制
- 需在服务器 `.env` 配置 `BAIDU_API_KEY` / `BAIDU_SECRET_KEY`

## 修改后端地址

**服务器地址已可在 popup 中配置，无需改代码。**

1. 点击工具栏插件图标打开 popup
2. 底部"服务器地址"输入框填入新地址（如 `http://localhost:8000`）
3. 点击"保存"，地址写入 `chrome.storage.sync`
4. **刷新视频页面**后生效

默认值在 `extension/config.js` 中：`http://8.130.190.169:8000`。popup 未保存过自定义值时使用默认值。

改为指向新服务器时注意：

- 新地址需要加入 `manifest.json` 的 `host_permissions`（否则 background.js 代理请求会被浏览器拦截）
- 页面内 `getUserMedia` 录音在 HTTPS 页面中始终可用，与后端地址无关；但 HTTPS 后端或 localhost 之外的自定义后端必须是 `host_permissions` 允许的地址

## 打包发布版

### 方式一：命令行打包（推荐）

```powershell
# Windows PowerShell（仓库根目录）:
Compress-Archive -Path "extension\*" -DestinationPath "miaomiao-extension.zip"
```

```bash
# Linux/macOS:
cd extension
zip -r ../miaomiao-extension.zip .
cd ..
```

### 方式二：Chrome 开发者打包

1. 在 `chrome://extensions/` 点击 **打包扩展程序**
2. 扩展程序根目录选择 `extension/`
3. 留空私钥（首次打包），点击确定
4. 生成 `extension.crx` 和 `extension.pem`（`.pem` 需妥善保管，后续更新版本必须复用同一私钥）

### 方式三：ZIP 直接上传 Chrome Web Store

Chrome Web Store 接受 `.zip` 格式，直接使用方式一的产物。

## Chrome Web Store 发布

> 当前插件**尚未上架**。以下为发布流程备查。

### 前置条件

1. 注册 [Chrome Web Store 开发者账号](https://chrome.google.com/webstore/devconsole)（一次性注册费 $5）
2. 准备材料：
   - 插件 ZIP 包（不包含 `.crx` 或 `.pem`）
   - 128x128 图标（已有 `extension/assets/cat128.png`）
   - 至少一张截图（1280x800 或 640x400）
   - 描述文字（简短描述 + 详细描述）

### 发布步骤

1. 登录 [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. 点击 **New Item**
3. 上传 `miaomiao-extension.zip`
4. 填写商品信息：
   - **名称**：妙喵私教
   - **简短描述**：把教学视频变成一对一私教
   - **详细描述**：在 B站/抖音视频页注入妙喵助手，支持视频问答、课程闯关、语音答题
   - **类别**：教育
   - **语言**：中文
5. 上传截图和图标
6. 设置隐私实践（本插件不收集用户数据）
7. 提交审核（通常 1-3 个工作日）

### 审核要点

- **最小权限原则**：仅申请 `storage` 和 `tabs`，符合要求
- **主机权限**：仅声明 `douyin.com`、`bilibili.com` 与自托管后端 `http://8.130.190.169:8000/*`
- **数据使用**：不收集、不传输用户数据到第三方；语音音频仅发送至自托管后端进行识别
- **内容安全**：不涉及恶意代码或误导行为
- **麦克风权限**：不申请 `audioCapture`，通过页面 `getUserMedia` 在 B站/抖音页面内请求麦克风

## 插件文件结构

```
extension/
├── manifest.json            # 插件清单（MV3）
├── config.js                # 全局配置：服务器地址（MiaoConfig，读 chrome.storage.sync）
├── background.js            # Service Worker（代理 fetch 请求，含语音上传）
├── pet.js                   # 桌宠交互逻辑
├── sound.js                 # 音效管理（howler.js 封装）
├── content/
│   ├── bilibili.js          # B站内容脚本（视频问答 + 课程闯关 + 语音）
│   ├── douyin.js            # 抖音内容脚本（视频问答 + 语音）
│   ├── voice.js             # 通用语音录制/上传工具
│   └── style.css            # 注入样式
├── lib/
│   ├── lottie_light.min.js  # Lottie 动画引擎（轻量版）
│   ├── howler.min.js        # 音频播放库
│   └── confetti.browser.js  # 撒花特效
├── lottie/                  # Lottie 动画 JSON 文件
│   ├── cat-lovely.json      # idle 状态
│   ├── cat-playing.json     # watching 状态
│   ├── cat-loading.json     # analyzing 状态
│   ├── cat-dance.json       # celebrating 状态
│   ├── cat-sad.json         # failed 状态
│   └── cat-eating-fish.json # reward 状态
├── sounds/                  # 音效文件（MP3）
├── popup/
│   ├── popup.html           # 弹出窗口（含"服务器地址"配置区）
│   └── popup.js             # 弹出窗口逻辑（保存地址到 chrome.storage.sync）
└── assets/
    ├── cat16.png            # 工具栏图标
    ├── cat48.png            # 扩展管理页图标
    └── cat128.png           # 商店图标
```

## 常见问题

### 插件加载后没有反应

1. 检查 `chrome://extensions/` 页面是否有错误提示
2. 确认后端服务可达：浏览器直接访问 `http://8.130.190.169:8000/health`（或你配置的地址）
3. 打开视频页开发者工具查看 Console 日志

### 后端连接不上

插件通过 `background.js` service worker 代理所有 HTTP 请求，绕过 HTTPS 页面对 HTTP 后端的混合内容限制。如果仍连接不上：

1. 确认后端运行：访问 `http://8.130.190.169:8000/health`
2. 检查 popup 里"服务器地址"是否填对（保存后**需刷新视频页**才生效）
3. 检查 `manifest.json` 中 `host_permissions` 是否包含后端地址
4. 回到 `chrome://extensions/` 重新加载插件

### 语音输入无反应

1. 确认后端 `.env` 中 `BAIDU_API_KEY` / `BAIDU_SECRET_KEY` 已配置且有效
2. 在 B站/抖音页面地址栏左侧允许麦克风权限
3. 检查 Console 是否有 `MediaRecorder` 报错
4. 确认后端 `/api/speech-to-text` 可访问

### 只想测试 B站 或 抖音其中一个

插件支持两个平台同时工作。如果只想测试一个，在 `manifest.json` 中删掉不需要的 `content_scripts` 条目即可（注意 JSON 不支持注释，直接删除整块对象）。

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

Chrome Web Store 发布新版本后，浏览器会自动更新（通常几小时内）。开发者模式手动加载的插件需要重新加载解压目录。

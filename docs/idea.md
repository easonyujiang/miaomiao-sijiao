# 插件语音答题功能规划

## 目标
在 Chrome 插件（抖音/B站内容脚本）的输入区加入基础语音输入能力，主要用于**课程/练习模式下的口语答题**。用户按住麦克风说话，松开后自动把语音转成文字并提交答案。

## 使用场景
1. **练习模式出题后**：妙喵暂停视频并提问，用户按住麦克风说出答案，系统自动识别并提交。
2. **自由问答**：用户也可以用语音代替键盘输入问题。

## 总体流程

```
┌─────────────┐   按住说话   ┌─────────────┐   上传音频   ┌─────────────┐
│ 插件输入区  │ ──────────> │ 音频 Blob   │ ──────────> │ 后端 /api/  │
│ 麦克风按钮  │             │ (webm/opus) │             │ speech-to-  │
└─────────────┘   松开发送  └─────────────┘             │ text        │
                                                         └──────┬──────┘
                                                                │
                                                                ▼
                                                         ┌─────────────┐
                                                         │  百度 ASR   │
                                                         │ 返回文字    │
                                                         └──────┬──────┘
                                                                │
                                                                ▼
┌─────────────┐   提交答案   ┌─────────────┐   返回结果   ┌─────────────┐
│  课程答题   │ <────────── │  文字答案   │ <────────── │ 后端判题    │
│  或自由问答  │             │             │             │ 接口        │
└─────────────┘             └─────────────┘             └─────────────┘
```

## 需要改动的文件

### 1. `extension/background.js`
新增 `UPLOAD_AUDIO` 消息类型：
- 接收 base64 音频数据 + 文件名
- 构造 `FormData` 并 POST 到 `http://localhost:8000/api/speech-to-text`
- 返回识别文本或错误信息

原因：内容脚本在 HTTPS 页面内无法直接访问 `http://localhost:8000`，需要通过 background service worker 代理；`FormData` 本身不能通过 `chrome.runtime.sendMessage` 直接传递，所以传 base64 在 background 里重建。

### 2. `extension/content/style.css`
新增样式：
- 麦克风按钮（输入框右侧）
- 录音中按钮高亮/变红
- 录音提示（可选）：输入框上方显示「正在听…」
- 语音输入不可用时的禁用态

### 3. `extension/content/douyin.js`
- 在 `buildUI` 的 `#mm-input-area` 中加入麦克风按钮
- 新增语音录制函数：`startRecording`、`stopRecording`
- 新增 `sendVoiceAnswer` 函数：
  - 调用 background 上传音频
  - 若当前处于 `pendingQuizStep`，把识别结果直接走 `submitAndShow`
  - 否则走普通 `sendMessage`
- 绑定事件：按住开始录音，松开结束

### 4. `extension/content/bilibili.js`
- 与 `douyin.js` 做同样的改动（两者 UI 和流程几乎一致，可以抽象公共函数，但本次先保持简单重复）

### 5. 可选：`extension/sound.js`
- 录音开始/结束时播放简短音效，增强反馈（类似网站端语音按钮）

## 后端接口
复用现有接口，无需新增：
- `POST /api/speech-to-text`：音频文件 → 文字
- `POST /api/lesson/quiz_submit`：文字答案 → 判题结果
- `POST /api/ext/chat`：文字问题 → 聊天回复

## 关键实现细节

### 录音实现
```js
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
  ? 'audio/webm;codecs=opus'
  : 'audio/webm';
const recorder = new MediaRecorder(stream, { mimeType });
// 收集 chunks，stop 后合并成 Blob
```

### 上传到 background
```js
const reader = new FileReader();
reader.readAsDataURL(blob);  // base64 data url
reader.onloadend = () => {
  const base64 = reader.result.split(',')[1];
  chrome.runtime.sendMessage({
    type: 'UPLOAD_AUDIO',
    audio: base64,
    filename: 'answer.webm',
  }, (res) => { ... });
};
```

### Background 端重建 FormData
```js
const blob = await fetch(`data:application/octet-stream;base64,${msg.audio}`).then(r => r.blob());
const formData = new FormData();
formData.append('audio', blob, msg.filename);
fetch('http://localhost:8000/api/speech-to-text', { method: 'POST', body: formData });
```

## 交互设计（微信式）
- **麦克风按钮**：放在输入框右侧，默认显示麦克风图标
- **按住说话**：按钮变红，显示录音状态提示
- **松开发送**：停止录音，识别中显示「识别中…」
- **识别结果**：
  - 练习模式下直接作为答案提交，显示「你说：xxx」
  - 自由模式下作为普通消息发送
- **无结果/错误**：提示「没有听清，请再说一遍」

## 错误处理
- 用户拒绝麦克风权限：提示检查浏览器权限
- 识别为空：提示没有识别到内容
- 后端未启动：提示启动本地服务
- 录音超时（如 30 秒）：自动停止

## 后续可扩展
- 多模态/端侧语音识别：后续可接入本地 Whisper 或 Qwen-Audio 减少对后端依赖
- 语音控制：用户说「出下一题」「帮我解释」等可直接触发插件快捷按钮
- 语音评价：判题结果可以用语音朗读给用户（TTS）

## 验收标准
1. 在 B站/抖音视频页打开妙喵插件，进入课程练习模式
2. 暂停出题后，按住麦克风按钮说出答案
3. 松开后自动识别文字并提交
4. 妙喵给出判题结果（正确/错误 + 星星 + 反馈）
5. 自由问答模式下也能用语音提问

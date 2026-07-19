/**
 * 妙喵私教 — 语音输入通用工具（内容脚本）
 *
 * 提供：
 * - startVoiceRecording(cb): 开始录音，成功后回调 Blob
 * - stopVoiceRecording(): 停止录音
 * - uploadVoice(blob, baseUrl): 上传音频到后端 /api/speech-to-text
 */

var MiaoVoice = {
  recorder: null,
  chunks: [],
  mimeType: "",
  stream: null,

  isSupported() {
    return typeof MediaRecorder !== "undefined" && typeof navigator !== "undefined";
  },

  start(onBlobReady) {
    if (!this.isSupported()) {
      onBlobReady(null, "浏览器不支持录音");
      return;
    }

    this.stop();
    this.chunks = [];
    this.mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then((stream) => {
        this.stream = stream;
        this.recorder = new MediaRecorder(stream, { mimeType: this.mimeType });

        this.recorder.ondataavailable = (e) => {
          if (e.data.size > 0) this.chunks.push(e.data);
        };

        this.recorder.onstop = () => {
          this.stream?.getTracks().forEach((t) => t.stop());
          this.stream = null;
          this.recorder = null;

          if (this.chunks.length === 0) {
            onBlobReady(null, "没有录制到声音");
            return;
          }
          const blob = new Blob(this.chunks, { type: this.mimeType });
          onBlobReady(blob, null);
        };

        this.recorder.onerror = () => {
          this.stream?.getTracks().forEach((t) => t.stop());
          this.stream = null;
          onBlobReady(null, "录音出错");
        };

        this.recorder.start();

        // 最长 30 秒自动停止
        setTimeout(() => {
          if (this.recorder && this.recorder.state === "recording") {
            this.recorder.stop();
          }
        }, 30000);
      })
      .catch((err) => {
        const msg = err.name === "NotAllowedError"
          ? "麦克风权限被拒绝"
          : err.message || "无法启动录音";
        onBlobReady(null, msg);
      });
  },

  stop() {
    if (this.recorder && this.recorder.state === "recording") {
      this.recorder.stop();
    }
    this.recorder = null;
  },

  upload(blob, baseUrl = "http://localhost:8000") {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.readAsDataURL(blob);
      reader.onloadend = () => {
        const base64 = reader.result.split(",")[1];
        chrome.runtime.sendMessage({
          type: "UPLOAD_AUDIO",
          audio: base64,
          filename: "recording.webm",
          baseUrl,
        }, (res) => {
          if (!res || res.error) {
            resolve({ ok: false, error: res?.error || "上传失败" });
            return;
          }
          try {
            const data = JSON.parse(res.text);
            resolve({ ok: res.ok, text: data.text });
          } catch {
            resolve({ ok: false, error: "识别结果解析失败" });
          }
        });
      };
    });
  },
};

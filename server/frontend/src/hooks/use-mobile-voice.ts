import { useCallback, useRef, useState } from 'react'

export function useMobileVoice() {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)

  const isSupported = typeof navigator !== 'undefined' &&
    typeof MediaRecorder !== 'undefined' &&
    typeof navigator.mediaDevices?.getUserMedia === 'function'

  const start = useCallback(() => {
    if (!isSupported) {
      setError('当前浏览器不支持录音')
      return
    }
    if (recording || recorderRef.current) {
      return
    }
    setError(null)
    setRecording(true)
    chunksRef.current = []

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4'

    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        streamRef.current = stream
        const recorder = new MediaRecorder(stream, { mimeType })
        recorderRef.current = recorder

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data)
        }

        recorder.onstop = () => {
          streamRef.current?.getTracks().forEach((t) => t.stop())
          streamRef.current = null
          recorderRef.current = null
          setRecording(false)
        }

        recorder.onerror = () => {
          streamRef.current?.getTracks().forEach((t) => t.stop())
          streamRef.current = null
          recorderRef.current = null
          setRecording(false)
          setError('录音出错')
        }

        recorder.start()
        // 最长 30 秒自动停止
        setTimeout(() => {
          if (recorder.state === 'recording') recorder.stop()
        }, 30000)
      })
      .catch((err) => {
        setRecording(false)
        setError(err.name === 'NotAllowedError' ? '麦克风权限被拒绝' : err.message || '无法启动录音')
      })
  }, [isSupported])

  const stop = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current
      if (!recorder || recorder.state !== 'recording') {
        setRecording(false)
        resolve(null)
        return
      }

      recorder.onstop = () => {
        streamRef.current?.getTracks().forEach((t) => t.stop())
        streamRef.current = null
        recorderRef.current = null
        setRecording(false)

        if (chunksRef.current.length === 0) {
          resolve(null)
          return
        }
        const mimeType = recorder.mimeType || 'audio/webm'
        resolve(new Blob(chunksRef.current, { type: mimeType }))
      }

      recorder.stop()
    })
  }, [])

  return { recording, error, isSupported, start, stop }
}

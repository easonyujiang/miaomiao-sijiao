'use client'

import { useCallback, useRef, useState } from 'react'

type VoiceRecorderState = 'idle' | 'recording' | 'processing' | 'error'

interface UseVoiceRecorderReturn {
  state: VoiceRecorderState
  error: string
  start: () => void
  stop: () => void
  isSupported: boolean
}

export function useVoiceRecorder(onTranscript: (text: string) => void): UseVoiceRecorderReturn {
  const [state, setState] = useState<VoiceRecorderState>('idle')
  const [error, setError] = useState('')
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const isSupported = typeof window !== 'undefined' && 'MediaRecorder' in window && 'navigator' in window

  const stop = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    mediaRecorderRef.current = null
  }, [])

  const start = useCallback(async () => {
    if (!isSupported) {
      setState('error')
      setError('浏览器不支持录音')
      return
    }

    stop()
    setError('')
    setState('recording')
    chunksRef.current = []

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4'

      const recorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onstop = async () => {
        // 停止所有音轨，释放麦克风指示灯
        stream.getTracks().forEach((track) => track.stop())

        if (chunksRef.current.length === 0) {
          setState('idle')
          return
        }

        setState('processing')
        const blob = new Blob(chunksRef.current, { type: mimeType })

        try {
          const formData = new FormData()
          const ext = mimeType.includes('webm') ? 'webm' : mimeType.includes('mp4') ? 'm4a' : 'webm'
          formData.append('audio', blob, `recording.${ext}`)

          const res = await fetch('/api/speech-to-text', {
            method: 'POST',
            body: formData,
          })

          if (!res.ok) {
            const data = await res.json().catch(() => ({ detail: '语音识别服务不可用' }))
            throw new Error(data.detail || '语音识别失败')
          }

          const data = await res.json()
          if (data.text) {
            onTranscript(data.text)
          } else {
            throw new Error('没有识别到内容')
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : '语音识别失败'
          setError(msg)
          setState('error')
          return
        } finally {
          setState('idle')
        }
      }

      recorder.onerror = () => {
        setError('录音出错')
        setState('error')
        stream.getTracks().forEach((track) => track.stop())
      }

      recorder.start()

      // 最长录制 30 秒，自动停止
      setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop()
        }
      }, 30000)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '无法启动录音'
      setError(msg)
      setState('error')
    }
  }, [isSupported, stop, onTranscript])

  return { state, error, start, stop, isSupported }
}

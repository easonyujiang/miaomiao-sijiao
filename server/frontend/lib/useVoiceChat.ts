'use client'

import { useCallback, useRef, useState } from 'react'

type VoiceChatState = 'idle' | 'recording' | 'processing' | 'error'

interface UseVoiceChatReturn {
  state: VoiceChatState
  error: string
  start: () => void
  stop: () => void
  isSupported: boolean
}

export function useVoiceChat(
  onAudioReady: (blob: Blob) => Promise<void>,
): UseVoiceChatReturn {
  const [state, setState] = useState<VoiceChatState>('idle')
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

  const start = useCallback(() => {
    if (!isSupported) {
      setState('error')
      setError('浏览器不支持录音')
      return
    }

    stop()
    setError('')
    setState('recording')
    chunksRef.current = []

    void (async () => {
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
          stream.getTracks().forEach((track) => track.stop())

          if (chunksRef.current.length === 0) {
            setState('idle')
            return
          }

          setState('processing')
          const blob = new Blob(chunksRef.current, { type: mimeType })

          try {
            await onAudioReady(blob)
          } catch (err) {
            const msg = err instanceof Error ? err.message : '语音聊天失败'
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
    })()
  }, [isSupported, stop, onAudioReady])

  return { state, error, start, stop, isSupported }
}

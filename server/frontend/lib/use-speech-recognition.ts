'use client'

import { useCallback, useRef, useState } from 'react'

type SpeechRecognitionState = 'idle' | 'listening' | 'error' | 'not-supported'

interface UseSpeechRecognitionReturn {
  state: SpeechRecognitionState
  transcript: string
  error: string
  start: () => void
  stop: () => void
  isSupported: boolean
}

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
  const [state, setState] = useState<SpeechRecognitionState>('idle')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  const isSupported = typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore stop errors
      }
      recognitionRef.current = null
    }
    setState('idle')
  }, [])

  const start = useCallback(() => {
    if (!isSupported) {
      setState('not-supported')
      setError('浏览器不支持语音输入')
      return
    }

    stop()
    setTranscript('')
    setError('')
    setState('listening')

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognitionRef.current = recognition

    recognition.lang = 'zh-CN'
    recognition.interimResults = true
    recognition.continuous = false
    recognition.maxAlternatives = 1

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = ''
      let interimTranscript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript
        } else {
          interimTranscript += result[0].transcript
        }
      }
      if (finalTranscript) {
        setTranscript(finalTranscript)
      } else if (interimTranscript) {
        setTranscript(interimTranscript)
      }
    }

    recognition.onerror = (event: Event & { error?: string; message?: string }) => {
      if (event.error === 'aborted') return
      const msg = event.error === 'not-allowed'
        ? '麦克风权限被拒绝，请检查浏览器权限设置'
        : event.error === 'network'
          ? '语音识别网络错误，请检查网络连接'
          : event.error === 'no-speech'
            ? '没有检测到语音'
            : `语音识别失败: ${event.error || 'unknown'}`
      console.error('Speech recognition error:', event.error, event.message)
      setError(msg)
      setState('error')
      recognitionRef.current = null
    }

    recognition.onend = () => {
      setState('idle')
      recognitionRef.current = null
    }

    try {
      recognition.start()
    } catch (err) {
      console.error('Failed to start speech recognition:', err)
      setError('启动语音识别失败')
      setState('error')
      recognitionRef.current = null
    }
  }, [isSupported, stop])

  return { state, transcript, error, start, stop, isSupported }
}

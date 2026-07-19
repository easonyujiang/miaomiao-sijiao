'use client'

/**
 * 妙喵语音输入 hook —— react-speech-recognition 薄封装
 *
 * 用法：
 *   const { listening, transcript, supported, start, stop, reset } = usePetAsr()
 *   start() / stop()
 *
 * 不支持时 supported === false，调用处应隐藏麦克风按钮。
 */

import { useCallback, useEffect, useState } from 'react'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'

export function usePetAsr() {
  const { transcript, interimTranscript, listening, resetTranscript, browserSupportsSpeechRecognition } = useSpeechRecognition()
  const [supported, setSupported] = useState(false)

  useEffect(() => {
    // react-speech-recognition 在 SSR/不支持时会抛或返回 false
    setSupported(browserSupportsSpeechRecognition)
  }, [browserSupportsSpeechRecognition])

  const start = useCallback(() => {
    if (!supported) return
    resetTranscript()
    SpeechRecognition.startListening({ language: 'zh-CN', continuous: true })
  }, [supported, resetTranscript])

  const stop = useCallback(() => {
    if (!supported) return
    SpeechRecognition.stopListening()
  }, [supported])

  const reset = useCallback(() => {
    resetTranscript()
  }, [resetTranscript])

  return {
    listening,
    transcript,
    interimTranscript,
    supported,
    start,
    stop,
    reset,
  }
}

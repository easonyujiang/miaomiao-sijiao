'use client'

/**
 * 妙喵语音朗读 hook —— 后端 edge-tts 播放器
 *
 * 用法：
 *   const { speaking, speak, stop } = usePetTts()
 *   speak('这句话会被朗读')
 *
 * 会复用全局静音开关（与 useMiaoSound 同一个 localStorage key）。
 */

import { useCallback, useEffect, useRef, useState } from 'react'

const MUTE_STORAGE_KEY = 'miaomiao_muted'

export type TTSOptions = {
  voice?: string
  rate?: string
  volume?: string
  pitch?: string
}

export function usePetTts() {
  const [speaking, setSpeaking] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // 取消进行中的朗读
  const stop = useCallback(() => {
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.currentTime = 0
      audioRef.current = null
    }
    setSpeaking(false)
  }, [])

  const speak = useCallback(async (text: string, options: TTSOptions = {}) => {
    stop()

    // 全局静音时不朗读
    try {
      if (localStorage.getItem(MUTE_STORAGE_KEY) === '1') return
    } catch { /* SSR/隐私模式 */ }

    setSpeaking(true)
    try {
      const response = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, ...options }),
      })
      if (!response.ok) throw new Error(`TTS ${response.status}`)

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio

      await new Promise<void>((resolve, reject) => {
        audio.addEventListener('ended', () => {
          URL.revokeObjectURL(url)
          audioRef.current = null
          setSpeaking(false)
          resolve()
        }, { once: true })
        audio.addEventListener('error', (event) => {
          URL.revokeObjectURL(url)
          audioRef.current = null
          setSpeaking(false)
          reject(event)
        }, { once: true })
        void audio.play().catch((error) => {
          URL.revokeObjectURL(url)
          audioRef.current = null
          setSpeaking(false)
          reject(error)
        })
      })
    } catch (error) {
      setSpeaking(false)
      // eslint-disable-next-line no-console
      console.error('TTS failed:', error)
    }
  }, [stop])

  // 卸载时清理
  useEffect(() => () => stop(), [stop])

  return { speaking, speak, stop }
}

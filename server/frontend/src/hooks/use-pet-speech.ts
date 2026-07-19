'use client'

/**
 * 妙喵说话队列 hook
 * 按句切换猫形态，支持后端返回的 segments，也支持本地兜底。
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  type CatStateKey,
  type SpeechSegment,
  FORM_PROTECTED,
  moodFor,
  calcDuration,
} from '@/src/data/cat-states'

export function usePetSpeech() {
  const [catState, setCatState] = useState<CatStateKey>('idle')
  const [speechText, setSpeechText] = useState('')
  const [speechVisible, setSpeechVisible] = useState(false)

  const queueRef = useRef<SpeechSegment[]>([])
  const indexRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clear = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = null
    queueRef.current = []
    indexRef.current = 0
  }, [])

  const say = useCallback((text: string, ms?: number, form: CatStateKey = 'idle') => {
    clear()
    setSpeechText(text)
    setSpeechVisible(true)
    if (!FORM_PROTECTED.includes(catState)) {
      setCatState(form)
    }
    timerRef.current = setTimeout(() => {
      setSpeechVisible(false)
      if (!FORM_PROTECTED.includes(form)) setCatState('idle')
    }, ms ?? calcDuration(text))
  }, [clear, catState])

  const playNext = useCallback(() => {
    if (indexRef.current >= queueRef.current.length) {
      setSpeechVisible(false)
      if (!FORM_PROTECTED.includes(catState)) setCatState('idle')
      return
    }
    const seg = queueRef.current[indexRef.current++]
    const duration = seg.duration_ms ?? calcDuration(seg.text)
    const form = seg.form ?? moodFor(seg.text)
    setSpeechText(seg.text)
    setSpeechVisible(true)
    setCatState(form)
    timerRef.current = setTimeout(playNext, duration)
  }, [catState])

  const saySequence = useCallback((segments: SpeechSegment[]) => {
    if (!segments.length) return
    clear()
    queueRef.current = segments
    indexRef.current = 0
    playNext()
  }, [clear, playNext])

  useEffect(() => {
    return () => clear()
  }, [clear])

  return {
    catState,
    speechText,
    speechVisible,
    say,
    saySequence,
    setCatState,
  }
}

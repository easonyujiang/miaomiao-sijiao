'use client'

import { useCallback, useRef, useState } from 'react'

type SpeechRecognitionState = 'idle' | 'listening' | 'processing' | 'error' | 'not-supported'

interface UseSpeechRecognitionReturn {
  state: SpeechRecognitionState
  transcript: string
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
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  const isSupported = typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setState('idle')
  }, [])

  const start = useCallback(() => {
    if (!isSupported) {
      setState('not-supported')
      return
    }

    stop()
    setTranscript('')
    setState('listening')

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognitionRef.current = recognition

    recognition.lang = 'zh-CN'
    recognition.interimResults = true
    recognition.continuous = true
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

    recognition.onerror = (event: Event & { error?: string }) => {
      if (event.error === 'aborted') return
      console.error('Speech recognition error:', event.error)
      setState('error')
      recognitionRef.current = null
    }

    recognition.onend = () => {
      setState('idle')
      recognitionRef.current = null
    }

    recognition.start()
  }, [isSupported, stop])

  return { state, transcript, start, stop, isSupported }
}

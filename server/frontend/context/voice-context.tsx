'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  matchCommand,
  type VoiceCommand,
  type VoiceStatus,
} from '@/lib/voice-commands'

// ── Speech Recognition wrapper ──────────────────────────────────────────

function createRecognition(): SpeechRecognition | null {
  if (typeof window === 'undefined') return null
  const win = window as unknown as Record<string, unknown>
  const Ctor: typeof SpeechRecognition | undefined =
    (win['SpeechRecognition'] ?? win['webkitSpeechRecognition']) as typeof SpeechRecognition | undefined
  if (!Ctor) return null
  const r = new Ctor()
  r.lang = 'zh-CN'
  r.interimResults = true
  r.continuous = true
  r.maxAlternatives = 1
  return r
}

// ── Context shape ───────────────────────────────────────────────────────

interface VoiceContextValue {
  status: VoiceStatus
  isListening: boolean
  transcript: string
  lastCommand: VoiceCommand | null
  showHelp: boolean
  startListening: () => void
  stopListening: () => void
  setShowHelp: (v: boolean) => void
  registerCommands: (commands: VoiceCommand[]) => () => void
  supported: boolean
}

const VoiceContext = createContext<VoiceContextValue>({
  status: 'idle',
  isListening: false,
  transcript: '',
  lastCommand: null,
  showHelp: false,
  startListening: () => {},
  stopListening: () => {},
  setShowHelp: () => {},
  registerCommands: () => () => {},
  supported: false,
})

// ── Provider ────────────────────────────────────────────────────────────

export function VoiceProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [transcript, setTranscript] = useState('')
  const [lastCommand, setLastCommand] = useState<VoiceCommand | null>(null)
  const [showHelp, setShowHelp] = useState(false)
  const [supported] = useState(() => createRecognition() !== null)

  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const commandsRef = useRef<VoiceCommand[]>([])
  const statusTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const restartTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const listeningRef = useRef(false)

  // Clear any pending status timeout
  const clearStatusTimeout = useCallback(() => {
    if (statusTimeoutRef.current) {
      clearTimeout(statusTimeoutRef.current)
      statusTimeoutRef.current = null
    }
  }, [])

  // Register a batch of commands; returns an unregister function
  const registerCommands = useCallback((commands: VoiceCommand[]) => {
    commandsRef.current = [...commandsRef.current, ...commands]

    return () => {
      const ids = new Set(commands.map(c => c.id))
      commandsRef.current = commandsRef.current.filter(c => !ids.has(c.id))
    }
  }, [])

  // Start listening
  const startListening = useCallback(() => {
    if (!supported) return
    if (listeningRef.current) return

    const r = createRecognition()
    if (!r) return

    recognitionRef.current = r
    listeningRef.current = true
    setStatus('listening')

    r.onresult = (event: SpeechRecognitionEvent) => {
      let final = ''
      let interim = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          final += result[0]?.transcript ?? ''
        } else {
          interim += result[0]?.transcript ?? ''
        }
      }

      const text = final || interim
      if (text) {
        setTranscript(text)
      }

      // Only try matching on final results
      if (final) {
        const matched = matchCommand(final, commandsRef.current)
        if (matched) {
          setLastCommand(matched)
          setStatus('recognized')

          clearStatusTimeout()
          statusTimeoutRef.current = setTimeout(() => {
            setStatus('executing')
            matched.handler()

            statusTimeoutRef.current = setTimeout(() => {
              setStatus('listening')
            }, 600)
          }, 400)
        }
      }
    }

    r.onerror = (event: Event) => {
      const err = event as SpeechRecognitionErrorEvent
      // 'no-speech' and 'aborted' are normal; only treat real errors
      if (err.error === 'not-allowed') {
        setStatus('error')
        listeningRef.current = false
        clearStatusTimeout()
        statusTimeoutRef.current = setTimeout(() => setStatus('idle'), 2000)
      }
      // For other errors, try to restart
      if (err.error === 'network' || err.error === 'service-not-allowed') {
        setStatus('error')
        listeningRef.current = false
        clearStatusTimeout()
        statusTimeoutRef.current = setTimeout(() => {
          if (listeningRef.current === false) {
            // User hasn't manually stopped; retry
            startListening()
          }
        }, 1000)
      }
    }

    r.onend = () => {
      // Auto-restart if still in listening mode
      if (listeningRef.current) {
        restartTimeoutRef.current = setTimeout(() => {
          if (listeningRef.current) {
            try { r.start() } catch { /* ignore */ }
          }
        }, 200)
      }
    }

    try {
      r.start()
    } catch {
      // Already started
    }
  }, [supported, clearStatusTimeout])

  // Stop listening
  const stopListening = useCallback(() => {
    listeningRef.current = false
    clearStatusTimeout()
    if (restartTimeoutRef.current) {
      clearTimeout(restartTimeoutRef.current)
      restartTimeoutRef.current = null
    }
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch { /* ignore */ }
      recognitionRef.current = null
    }
    setStatus('idle')
    setTranscript('')
  }, [clearStatusTimeout])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      listeningRef.current = false
      clearStatusTimeout()
      if (restartTimeoutRef.current) {
        clearTimeout(restartTimeoutRef.current)
      }
      if (recognitionRef.current) {
        try { recognitionRef.current.stop() } catch { /* ignore */ }
      }
    }
  }, [clearStatusTimeout])

  return (
    <VoiceContext.Provider
      value={{
        status,
        isListening: status === 'listening' || status === 'recognized' || status === 'executing',
        transcript,
        lastCommand,
        showHelp,
        startListening,
        stopListening,
        setShowHelp,
        registerCommands,
        supported,
      }}
    >
      {children}
    </VoiceContext.Provider>
  )
}

// ── Hook ────────────────────────────────────────────────────────────────

export function useVoice() {
  return useContext(VoiceContext)
}

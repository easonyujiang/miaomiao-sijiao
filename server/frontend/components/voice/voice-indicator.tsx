'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Mic, MicOff, Check, HelpCircle } from 'lucide-react'
import { useVoice } from '@/context/voice-context'
import { buildNavCommands, buildVoiceCommands } from '@/lib/voice-commands'
import { useRouter } from 'next/navigation'

export function VoiceIndicator() {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const {
    status,
    isListening,
    transcript,
    lastCommand,
    startListening,
    stopListening,
    setShowHelp,
    registerCommands,
    supported,
  } = useVoice()

  // Register global navigation + voice control commands
  useEffect(() => {
    setMounted(true)
    const navCmds = buildNavCommands((path) => router.push(path))
    const voiceCmds = buildVoiceCommands(
      startListening,
      stopListening,
      () => setShowHelp(true),
    )
    const unregister = registerCommands([...navCmds, ...voiceCmds])
    return unregister
  }, [router, startListening, stopListening, setShowHelp, registerCommands])

  if (!mounted || !supported) return null

  const statusIcon = () => {
    switch (status) {
      case 'listening':
        return <Mic className="h-5 w-5 text-blue-500" />
      case 'recognized':
        return <Check className="h-5 w-5 text-green-500" />
      case 'executing':
        return <Check className="h-5 w-5 text-amber-500" />
      case 'error':
        return <MicOff className="h-5 w-5 text-red-500" />
      default:
        return <Mic className="h-5 w-5 text-neutral-400" />
    }
  }

  const statusLabel = () => {
    switch (status) {
      case 'idle': return '点击开始语音'
      case 'listening': return '正在聆听…'
      case 'recognized': return `识别: "${transcript}"`
      case 'executing': return lastCommand ? `执行: ${lastCommand.description}` : '执行中…'
      case 'error': return '语音识别出错'
    }
  }

  const pulseRing =
    status === 'listening'
      ? {
          boxShadow: [
            '0 0 0 0px rgba(59, 130, 246, 0.4)',
            '0 0 0 12px rgba(59, 130, 246, 0)',
          ],
        }
      : {}

  return (
    <div className="fixed bottom-5 left-5 z-40 flex flex-col items-center gap-2">
      {/* Transcript tooltip */}
      <AnimatePresence>
        {isListening && transcript && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="rounded-lg bg-white border border-neutral-200 px-3 py-1.5 text-xs text-neutral-600 shadow-sm max-w-48 text-center"
          >
            {transcript}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Status label */}
      <motion.span
        key={status}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-[10px] text-neutral-400 font-medium tracking-wide"
      >
        {statusLabel()}
      </motion.span>

      {/* Mic button */}
      <motion.button
        onClick={() => (isListening ? stopListening() : startListening())}
        aria-label={isListening ? '关闭语音' : '打开语音'}
        className="relative flex h-12 w-12 items-center justify-center rounded-full border border-neutral-200 bg-white shadow-lg"
        animate={pulseRing}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.95 }}
      >
        {statusIcon()}
      </motion.button>

      {/* Help button */}
      <motion.button
        onClick={() => setShowHelp(true)}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-neutral-100 bg-white text-neutral-300 hover:text-neutral-500 transition-colors"
        aria-label="语音帮助"
        whileHover={{ scale: 1.1 }}
      >
        <HelpCircle className="h-3.5 w-3.5" />
      </motion.button>
    </div>
  )
}

'use client'

import type { ReactNode } from 'react'
import { VoiceProvider } from '@/context/voice-context'
import { VoiceIndicator } from '@/components/voice/voice-indicator'
import { VoiceHelpPanel } from '@/components/voice/voice-help-panel'

export function AppWrapper({ children }: { children: ReactNode }) {
  return (
    <VoiceProvider>
      {children}
      <VoiceIndicator />
      <VoiceHelpPanel />
    </VoiceProvider>
  )
}

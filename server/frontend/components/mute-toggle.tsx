'use client'

/**
 * 全局静音开关 —— header 右侧 🔊/🔇
 * 静音偏好持久化在 localStorage（miaomiao_muted），与插件端 chrome.storage 各自独立
 */

import { Volume2, VolumeX } from 'lucide-react'
import { useMiaoSound } from '@/src/hooks/use-miao-sound'

export function MuteToggle() {
  const { muted, toggleMute } = useMiaoSound()
  return (
    <button
      type="button"
      onClick={toggleMute}
      aria-label={muted ? '取消静音' : '静音'}
      title={muted ? '取消静音' : '静音'}
      className="text-neutral-400 transition hover:text-neutral-950"
    >
      {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
    </button>
  )
}

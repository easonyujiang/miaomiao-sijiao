'use client'

/**
 * 妙喵音效 hook —— use-sound 薄封装
 *
 * 用法：
 *   const { play, startThinking, stopThinking, muted, toggleMute } = useMiaoSound()
 *   play('pass'); startThinking(); stopThinking(); toggleMute()
 *
 * 依赖：npm install use-sound（howler 为其懒加载依赖）
 * 资产：frontend/public/sounds/*.mp3（见购置方案 §1.2）
 * 注意：浏览器 autoplay 政策 —— 首次用户交互前调用 play 会被 howler 静默忽略，属预期行为
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import useSound from 'use-sound'
import type { SoundKey } from '@/src/data/cat-states'

/** 音量分级（购置方案 §六：错误音不能刺耳） */
const VOLUME: Record<SoundKey, number> = {
  'pop-open': 0.5, 'pop-close': 0.5,
  send: 0.5, receive: 0.5,
  thinking: 0.15,          // 循环背景音，极轻
  meow: 0.6,               // 品牌音
  pass: 0.7, perfect: 0.7, 'level-up': 0.7,
  fail: 0.4,               // 不惩罚感
  seek: 0.5, badge: 0.5,
  click: 0.2,              // 几乎不可察觉
  yawn: 0.5,
}

const MUTE_STORAGE_KEY = 'miaomiao_muted'

export function useMiaoSound() {
  const [muted, setMuted] = useState(false)

  // 初始化读取静音偏好
  useEffect(() => {
    try { setMuted(localStorage.getItem(MUTE_STORAGE_KEY) === '1') } catch { /* SSR/隐私模式 */ }
  }, [])

  // 每个音效一个 use-sound 实例（sprite 合并是后续优化项）
  const players = {
    'pop-open': useSound('/sounds/pop-open.mp3', { volume: VOLUME['pop-open'], interrupt: true, soundEnabled: !muted }),
    'pop-close': useSound('/sounds/pop-close.mp3', { volume: VOLUME['pop-close'], soundEnabled: !muted }),
    send: useSound('/sounds/send.mp3', { volume: VOLUME.send, soundEnabled: !muted }),
    receive: useSound('/sounds/receive.mp3', { volume: VOLUME.receive, soundEnabled: !muted }),
    thinking: useSound('/sounds/thinking.mp3', { volume: VOLUME.thinking, loop: true, soundEnabled: !muted }),
    meow: useSound('/sounds/meow.mp3', { volume: VOLUME.meow, soundEnabled: !muted }),
    pass: useSound('/sounds/pass.mp3', { volume: VOLUME.pass, interrupt: true, soundEnabled: !muted }),
    perfect: useSound('/sounds/perfect.mp3', { volume: VOLUME.perfect, soundEnabled: !muted }),
    fail: useSound('/sounds/fail.mp3', { volume: VOLUME.fail, soundEnabled: !muted }),
    seek: useSound('/sounds/seek.mp3', { volume: VOLUME.seek, soundEnabled: !muted }),
    'level-up': useSound('/sounds/level-up.mp3', { volume: VOLUME['level-up'], soundEnabled: !muted }),
    click: useSound('/sounds/click.mp3', { volume: VOLUME.click, interrupt: true, soundEnabled: !muted }),
    badge: useSound('/sounds/badge.mp3', { volume: VOLUME.badge, soundEnabled: !muted }),
    yawn: useSound('/sounds/yawn.mp3', { volume: VOLUME.yawn, soundEnabled: !muted }),
  } satisfies Record<SoundKey, ReturnType<typeof useSound>>

  const thinkingIdRef = useRef<number | null>(null)

  const play = useCallback((key: SoundKey) => {
    const [p] = players[key]
    p()
  }, [muted]) // eslint-disable-line react-hooks/exhaustive-deps

  /** 判卷循环音开始（返回的 id 由内部管理，重复调用安全） */
  const startThinking = useCallback(() => {
    const [p, { sound }] = players.thinking
    if (thinkingIdRef.current == null && sound) {
      thinkingIdRef.current = p() as unknown as number
    }
  }, [muted]) // eslint-disable-line react-hooks/exhaustive-deps

  const stopThinking = useCallback(() => {
    const [, { stop }] = players.thinking
    if (thinkingIdRef.current != null) {
      // use-sound v5 的 d.ts 把 stop(id) 误标为 string；howler 运行时按数字严格相等比较，必须传数字
      stop(thinkingIdRef.current as unknown as string)
      thinkingIdRef.current = null
    }
  }, [muted]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleMute = useCallback(() => {
    setMuted((m) => {
      const next = !m
      try { localStorage.setItem(MUTE_STORAGE_KEY, next ? '1' : '0') } catch { /* ignore */ }
      if (next) stopThinking()
      return next
    })
  }, [stopThinking])

  return { play, startThinking, stopThinking, muted, toggleMute }
}

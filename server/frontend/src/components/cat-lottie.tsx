'use client'

/**
 * 状态猫组件 —— 给一个状态 key，渲染对应 Lottie 猫，自动联动音效
 *
 * 用法：
 *   <CatLottie state="analyzing" size={120} sound />
 *   <CatLottie state="celebrating" soundOverride="perfect" />   // 3星完美
 *
 * 依赖：npm install lottie-react
 * 资产：frontend/public/lottie/*.json（见购置方案 §1.1）
 */

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import { CAT_STATES, type CatStateKey, type SoundKey } from '@/src/data/cat-states'
import { useMiaoSound } from '@/src/hooks/use-miao-sound'

// lottie-react 依赖 window，必须关 SSR
const Lottie = dynamic(() => import('lottie-react'), { ssr: false })

/** JSON 缓存：同一文件只 fetch 一次 */
const animationCache = new Map<string, Promise<unknown>>()
function loadAnimation(file: string) {
  if (!animationCache.has(file)) {
    animationCache.set(
      file,
      fetch(`/lottie/${file}`).then((r) => {
        if (!r.ok) throw new Error(`lottie ${file} ${r.status}`)
        return r.json()
      }),
    )
  }
  return animationCache.get(file)!
}

export function CatLottie({
  state,
  size = 96,
  sound = false,
  soundOverride,
  className,
}: {
  state: CatStateKey
  size?: number
  /** true = 进入状态时播放注册表里的联动音效 */
  sound?: boolean
  /** 覆盖联动音效（如 3 星时传 'perfect'） */
  soundOverride?: SoundKey
  className?: string
}) {
  const def = CAT_STATES[state]
  const [data, setData] = useState<unknown>(null)
  const { play, startThinking, stopThinking } = useMiaoSound()

  // 加载动画数据
  useEffect(() => {
    let alive = true
    loadAnimation(def.file)
      .then((d) => alive && setData(d))
      .catch(() => alive && setData(null))
    return () => { alive = false }
  }, [def.file])

  // 音效联动
  useEffect(() => {
    if (!sound) return
    const key = soundOverride ?? def.sound
    if (key) play(key)
    if (def.thinkingLoop) {
      startThinking()
      return () => stopThinking()
    }
  }, [state]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      role="img"
      aria-label={def.label}
      title={def.label}
      className={className}
      style={{ width: size, height: size }}
    >
      {data ? (
        <Lottie animationData={data} loop={def.loop} autoplay style={{ width: '100%', height: '100%' }} />
      ) : (
        // JSON 未加载完成前的占位（保持布局不抖动）
        <span style={{ fontSize: size * 0.5, lineHeight: `${size}px`, display: 'block', textAlign: 'center' }}>🐱</span>
      )}
    </div>
  )
}

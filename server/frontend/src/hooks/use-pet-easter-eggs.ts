'use client'

/**
 * 妙喵桌宠彩蛋 hook
 *
 * 给 CatLottie 增加点击、双击、右键菜单等趣味交互：
 * - 单击：切换形态 + 随机喵语
 * - 快速连击 3 次："不要再戳啦～"
 * - 双击：撒花庆祝
 * - 右键：喂食 / 跳舞 / 睡觉 / 伸懒腰
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import confetti from 'canvas-confetti'
import type { CatStateKey, SoundKey } from '@/src/data/cat-states'

type Point = { x: number; y: number }

const EGG_STATES: CatStateKey[] = ['idle', 'tail', 'sleepy', 'stretch', 'celebrating']

const PAT_PHRASES = [
  '喵～',
  '再点一下？',
  '好舒服～',
  '我在这里！',
  '今天学什么？',
  '妙喵盯着你 👀',
]

const POKED_PHRASES = [
  '不要再戳啦～',
  '脸都要被戳扁了！',
  '再戳我就睡觉了 💤',
]

export function usePetEasterEggs(
  setCatState: (state: CatStateKey) => void,
  play: (key: SoundKey) => void,
  say: (text: string, ms?: number, form?: CatStateKey) => void,
) {
  const [eggIndex, setEggIndex] = useState(0)
  const [eggText, setEggText] = useState<string | null>(null)
  const [menu, setMenu] = useState<{ visible: boolean; pos: Point }>({ visible: false, pos: { x: 0, y: 0 } })
  const patCountRef = useRef(0)
  const patTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const eggTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearEggText = useCallback(() => {
    if (eggTimerRef.current) clearTimeout(eggTimerRef.current)
    eggTimerRef.current = null
    setEggText(null)
  }, [])

  const showEggText = useCallback((text: string, ms = 1500) => {
    clearEggText()
    setEggText(text)
    eggTimerRef.current = setTimeout(() => setEggText(null), ms)
  }, [clearEggText])

  const pat = useCallback(() => {
    play('click')
    patCountRef.current += 1

    // 快速连击判定窗口 600ms
    if (patTimerRef.current) clearTimeout(patTimerRef.current)
    patTimerRef.current = setTimeout(() => {
      patCountRef.current = 0
    }, 600)

    if (patCountRef.current >= 3) {
      patCountRef.current = 0
      play('meow')
      showEggText(POKED_PHRASES[Math.floor(Math.random() * POKED_PHRASES.length)])
      setCatState('sleepy')
      return
    }

    const nextIndex = (eggIndex + 1) % EGG_STATES.length
    setEggIndex(nextIndex)
    const nextState = EGG_STATES[nextIndex]
    setCatState(nextState)

    // 庆祝形态时播放音效
    if (nextState === 'celebrating') play('pass')

    showEggText(PAT_PHRASES[Math.floor(Math.random() * PAT_PHRASES.length)])
  }, [eggIndex, play, setCatState, showEggText])

  const celebrate = useCallback(() => {
    play('level-up')
    setCatState('celebrating')
    say('妙喵为你庆祝！', 2000, 'celebrating')
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.8 },
      colors: ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1'],
    })
  }, [play, setCatState, say])

  const feed = useCallback(() => {
    play('badge')
    setCatState('reward')
    showEggText('小鱼干真香～', 2000)
  }, [play, setCatState, showEggText])

  const dance = useCallback(() => {
    play('pass')
    setCatState('celebrating')
    showEggText('一起跳舞吧！', 2000)
  }, [play, setCatState, showEggText])

  const sleep = useCallback(() => {
    play('yawn')
    setCatState('sleepy')
    showEggText('zzz…', 2000)
  }, [play, setCatState, showEggText])

  const stretch = useCallback(() => {
    play('click')
    setCatState('stretch')
    showEggText('伸个懒腰～', 2000)
  }, [play, setCatState, showEggText])

  const openMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault()
    play('click')
    setMenu({ visible: true, pos: { x: event.clientX, y: event.clientY } })
  }, [play])

  const closeMenu = useCallback(() => {
    setMenu((m) => ({ ...m, visible: false }))
  }, [])

  useEffect(() => {
    const handleClick = () => closeMenu()
    if (menu.visible) {
      window.addEventListener('click', handleClick, { once: true })
      return () => window.removeEventListener('click', handleClick)
    }
  }, [menu.visible, closeMenu])

  useEffect(() => {
    return () => {
      if (patTimerRef.current) clearTimeout(patTimerRef.current)
      if (eggTimerRef.current) clearTimeout(eggTimerRef.current)
    }
  }, [])

  return {
    eggText,
    menu,
    pat,
    celebrate,
    feed,
    dance,
    sleep,
    stretch,
    openMenu,
    closeMenu,
  }
}

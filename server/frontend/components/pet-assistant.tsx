'use client'

import { FormEvent, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'motion/react'
import { MessageCircle, Mic, MicOff, Volume2, VolumeX } from 'lucide-react'
import type { SiteProfile } from '@/src/data/siteProfile'
import { chatWithPet, createSiteSession, type AgentAction, type SiteSession } from '@/src/lib/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { CatLottie } from '@/src/components/cat-lottie'
import { useMiaoSound } from '@/src/hooks/use-miao-sound'
import { usePetSpeech } from '@/src/hooks/use-pet-speech'
import { usePetAsr } from '@/src/hooks/use-pet-asr'
import { usePetTts } from '@/src/hooks/use-pet-tts'
import { usePetEasterEggs } from '@/src/hooks/use-pet-easter-eggs'
import { moodFor, type SpeechSegment } from '@/src/data/cat-states'

type Message = { id: string; role: 'visitor' | 'pet'; text: string; action?: AgentAction }

export function PetAssistant({ profile }: { profile: SiteProfile }) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [session, setSession] = useState<SiteSession | null>(null)
  const [status, setStatus] = useState<'connecting' | 'online' | 'offline'>('connecting')
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)
  const [messages, setMessages] = useState<Message[]>([{ id: 'welcome', role: 'pet', text: profile.pet.greeting }])
  const { play } = useMiaoSound()
  const { catState, speechText, speechVisible, say, saySequence, setCatState } = usePetSpeech()
  const { listening, transcript, interimTranscript, supported: asrSupported, start: startAsr, stop: stopAsr, reset: resetAsr } = usePetAsr()
  const { speaking, speak: speakTts, stop: stopTts } = usePetTts()
  const { eggText, menu, pat, celebrate, feed, dance, sleep, stretch, openMenu, closeMenu } = usePetEasterEggs(setCatState, play, say)
  const firstOpenRef = useRef(true)

  // ASR 转写实时回填输入框
  useEffect(() => {
    const text = transcript || interimTranscript
    if (text) setQuestion(text)
  }, [transcript, interimTranscript])

  // 停止语音输入后若拿到文本则自动提交
  useEffect(() => {
    if (!listening && transcript.trim() && !pending) {
      const text = transcript.trim()
      resetAsr()
      void ask(text)
    }
  }, [listening, transcript, pending, resetAsr])

  function handleOpenChange(next: boolean) {
    setOpen(next)
    if (next) {
      play('pop-open')
      if (firstOpenRef.current) {
        firstOpenRef.current = false
        play('meow')
        say(profile.pet.greeting, 4500, 'celebrating')
      }
    } else {
      play('pop-close')
    }
  }

  useEffect(() => {
    const keyName = 'miaomiao_anonymous_key'
    const key = localStorage.getItem(keyName) ?? crypto.randomUUID()
    localStorage.setItem(keyName, key)
    void createSiteSession(key).then((value) => { setSession(value); setStatus('online') }).catch(() => setStatus('offline'))
  }, [])

  function localAnswer(text: string) {
    const faq = profile.faq.find((item) => text.includes(item.question.replace(/[？?]/g, '')))
      ?? profile.faq.find((item) => /视频|进度条|片段/.test(text) ? item.id === 'video-navigation' : /项目|作品/.test(text) ? item.id === 'project' : item.id === 'who')
      ?? profile.faq[0]
    const action: AgentAction | undefined = faq.videoId
      ? { type: faq.seekTo ? 'seek_video' : 'open_video', video_id: faq.videoId, time_ms: (faq.seekTo ?? 0) * 1000, label: faq.seekTo ? `跳到 ${faq.seekTo} 秒` : '打开内容' }
      : faq.target ? { type: 'open_section', target: faq.target, label: '查看相关内容' } : undefined
    return { text: faq.answer, action }
  }

  async function ask(raw: string) {
    const text = raw.trim()
    if (!text || pending) return
    setQuestion('')
    setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'visitor', text }])
    setPending(true)
    setCatState('listening')
    play('send')
    try {
      const response = await chatWithPet(text, { sessionId: session?.session_id })
      play('receive')
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'pet', text: response.answer, action: response.actions[0] }])
      // 每句话切形态
      const segments: SpeechSegment[] | undefined = response.segments
      if (segments && segments.length > 0) {
        saySequence(segments)
      } else {
        say(response.answer, 5000, moodFor(response.answer))
      }
    } catch {
      play('receive')
      const answer = localAnswer(text)
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'pet', ...answer }])
      say(answer.text, 5000, moodFor(answer.text))
    } finally {
      setPending(false)
    }
  }

  function runAction(action: AgentAction) {
    if ((action.type === 'seek_video' || action.type === 'open_video') && action.video_id) {
      router.push(`/projects?video=${encodeURIComponent(action.video_id)}&t=${Math.round((action.time_ms ?? 0) / 1000)}`)
    } else if (action.target === 'projects' || action.target === 'videos') {
      router.push('/projects')
    } else {
      router.push('/')
    }
    setOpen(false)
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void ask(question)
  }

  const menuItems = [
    { label: '喂食小鱼干', action: () => { closeMenu(); feed() } },
    { label: '跳舞', action: () => { closeMenu(); dance() } },
    { label: '睡觉', action: () => { closeMenu(); sleep() } },
    { label: '伸懒腰', action: () => { closeMenu(); stretch() } },
  ]

  return <Dialog open={open} onOpenChange={handleOpenChange}>
    <DialogTrigger asChild>
      <motion.button
        data-pet-assistant
        aria-label="打开妙喵"
        className="fixed bottom-5 right-5 z-40 flex h-12 w-12 items-center justify-center rounded-full border border-neutral-200 bg-white text-xl shadow-lg"
        animate={{ y: [0, -4, 0] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
        whileHover={{ scale: 1.06 }}
        onDoubleClick={() => { play('click'); celebrate() }}
      >🐱</motion.button>
    </DialogTrigger>
    <DialogContent data-pet-assistant className="overflow-visible">
      {speechVisible && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.92 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          className="absolute -top-16 left-4 max-w-[220px] rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-700 shadow-lg"
        >
          {speechText}
        </motion.div>
      )}
      {eggText && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.92 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          className="absolute -top-14 left-4 max-w-[180px] rounded-xl border border-neutral-200 bg-white px-3 py-1.5 text-xs text-neutral-700 shadow-lg"
        >
          {eggText}
        </motion.div>
      )}
      <div
        className="absolute -top-2 right-4 -translate-y-full cursor-pointer select-none"
        onClick={() => pat()}
        onDoubleClick={() => celebrate()}
        onContextMenu={openMenu}
        title="单击切换形态 · 双击庆祝 · 右键菜单"
      >
        <CatLottie state={catState} size={72} sound={catState !== 'idle'} soundOverride={catState === 'levelup' ? 'level-up' : undefined} />
      </div>
      {menu.visible && (
        <div
          className="fixed z-50 min-w-[120px] rounded-lg border border-neutral-200 bg-white py-1 text-xs shadow-lg"
          style={{ left: menu.pos.x, top: menu.pos.y }}
        >
          {menuItems.map((item) => (
            <button
              key={item.label}
              type="button"
              className="block w-full px-3 py-1.5 text-left text-neutral-700 hover:bg-neutral-100"
              onClick={item.action}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
      <div className="border-b border-neutral-100 px-4 py-3 pr-12">
        <DialogTitle className="text-sm font-medium">{profile.pet.name}</DialogTitle>
        <DialogDescription className="mt-0.5 text-xs text-neutral-400">{status === 'online' ? 'Connected to knowledge base' : status === 'connecting' ? 'Connecting…' : 'Offline answers'}</DialogDescription>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((message) => <div key={message.id} className={`flex ${message.role === 'visitor' ? 'justify-end' : 'justify-start'}`}>
          <div className={`max-w-[88%] rounded-xl px-3 py-2 text-sm leading-6 ${message.role === 'visitor' ? 'bg-neutral-900 text-white' : 'bg-neutral-100'}`}>
            <p>{message.text}</p>
            {message.role === 'pet' && (
              <button
                type="button"
                aria-label={speaking ? '停止朗读' : '朗读'}
                title={speaking ? '停止朗读' : '朗读'}
                className="mt-1 inline-flex items-center gap-1 text-[11px] text-neutral-400 hover:text-neutral-600 disabled:opacity-50"
                disabled={speaking}
                onClick={() => {
                  play('click')
                  if (speaking) stopTts()
                  else void speakTts(message.text)
                }}
              >
                {speaking ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
                {speaking ? '朗读中…' : '朗读'}
              </button>
            )}
            {message.action && <Button size="sm" variant="outline" className="mt-2 bg-white text-neutral-900" onClick={() => runAction(message.action!)}>{message.action.label} →</Button>}
          </div>
        </div>)}
        {pending && <div className="w-fit rounded-xl bg-neutral-100 px-3 py-2" aria-live="polite"><CatLottie state="analyzing" size={64} sound /></div>}
      </div>
      <div className="border-t border-neutral-100 p-3">
        <div className="mb-2 flex gap-2 overflow-x-auto">{profile.faq.slice(0, 3).map((item) => <button key={item.id} onClick={() => void ask(item.question)} className="shrink-0 rounded-full bg-neutral-100 px-3 py-1 text-[11px] text-neutral-500">{item.question}</button>)}</div>
        <form onSubmit={submit} className="flex gap-2">
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask anything" className="min-w-0 flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400"/>
          {asrSupported && (
            <Button
              type="button"
              size="icon"
              variant={listening ? 'default' : 'outline'}
              aria-label={listening ? '停止语音输入' : '语音输入'}
              title={listening ? '停止语音输入' : '语音输入'}
              disabled={pending}
              onClick={() => {
                play('click')
                if (listening) stopAsr()
                else { setQuestion(''); startAsr() }
              }}
            >
              {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </Button>
          )}
          <Button type="submit" size="icon" disabled={pending}><MessageCircle className="h-4 w-4" /></Button>
        </form>
      </div>
    </DialogContent>
  </Dialog>
}

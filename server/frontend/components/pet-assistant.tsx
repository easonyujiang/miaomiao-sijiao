'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'motion/react'
import { MessageCircle, Mic } from 'lucide-react'
import type { SiteProfile } from '@/src/data/siteProfile'
import { chatWithPet, chatWithVoice, createSiteSession, type AgentAction, type SiteSession } from '@/src/lib/api'
import { generateId } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { useVoiceChat } from '@/lib/useVoiceChat'

type Message = { id: string; role: 'visitor' | 'pet'; text: string; action?: AgentAction }

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="inline-block h-1.5 w-1.5 rounded-full bg-neutral-400"
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </span>
  )
}

export function PetAssistant({ profile }: { profile: SiteProfile }) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [session, setSession] = useState<SiteSession | null>(null)
  const [status, setStatus] = useState<'connecting' | 'online' | 'offline'>('connecting')
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)
  const [messages, setMessages] = useState<Message[]>([{ id: 'welcome', role: 'pet', text: profile.pet.greeting }])

  const onVoiceReady = useCallback(async (blob: Blob) => {
    setPending(true)
    try {
      const response = await chatWithVoice(blob, { sessionId: session?.session_id })
      const transcript = response.transcript || response.answer
      const action = response.actions[0]
      setMessages((items) => [
        ...items,
        { id: generateId(), role: 'visitor', text: transcript },
        { id: generateId(), role: 'pet', text: response.answer, action },
      ])
    } catch {
      setMessages((items) => [...items, { id: generateId(), role: 'pet', text: '语音聊天服务暂时不可用，请用文字试试~' }])
    } finally {
      setPending(false)
    }
  }, [session?.session_id])

  const voice = useVoiceChat(onVoiceReady)

  useEffect(() => {
    const keyName = 'miaomiao_anonymous_key'
    const key = localStorage.getItem(keyName) ?? generateId()
    localStorage.setItem(keyName, key)
    void createSiteSession(key).then((value) => { setSession(value); setStatus('online') }).catch(() => setStatus('offline'))
  }, [])

  useEffect(() => {
    if (voice.error) {
      setMessages((items) => [...items, { id: generateId(), role: 'pet', text: voice.error }])
    }
  }, [voice.error])

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
    setMessages((items) => [...items, { id: generateId(), role: 'visitor', text }])
    setPending(true)
    try {
      const response = await chatWithPet(text, { sessionId: session?.session_id })
      setMessages((items) => [...items, { id: generateId(), role: 'pet', text: response.answer, action: response.actions[0] }])
    } catch {
      const answer = localAnswer(text)
      setMessages((items) => [...items, { id: generateId(), role: 'pet', ...answer }])
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

  function startVoice() {
    if (voice.state === 'processing') return
    setQuestion('')
    voice.start()
  }

  function stopVoice() {
    if (voice.state === 'recording') {
      voice.stop()
    }
  }

  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild>
      <motion.button
        data-pet-assistant
        aria-label="打开妙喵"
        className="fixed bottom-5 right-5 z-40 flex h-12 w-12 cursor-pointer items-center justify-center rounded-full border border-neutral-200 bg-white text-xl shadow-lg"
        animate={{ y: [0, -4, 0] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
        whileHover={{ scale: 1.06 }}
      >🐱</motion.button>
    </DialogTrigger>
    <DialogContent data-pet-assistant className="sm:max-w-lg h-[70vh] flex flex-col">
      <div className="border-b border-neutral-100 px-4 py-3 pr-12">
        <DialogTitle className="text-sm font-medium">{profile.pet.name}</DialogTitle>
        <DialogDescription className="mt-0.5 text-xs text-neutral-400">{status === 'online' ? 'Connected to knowledge base' : status === 'connecting' ? 'Connecting…' : 'Offline answers'}</DialogDescription>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((message) => <div key={message.id} className={`flex ${message.role === 'visitor' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[88%] rounded-xl px-3 py-2 text-sm leading-6 ${message.role === 'visitor' ? 'bg-neutral-900 text-white' : 'bg-neutral-100'}`}><p>{message.text}</p>{message.action && <Button size="sm" variant="outline" className="mt-2 bg-white text-neutral-900" onClick={() => runAction(message.action!)}>{message.action.label} →</Button>}</div></div>)}
        <AnimatePresence>
          {pending && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="w-fit rounded-xl bg-neutral-100 px-4 py-2.5 text-sm text-neutral-500"
            >
              <ThinkingDots />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      <div className="border-t border-neutral-100 p-3">
        <div className="mb-2 flex gap-2 overflow-x-auto">{profile.faq.slice(0, 3).map((item) => <button key={item.id} onClick={() => void ask(item.question)} className="shrink-0 rounded-full bg-neutral-100 px-3 py-1 text-[11px] text-neutral-500">{item.question}</button>)}</div>

        {/* 微信式录音浮层 */}
        {voice.state === 'recording' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="flex flex-col items-center gap-4 rounded-2xl bg-neutral-900/90 px-8 py-10 text-white shadow-2xl">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-white/10">
                <Mic className="h-8 w-8" />
              </div>
              <div className="flex items-center gap-1">
                <span className="h-2 w-2 animate-bounce rounded-full bg-white" style={{ animationDelay: '0ms' }} />
                <span className="h-2 w-2 animate-bounce rounded-full bg-white" style={{ animationDelay: '150ms' }} />
                <span className="h-2 w-2 animate-bounce rounded-full bg-white" style={{ animationDelay: '300ms' }} />
              </div>
              <p className="text-sm font-medium">正在听…</p>
              <p className="text-xs text-white/60">松开发送</p>
            </div>
          </div>
        )}

        <form onSubmit={submit} className="flex gap-2">
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={voice.state === 'processing' ? '妙喵思考中…' : 'Ask anything'} className="min-w-0 flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400"/>
          {voice.isSupported && (
            <button
              type="button"
              onMouseDown={startVoice}
              onMouseUp={stopVoice}
              onMouseLeave={stopVoice}
              onTouchStart={startVoice}
              onTouchEnd={stopVoice}
              disabled={voice.state === 'processing'}
              title="按住说话"
              className={`flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-md border transition-colors ${
                voice.state === 'recording'
                  ? 'border-red-300 bg-red-50 text-red-500'
                  : voice.state === 'error'
                    ? 'border-amber-300 bg-amber-50 text-amber-500'
                    : voice.state === 'processing'
                      ? 'cursor-not-allowed border-neutral-200 bg-neutral-100 text-neutral-400'
                      : 'border-neutral-200 text-neutral-600 hover:border-neutral-300 hover:text-neutral-900'
              }`}
            >
              {voice.state === 'recording' ? (
                <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 1, repeat: Infinity }}>
                  <Mic className="h-4 w-4" />
                </motion.div>
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </button>
          )}
          <Button type="submit" size="icon" disabled={pending}><MessageCircle className="h-4 w-4" /></Button>
        </form>
      </div>
    </DialogContent>
  </Dialog>
}

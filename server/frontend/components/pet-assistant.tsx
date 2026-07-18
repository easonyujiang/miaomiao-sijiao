'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'motion/react'
import { MessageCircle } from 'lucide-react'
import type { SiteProfile } from '@/src/data/siteProfile'
import { chatWithPet, createSiteSession, type AgentAction, type SiteSession } from '@/src/lib/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/components/ui/dialog'

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
    try {
      const response = await chatWithPet(text, { sessionId: session?.session_id })
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'pet', text: response.answer, action: response.actions[0] }])
    } catch {
      const answer = localAnswer(text)
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'pet', ...answer }])
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

  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild>
      <motion.button
        data-pet-assistant
        aria-label="打开妙喵"
        className="fixed bottom-5 right-5 z-40 flex h-12 w-12 items-center justify-center rounded-full border border-neutral-200 bg-white text-xl shadow-lg"
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
        <form onSubmit={submit} className="flex gap-2"><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask anything" className="min-w-0 flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400"/><Button type="submit" size="icon" disabled={pending}><MessageCircle className="h-4 w-4" /></Button></form>
      </div>
    </DialogContent>
  </Dialog>
}

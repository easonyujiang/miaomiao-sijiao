'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CatLottie } from '@/src/components/cat-lottie'
import { useMiaoSound } from '@/src/hooks/use-miao-sound'
import { useMobileVoice } from '@/src/hooks/use-mobile-voice'
import { usePetTts } from '@/src/hooks/use-pet-tts'
import { moodFor, type CatStateKey, type SpeechSegment } from '@/src/data/cat-states'
import {
  chatWithPet,
  createVisitorSession,
  loadLesson,
  submitQuiz,
  speechToText,
  type LessonInfo,
  type LessonStep,
  type QuizResult,
} from '@/src/lib/mobile-api'

function formatTime(ms: number) {
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function isDouyinWebView() {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent.toLowerCase()
  return ua.includes('aweme') || ua.includes('douyin') || ua.includes('tiktok')
}

type Message = {
  id: string
  role: 'user' | 'cat' | 'system'
  text: string
  seekToSec?: number
  segments?: SpeechSegment[]
}

export function MobilePetAssistant({ videoId, platform = 'douyin' }: { videoId?: string; platform?: string }) {
  const [open, setOpen] = useState(false)
  const [catState, setCatState] = useState<CatStateKey>('idle')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [lesson, setLesson] = useState<LessonInfo | null>(null)
  const [lessonLoading, setLessonLoading] = useState(false)
  const [lessonError, setLessonError] = useState<string | null>(null)
  const [lessonStarted, setLessonStarted] = useState(false)
  const [currentStep, setCurrentStep] = useState<LessonStep | null>(null)
  const [pendingStep, setPendingStep] = useState<LessonStep | null>(null)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())
  const [sessionId, setSessionId] = useState('')
  const [isDouyin, setIsDouyin] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sessionCreatingRef = useRef(false)
  const mountedRef = useRef(true)

  const { play, startThinking, stopThinking, muted, toggleMute } = useMiaoSound()
  const { speak, stop: stopTts, speaking } = usePetTts()
  const { recording, error: voiceError, isSupported, start: startVoice, stop: stopVoice } = useMobileVoice()

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      stopTts()
      if (recording) stopVoice()
    }
  }, [recording, stopTts, stopVoice])

  useEffect(() => {
    setIsDouyin(isDouyinWebView())
  }, [])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const addMessage = useCallback((role: Message['role'], text: string, meta?: Partial<Message>) => {
    setMessages((prev) => [...prev, { id: `${Date.now()}_${Math.random()}`, role, text, ...meta }])
  }, [])

  const setProtectedState = useCallback((state: CatStateKey) => {
    setCatState(state)
  }, [])

  const resetProtectedState = useCallback(() => {
    setCatState((s) => {
      if (['analyzing', 'celebrating', 'failed', 'levelup'].includes(s)) return s
      return 'idle'
    })
  }, [])

  const loadLessonData = useCallback(async () => {
    if (!videoId) return
    setLessonLoading(true)
    setLessonError(null)
    try {
      const data = await loadLesson(videoId, platform)
      if (!mountedRef.current) return
      if (data?.lesson_id) {
        setLesson(data)
        addMessage('system', `✨ 发现课程「${data.title}」，共 ${data.total_steps} 关。准备好了吗？`)
        setCatState('watching')
      } else {
        setLesson(null)
        addMessage('system', '未找到对应课程，可以直接向妙喵提问。')
      }
    } catch (e) {
      if (!mountedRef.current) return
      setLessonError('课程加载失败，请检查网络后重试')
      addMessage('system', '课程加载失败，请点击下方按钮重试。')
    } finally {
      if (mountedRef.current) setLessonLoading(false)
    }
  }, [addMessage, platform, videoId])

  useEffect(() => {
    if (!videoId) return
    setLesson(null)
    setLessonStarted(false)
    setCurrentStep(null)
    setPendingStep(null)
    setCompletedSteps(new Set())
    setMessages([])
    setCatState('idle')
    setLessonError(null)
    setSessionId('')
    sessionCreatingRef.current = false

    const ensureSession = async () => {
      if (sessionCreatingRef.current) return
      sessionCreatingRef.current = true
      const anonymousKey = `douyin_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
      const s = await createVisitorSession(anonymousKey)
      if (s?.session_id) {
        setSessionId(s.session_id)
      } else {
        // 离线/不可用时回退到本地 id，保证闯关状态不冲突
        setSessionId(`mobile_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`)
      }
    }

    void ensureSession()
    void loadLessonData()
  }, [loadLessonData, videoId])

  const handleChat = useCallback(async (text: string) => {
    if (!text.trim() || loading) return
    addMessage('user', text)
    setInput('')
    setLoading(true)
    setProtectedState('analyzing')
    startThinking()

    try {
      const res = await chatWithPet(text, { sessionId, videoId, platform })
      if (!mountedRef.current) return
      stopThinking()
      if (!res) throw new Error('请求失败')

      const seek = res.seek_to_sec ?? res.actions?.[0]?.time_ms
        ? Math.floor((res.actions[0].time_ms as number) / 1000)
        : undefined
      addMessage('cat', res.answer, { seekToSec: seek, segments: res.segments })
      setProtectedState(moodFor(res.answer))
      play('receive')
      setTimeout(resetProtectedState, 2500)
    } catch (e) {
      if (!mountedRef.current) return
      stopThinking()
      addMessage('cat', '喵呜…网络开小差了，请稍后再试。')
      setProtectedState('failed')
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [addMessage, loading, platform, resetProtectedState, sessionId, setProtectedState, startThinking, stopThinking, videoId, play])

  const startLesson = useCallback(() => {
    if (!lesson) return
    setLessonStarted(true)
    const first = lesson.steps[0]
    setCurrentStep(first)
    setProtectedState('watching')
    addMessage('cat', `📚 第 1 关：${first.title}\n\n${first.instruction}\n\n看到 ${formatTime(first.end_ms)} 后，妙喵会出题考你～`)
    play('meow')
  }, [addMessage, lesson, play, setProtectedState])

  const promptQuiz = useCallback((step: LessonStep) => {
    setPendingStep(step)
    addMessage('cat', `⏸️ 先暂停一下！\n\n📝 ${step.question}\n\n把答案发给我，支持口语化回答～`)
    setProtectedState('listening')
  }, [addMessage, setProtectedState])

  // 自动出题：如果当前步骤的 end_ms 接近，就出题
  // H5 内无法监听抖音视频进度，这里只在课程开始时提醒用户手动注意时间点
  // 当用户表示「准备好了/继续」时，可以调用 promptQuiz

  const submitAndShow = useCallback(async (answer: string, step: LessonStep) => {
    if (!lesson || loading) return
    setLoading(true)
    setProtectedState('analyzing')
    startThinking()

    const result = await submitQuiz(sessionId, lesson.lesson_id, step.id, answer)
    if (!mountedRef.current) return
    stopThinking()
    setLoading(false)

    if (!result) {
      addMessage('cat', '提交失败，请检查网络或后端服务。')
      setProtectedState('failed')
      return
    }

    if (result.passed) {
      setCompletedSteps((prev) => new Set([...prev, step.id]))
      const stars = result.stars_earned
      play(stars >= 3 ? 'perfect' : 'pass')
      setProtectedState('celebrating')
      addMessage('cat', result.cat_message)
      if (result.next_step) {
        setTimeout(() => {
          addMessage('cat', `🌟 太棒了！第 ${completedSteps.size + 1} 关完成，准备进入下一关。`)
          setCurrentStep(result.next_step as LessonStep)
          setPendingStep(null)
        }, 800)
      } else {
        setTimeout(() => {
          addMessage('cat', `🎉 全部通关！${lesson.title}你已掌握，小鱼干满满！`)
          setProtectedState('levelup')
          play('level-up')
        }, 800)
      }
    } else {
      play('fail')
      setProtectedState('failed')
      let text = result.cat_message
      if (result.seek_to_ms != null) {
        text += `\n\n⏪ 可跳回 ${formatTime(result.seek_to_ms)} 再看一遍`
      }
      addMessage('cat', text, { seekToSec: result.seek_to_ms })
      setPendingStep(null)
    }
  }, [addMessage, completedSteps.size, lesson, loading, play, sessionId, setProtectedState, startThinking, stopThinking])

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text) return
    if (pendingStep) {
      submitAndShow(text, pendingStep)
      setInput('')
      return
    }
    handleChat(text)
  }, [handleChat, input, pendingStep, submitAndShow])

  const handleVoiceRelease = useCallback(async () => {
    if (!recording) return
    const blob = await stopVoice()
    if (!blob) {
      addMessage('cat', '没有录到声音，请再试一次。')
      return
    }
    setLoading(true)
    addMessage('user', '🎤 识别中…')
    const text = await speechToText(blob)
    if (!mountedRef.current) {
      setLoading(false)
      return
    }
    // 移除 "识别中…" 临时消息
    setMessages((prev) => prev.filter((m) => m.text !== '🎤 识别中…'))
    setLoading(false)
    if (!text) {
      addMessage('cat', '语音没有识别到内容，请再说一遍。')
      return
    }
    addMessage('user', text)
    if (pendingStep) {
      submitAndShow(text, pendingStep)
    } else {
      handleChat(text)
    }
  }, [addMessage, handleChat, pendingStep, recording, stopVoice, submitAndShow])

  const quickActions = useMemo(() => {
    if (lessonError) {
      return [{ label: '🔄 重新加载课程', action: loadLessonData }]
    }
    if (lessonLoading) {
      return [{ label: '⏳ 加载中…', action: () => {} }]
    }
    if (pendingStep) {
      return [
        { label: '提交答案', action: () => handleSend() },
        { label: '给我提示', action: () => {
          if (currentStep?.hint_seek_ms != null) {
            addMessage('cat', `🔍 关键片段在 ${formatTime(currentStep.hint_seek_ms)}，可以回看。`)
          }
        }},
        { label: '自由问答', action: () => { setPendingStep(null); addMessage('cat', '已切换到自由问答，尽管提问吧。') } },
      ]
    }
    if (lesson && !lessonStarted) {
      return [{ label: '🚀 开始学习', action: startLesson }]
    }
    if (lessonStarted && currentStep) {
      const progress = `${completedSteps.size + 1}/${lesson?.total_steps ?? '?'}`
      return [
        { label: `📚 当前 ${progress}`, action: () => {} },
        { label: '准备答题', action: () => currentStep && promptQuiz(currentStep) },
        { label: '给我提示', action: () => {
          if (currentStep?.hint_seek_ms != null) {
            addMessage('cat', `🔍 关键片段在 ${formatTime(currentStep.hint_seek_ms)}，可以回看。`)
          }
        }},
        { label: '自由问答', action: () => { setPendingStep(null); addMessage('cat', '已切换到自由问答，尽管提问吧。') } },
      ]
    }
    return [
      { label: '讲解当前片段', action: () => handleChat('解释我当前在看的这段讲了什么') },
      { label: '出一道题', action: () => handleChat('针对这段内容给我出一道练习题') },
      { label: '跳到关键点', action: () => handleChat('找到最重要的知识点，告诉我跳回哪里重看') },
    ]
  }, [addMessage, completedSteps.size, currentStep, handleChat, handleSend, lesson, lessonError, lessonLoading, lessonStarted, loadLessonData, pendingStep, promptQuiz, startLesson])

  const handleSeek = useCallback((sec?: number) => {
    if (sec == null) return
    if (isDouyin) {
      addMessage('cat', `请手动拖动视频到 ${formatTime(sec * 1000)} 回看～`)
      return
    }
    addMessage('cat', `建议跳回到 ${formatTime(sec * 1000)} 回看。`)
  }, [addMessage, isDouyin])

  return (
    <div className="fixed bottom-4 right-4 z-50 font-sans text-sm">
      {/* 悬浮猫头像 */}
      {!open && (
        <button
          onClick={() => { setOpen(true); play('pop-open') }}
          className="flex h-16 w-16 items-center justify-center rounded-full bg-pink-50 shadow-lg border-2 border-pink-200 active:scale-95 transition"
        >
          <CatLottie state={catState} size={56} />
        </button>
      )}

      {/* 聊天面板 */}
      {open && (
        <div className="flex flex-col w-[90vw] max-w-[360px] h-[70vh] max-h-[520px] rounded-2xl border border-pink-200 bg-white/95 shadow-2xl overflow-hidden">
          {/* 头部 */}
          <div className="flex items-center gap-2 px-4 py-3 bg-pink-50 border-b border-pink-100">
            <CatLottie state={catState} size={36} />
            <span className="flex-1 font-semibold text-pink-900 truncate">妙喵私教</span>
            {isDouyin && <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-600">抖音内</span>}
            <button onClick={toggleMute} className="text-lg" title="静音">{muted ? '🔇' : '🔊'}</button>
            <button onClick={() => { setOpen(false); stopTts(); play('pop-close') }} className="text-lg">✕</button>
          </div>

          {/* 视频信息 */}
          <div className="px-4 py-2 text-xs text-gray-500 border-b border-pink-50 truncate">
            {videoId ? `📹 ${videoId}${lesson ? ` · ${lesson.title}` : ''}` : '未识别视频'}
          </div>

          {/* 消息区 */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 whitespace-pre-line ${
                  msg.role === 'user'
                    ? 'bg-pink-500 text-white rounded-br-none'
                    : msg.role === 'system'
                      ? 'bg-gray-100 text-gray-600 text-xs'
                      : 'bg-pink-50 text-pink-900 border border-pink-100 rounded-bl-none'
                }`}>
                  {msg.text}
                  {msg.role === 'cat' && msg.seekToSec != null && (
                    <button
                      onClick={() => handleSeek(msg.seekToSec)}
                      className="mt-1 block text-xs px-2 py-1 rounded-full bg-orange-100 text-orange-700"
                    >
                      ⏩ 跳到 {formatTime(msg.seekToSec * 1000)}
                    </button>
                  )}
                  {msg.role === 'cat' && (
                    <button
                      onClick={() => speak(msg.text)}
                      disabled={speaking}
                      className="mt-1 text-xs text-pink-500 disabled:opacity-50"
                    >
                      {speaking ? '朗读中…' : '🔊 朗读'}
                    </button>
                  )}
                </div>
              </div>
            ))}
            {lessonLoading && (
              <div className="flex items-center gap-2 text-pink-400 text-xs">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-pink-300 border-t-pink-500" />
                妙喵正在查找课程…
              </div>
            )}
            {lessonError && (
              <div className="rounded-xl bg-red-50 p-3 text-xs text-red-600">
                {lessonError}
                <button
                  onClick={loadLessonData}
                  className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-red-700"
                >
                  重试
                </button>
              </div>
            )}
            {loading && <div className="text-pink-400 text-xs">妙喵正在思考…</div>}
            <div ref={messagesEndRef} />
          </div>

          {/* 快捷按钮 */}
          <div className="px-3 py-2 flex gap-2 overflow-x-auto border-t border-pink-50">
            {quickActions.map((a, i) => (
              <button
                key={i}
                onClick={a.action}
                disabled={loading}
                className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs bg-white border border-pink-200 text-pink-600 active:bg-pink-50 disabled:opacity-50"
              >
                {a.label}
              </button>
            ))}
          </div>

          {/* 输入区 */}
          <div className="px-3 py-3 border-t border-pink-100 bg-white">
            {voiceError && <div className="text-xs text-red-500 mb-1">{voiceError}</div>}
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder={pendingStep ? '输入你的答案…' : '问妙喵…'}
                className="flex-1 rounded-full border border-pink-200 px-4 py-2 text-sm focus:outline-none focus:border-pink-400"
              />
              {isSupported && (
                <button
                  onMouseDown={startVoice}
                  onMouseUp={handleVoiceRelease}
                  onTouchStart={startVoice}
                  onTouchEnd={handleVoiceRelease}
                  className={`h-10 w-10 rounded-full flex items-center justify-center text-lg ${
                    recording ? 'bg-pink-500 text-white' : 'bg-pink-100 text-pink-600'
                  }`}
                >
                  {recording ? '⏹' : '🎤'}
                </button>
              )}
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="h-10 w-10 rounded-full bg-gradient-to-br from-pink-400 to-orange-300 text-white flex items-center justify-center disabled:opacity-50"
              >
                ➤
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

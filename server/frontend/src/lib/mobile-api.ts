import type { SpeechSegment } from '@/src/data/cat-states'

const DEFAULT_SLUG = process.env.NEXT_PUBLIC_SITE_SLUG || 'ashley'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || ''

export type AgentAction = {
  type: 'seek_video' | 'open_video' | 'open_section'
  video_id?: string
  time_ms?: number
  target?: string
  label: string
}

export type ChatResponse = {
  answer: string
  segments?: SpeechSegment[]
  expression: 'thinking' | 'excited'
  intent: string
  sources: Array<Record<string, unknown>>
  actions: AgentAction[]
  seek_to_sec?: number | null
}

export type LessonInfo = {
  lesson_id: string
  title: string
  video_id: string
  creator_name?: string
  total_steps: number
  steps: LessonStep[]
}

export type LessonStep = {
  id: string
  title: string
  start_ms: number
  end_ms: number
  instruction: string
  key_point: string
  common_errors: string[]
  question: string
  hint_seek_ms?: number
  pass_threshold?: number
}

export type QuizResult = {
  passed: boolean
  score: number
  cat_message: string
  seek_to_ms?: number
  stars_earned: number
  next_step?: LessonStep
  attempt_num: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: '请求失败' }))
    throw new Error(data.detail || `API ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function createVisitorSession(anonymousKey: string, slug = DEFAULT_SLUG) {
  try {
    return await request<{ session_id: string; visitor_id: string }>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({
        slug,
        anonymous_key: anonymousKey,
        source: 'douyin_h5',
        landing_path: '/douyin',
      }),
    })
  } catch {
    return null
  }
}

export function chatWithPet(
  message: string,
  context: { sessionId?: string; videoId?: string; currentTimeMs?: number; platform?: string },
  slug = DEFAULT_SLUG,
) {
  return request<ChatResponse>(`/api/site/${slug}/chat`, {
    method: 'POST',
    body: JSON.stringify({
      message,
      session_id: context.sessionId,
      video_id: context.videoId,
      current_time_ms: context.currentTimeMs ?? 0,
      platform: context.platform ?? 'douyin',
    }),
  })
}

export async function loadLesson(videoId: string, platform = 'douyin'): Promise<LessonInfo | null> {
  try {
    return await request<LessonInfo>('/api/lesson/load', {
      method: 'POST',
      body: JSON.stringify({ video_id: videoId, platform }),
    })
  } catch {
    return null
  }
}

export async function submitQuiz(
  sessionId: string,
  lessonId: string,
  stepId: string,
  answer: string,
  currentTimeSec = 0,
): Promise<QuizResult | null> {
  try {
    return await request<QuizResult>('/api/lesson/quiz_submit', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        lesson_id: lessonId,
        step_id: stepId,
        answer,
        current_time_sec: currentTimeSec,
      }),
    })
  } catch {
    return null
  }
}

export async function textToSpeech(text: string, voice?: string): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice }),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  } catch {
    return null
  }
}

export async function speechToText(audioBlob: Blob): Promise<string | null> {
  try {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    const res = await fetch(`${API_BASE}/api/speech-to-text`, {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) return null
    const data = await res.json()
    return data.text || null
  } catch {
    return null
  }
}

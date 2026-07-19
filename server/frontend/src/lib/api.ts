import type { SiteProfile, DiaryEntry } from '../data/siteProfile'
import type { SpeechSegment } from '@/src/data/cat-states'

const DEFAULT_SLUG = process.env.NEXT_PUBLIC_SITE_SLUG || 'ashley'

export type SiteSession = {
  session_id: string
  visitor_id: string
}

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
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json() as Promise<T>
}

export function fetchSite(slug = DEFAULT_SLUG) {
  return request<SiteProfile>(`/api/site/${slug}`)
}

export function fetchDiary(slug = DEFAULT_SLUG, limit = 30, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return request<{ items: DiaryEntry[] }>(`/api/site/${slug}/diary?${params.toString()}`)
}

export function fetchDiaryByDate(date: string, slug = DEFAULT_SLUG) {
  return request<DiaryEntry>(`/api/site/${slug}/diary/${date}`)
}

export function createSiteSession(anonymousKey: string, slug = DEFAULT_SLUG) {
  return request<SiteSession>('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({
      slug,
      anonymous_key: anonymousKey,
      source: document.referrer || 'direct',
      landing_path: window.location.pathname,
    }),
  })
}

export function chatWithPet(
  message: string,
  context: { sessionId?: string; videoId?: string; currentTimeMs?: number },
  slug = DEFAULT_SLUG,
) {
  return request<ChatResponse>(`/api/site/${slug}/chat`, {
    method: 'POST',
    body: JSON.stringify({
      message,
      session_id: context.sessionId,
      video_id: context.videoId,
      current_time_ms: context.currentTimeMs ?? 0,
    }),
  })
}

export function chatWithVoice(
  audioBlob: Blob,
  context: { sessionId?: string; videoId?: string; currentTimeMs?: number },
  slug = DEFAULT_SLUG,
) {
  const formData = new FormData()
  formData.append('audio', audioBlob, 'recording.webm')
  if (context.sessionId) formData.append('session_id', context.sessionId)
  if (context.videoId) formData.append('video_id', context.videoId)
  formData.append('current_time_ms', String(context.currentTimeMs ?? 0))

  return fetch(`/api/site/${slug}/voice-chat`, {
    method: 'POST',
    body: formData,
  }).then(async (response) => {
    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: '语音聊天服务不可用' }))
      throw new Error(data.detail || `API ${response.status}`)
    }
    return response.json() as Promise<ChatResponse>
  })
}

export function recordEvent(
  sessionId: string,
  event: { event_type: string; section_id?: string; target_id?: string; payload?: Record<string, unknown> },
) {
  return request<{ event_id: string }>(`/api/sessions/${sessionId}/events`, {
    method: 'POST',
    body: JSON.stringify(event),
  })
}

export function updateVideoProgress(videoId: string, visitorId: string, positionMs: number) {
  return request<{ success: boolean }>(`/api/videos/${videoId}/progress`, {
    method: 'PUT',
    body: JSON.stringify({ visitor_id: visitorId, position_ms: positionMs }),
  })
}

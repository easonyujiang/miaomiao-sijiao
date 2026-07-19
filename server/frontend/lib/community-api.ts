import { posts } from '@/lib/posts'
import type { ContentItem } from '@/lib/community-data'

const CATEGORY_MAP_TO_TYPE: Record<string, 'video' | 'question' | 'discussion' | 'share'> = {
  question: 'question',
  discussion: 'discussion',
  showcase: 'video',
  feedback: 'share',
  other: 'discussion',
}

const TYPE_ICONS: Record<string, string> = {
  video: '▶',
  question: '❓',
  discussion: '💬',
  share: '📤',
}

const THUMBNAIL_GRADIENTS: Record<string, string> = {
  question: 'from-rose-500 to-pink-600',
  discussion: 'from-sky-500 to-blue-600',
  showcase: 'from-emerald-500 to-teal-600',
  feedback: 'from-amber-500 to-orange-600',
  other: 'from-violet-500 to-purple-600',
}

export type ApiTopic = {
  id: string
  title: string
  content: string
  category: string
  author_name: string
  tags: string[]
  video_id: string | null
  view_count: number
  reply_count: number
  like_count: number
  is_pinned: boolean
  is_resolved: boolean
  created_at: string
  updated_at: string
}

export type ApiReply = {
  id: string
  topic_id: string
  parent_reply_id: string | null
  author_name: string
  content: string
  is_pet_reply: boolean
  like_count: number
  created_at: string
}

export type TopicDetail = {
  topic: ApiTopic
  replies: ApiReply[]
}

export type TopicListResponse = {
  items: ApiTopic[]
  total: number
  limit: number
  offset: number
}

function toInitials(name: string): string {
  return name.slice(0, 2).toUpperCase()
}

function formatDate(iso: string): string {
  return iso.slice(0, 10)
}

export function topicToContentItem(topic: ApiTopic) {
  const type = CATEGORY_MAP_TO_TYPE[topic.category] ?? 'discussion'
  return {
    id: topic.id,
    type,
    title: topic.title,
    description: topic.content,
    author: { name: topic.author_name, avatar: toInitials(topic.author_name) },
    thumbnailColor: THUMBNAIL_GRADIENTS[topic.category] ?? THUMBNAIL_GRADIENTS.other,
    category: topic.category,
    tags: topic.tags,
    createdAt: formatDate(topic.created_at),
    likes: topic.like_count,
    commentCount: topic.reply_count,
    icon: TYPE_ICONS[type] ?? '💬',
    videoId: topic.video_id ?? undefined,
  }
}

export function fetchBlogPostsAsContentItems(): ContentItem[] {
  return posts.map((post) => ({
    id: post.meta.slug,
    type: 'blog',
    title: post.meta.title,
    description: post.meta.summary,
    author: { name: '妙喵', avatar: '妙喵' },
    thumbnailColor: 'from-violet-500 to-purple-600',
    category: 'blog',
    tags: post.meta.tags,
    createdAt: post.meta.date,
    likes: 0,
    commentCount: 0,
    icon: '📄',
    source: 'blog',
    href: `/blog/${post.meta.slug}/`,
  }))
}

export function buildReplyTree(replies: ApiReply[]): Array<ApiReply & { replies: ApiReply[] }> {
  const map = new Map<string, ApiReply & { replies: ApiReply[] }>()
  const roots: Array<ApiReply & { replies: ApiReply[] }> = []

  for (const r of replies) {
    map.set(r.id, { ...r, replies: [] })
  }
  for (const r of replies) {
    const node = map.get(r.id)!
    if (r.parent_reply_id && map.has(r.parent_reply_id)) {
      map.get(r.parent_reply_id)!.replies.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
}

async function request<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`API ${res.status}`)
  return res.json() as Promise<T>
}

export function fetchTopics(category?: string, videoId?: string, limit = 50, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (category) params.set('category', category)
  if (videoId) params.set('video_id', videoId)
  return request<TopicListResponse>(`/api/community/topics?${params.toString()}`)
}

export function fetchTopicDetail(topicId: string) {
  return request<TopicDetail>(`/api/community/topics/${encodeURIComponent(topicId)}`)
}

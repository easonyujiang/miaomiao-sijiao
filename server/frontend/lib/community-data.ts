export type ContentItem = {
  id: string
  type: 'video' | 'question' | 'discussion' | 'share'
  title: string
  description: string
  author: { name: string; avatar: string }
  thumbnailColor: string
  category: string
  tags: string[]
  createdAt: string
  likes: number
  commentCount: number
  icon?: string
}

export type Comment = {
  id: string
  contentId: string
  parentId: string | null
  author: { name: string; avatar: string }
  content: string
  createdAt: string
  likes: number
  replies: Comment[]
}

export const CATEGORIES = [
  { key: '', label: '全部' },
  { key: 'question', label: '❓ 提问' },
  { key: 'discussion', label: '💬 讨论' },
  { key: 'showcase', label: '🎬 展示' },
  { key: 'feedback', label: '💡 反馈' },
]

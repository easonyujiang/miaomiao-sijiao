export type ContentItem = {
  id: string
  type: 'video' | 'question' | 'discussion' | 'share' | 'blog'
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
  videoId?: string
  source?: 'community' | 'blog'
  href?: string
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
  { key: 'all', label: '全部' },
  { key: 'blog', label: '文章' },
  { key: 'question', label: '问题' },
  { key: 'discussion', label: '讨论' },
  { key: 'video-linked', label: '视频关联' },
]

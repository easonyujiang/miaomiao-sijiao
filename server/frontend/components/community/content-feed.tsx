'use client'

import { useEffect, useState } from 'react'
import { CATEGORIES, type ContentItem } from '@/lib/community-data'
import { fetchTopics, topicToContentItem, fetchBlogPostsAsContentItems, type ApiTopic } from '@/lib/community-api'
import { ContentCard } from './content-card'

interface ContentFeedProps {
  onOpenDetail: (item: ContentItem, topicId: string) => void
  initialVideoId?: string | null
}

export function ContentFeed({ onOpenDetail, initialVideoId }: ContentFeedProps) {
  const [filter, setFilter] = useState(initialVideoId ? 'video-linked' : 'all')
  const [items, setItems] = useState<ContentItem[]>([])
  const [topicIds, setTopicIds] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)

    Promise.all([
      fetchTopics(undefined, initialVideoId || undefined, 50),
      Promise.resolve(fetchBlogPostsAsContentItems()),
    ])
      .then(([topicsRes, blogItems]) => {
        if (cancelled) return
        const communityItems = topicsRes.items.map(topicToContentItem)
        const idMap: Record<string, string> = {}
        topicsRes.items.forEach((t, i) => {
          idMap[communityItems[i].id] = t.id
        })
        const mixed = [...communityItems, ...blogItems].sort(
          (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        )
        setItems(mixed)
        setTopicIds(idMap)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))

    return () => { cancelled = true }
  }, [])

  const filtered = items.filter((item) => {
    if (filter === 'all') return true
    if (filter === 'blog') return item.type === 'blog'
    if (filter === 'question') return item.type === 'question'
    if (filter === 'discussion') return item.type === 'discussion'
    if (filter === 'video-linked') return !!item.videoId
    return true
  })

  return (
    <div>
      <div className="flex gap-1.5 mb-6 overflow-x-auto pb-1 scrollbar-hide">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setFilter(cat.key)}
            className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
              filter === cat.key
                ? 'bg-neutral-900 text-white'
                : 'bg-neutral-100 text-neutral-500 hover:bg-neutral-200'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="text-center py-12 text-neutral-400">
          <p className="text-sm">加载中…</p>
        </div>
      )}

      {error && !loading && (
        <div className="text-center py-12 text-neutral-400">
          <p className="text-4xl mb-3">🔌</p>
          <p className="text-sm">社区服务暂不可用</p>
          <p className="text-xs text-neutral-300 mt-1">请确认后端已启动</p>
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-3">
          {filtered.map((item) => (
            <ContentCard
              key={`${item.source}-${item.id}`}
              item={item}
              onOpen={() => {
                if (item.source === 'blog' && item.href) {
                  window.location.href = item.href
                } else {
                  onOpenDetail(item, topicIds[item.id] ?? item.id)
                }
              }}
            />
          ))}
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="text-center py-12 text-neutral-400">
          <p className="text-4xl mb-3">📭</p>
          <p className="text-sm">该分类暂无内容</p>
        </div>
      )}
    </div>
  )
}

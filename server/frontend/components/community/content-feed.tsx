'use client'

import { useEffect, useRef, useState } from 'react'
import { CATEGORIES, type ContentItem } from '@/lib/community-data'
import { fetchTopics, topicToContentItem, type ApiTopic } from '@/lib/community-api'
import { ContentCard } from './content-card'

interface ContentFeedProps {
  onOpenDetail: (item: ContentItem, topicId: string) => void
}

export function ContentFeed({ onOpenDetail }: ContentFeedProps) {
  const [activeCategory, setActiveCategory] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [items, setItems] = useState<ContentItem[]>([])
  const [topicIds, setTopicIds] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const cardRefs = useRef<Map<number, HTMLDivElement>>(new Map())

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    fetchTopics(activeCategory || undefined)
      .then((res) => {
        if (cancelled) return
        const mapped = res.items.map(topicToContentItem)
        const ids = res.items.map((t) => t.id)
        setItems(mapped)
        setTopicIds(ids)
        setSelectedIndex(0)
      })
      .catch(() => {
        if (cancelled) return
        setError(true)
        setItems([])
        setTopicIds([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [activeCategory])

  const filtered = items
  const safeIndex = Math.min(selectedIndex, Math.max(0, filtered.length - 1))

  useEffect(() => {
    const el = cardRefs.current.get(safeIndex)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [safeIndex])

  return (
    <div>
      {/* Category tabs */}
      <div className="flex gap-1.5 mb-6 overflow-x-auto pb-1 scrollbar-hide">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => {
              setActiveCategory(cat.key)
              setSelectedIndex(0)
            }}
            className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
              activeCategory === cat.key
                ? 'bg-neutral-900 text-white'
                : 'bg-neutral-100 text-neutral-500 hover:bg-neutral-200'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-12 text-neutral-400">
          <p className="text-sm">加载中…</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="text-center py-12 text-neutral-400">
          <p className="text-4xl mb-3">🔌</p>
          <p className="text-sm">社区服务暂不可用</p>
          <p className="text-xs text-neutral-300 mt-1">请确认后端已启动</p>
        </div>
      )}

      {/* Content cards */}
      {!loading && !error && (
        <div className="space-y-3">
          {filtered.map((item, index) => (
            <div
              key={item.id}
              ref={(el) => { if (el) cardRefs.current.set(index, el) }}
            >
              <ContentCard
                item={item}
                isSelected={index === safeIndex}
                onSelect={() => setSelectedIndex(index)}
                onOpen={() => onOpenDetail(item, topicIds[index])}
              />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && filtered.length === 0 && (
        <div className="text-center py-12 text-neutral-400">
          <p className="text-4xl mb-3">📭</p>
          <p className="text-sm">该分类暂无内容</p>
        </div>
      )}
    </div>
  )
}

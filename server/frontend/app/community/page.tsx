'use client'

import { useEffect, useState } from 'react'
import { AnimatePresence } from 'motion/react'
import { ContentFeed } from '@/components/community/content-feed'
import { ContentDetail } from '@/components/community/content-detail'
import { type ContentItem } from '@/lib/community-data'

export default function CommunityPage() {
  const [detailItem, setDetailItem] = useState<ContentItem | null>(null)
  const [detailTopicId, setDetailTopicId] = useState<string | null>(null)
  const [initialVideoId, setInitialVideoId] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setInitialVideoId(params.get('video_id'))
  }, [])

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">动态</h1>
        <p className="mt-1 text-sm text-neutral-500">
          {initialVideoId ? `与视频 ${initialVideoId} 相关的讨论` : '社区讨论与最新内容'}
        </p>
      </div>

      <AnimatePresence mode="wait">
        {detailItem && detailTopicId ? (
          <ContentDetail
            key="detail"
            item={detailItem}
            topicId={detailTopicId}
            onBack={() => { setDetailItem(null); setDetailTopicId(null) }}
          />
        ) : (
          <ContentFeed
            key="feed"
            initialVideoId={initialVideoId}
            onOpenDetail={(item, topicId) => {
              setDetailItem(item)
              setDetailTopicId(topicId)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

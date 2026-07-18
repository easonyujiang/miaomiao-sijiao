'use client'

import { useState } from 'react'
import { AnimatePresence } from 'motion/react'
import { ContentFeed } from '@/components/community/content-feed'
import { ContentDetail } from '@/components/community/content-detail'
import { type ContentItem } from '@/lib/community-data'

export default function CommunityPage() {
  const [detailItem, setDetailItem] = useState<ContentItem | null>(null)
  const [detailTopicId, setDetailTopicId] = useState<string | null>(null)

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">🎬 视频学习社区</h1>
        <p className="text-sm text-neutral-500">
          围绕视频内容的问答讨论，看完视频来提问、分享见解。
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
            onOpenDetail={(item, topicId) => { setDetailItem(item); setDetailTopicId(topicId) }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

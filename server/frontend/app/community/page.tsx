'use client'

import { useState } from 'react'
import { AnimatePresence } from 'motion/react'
import { ContentFeed } from '@/components/community/content-feed'
import { ContentDetail } from '@/components/community/content-detail'
import { type ContentItem } from '@/lib/community-data'

export default function CommunityPage() {
  const [detailItem, setDetailItem] = useState<ContentItem | null>(null)

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">🎬 视频学习社区</h1>
        <p className="text-sm text-neutral-500">
          围绕视频内容的问答讨论，看完视频来提问、分享见解。
          <span className="text-blue-500 ml-2">🎤 全程语音可控</span>
        </p>
      </div>

      {/* Feed or Detail */}
      <AnimatePresence mode="wait">
        {detailItem ? (
          <ContentDetail
            key="detail"
            item={detailItem}
            onBack={() => setDetailItem(null)}
          />
        ) : (
          <ContentFeed
            key="feed"
            onOpenDetail={(item) => setDetailItem(item)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

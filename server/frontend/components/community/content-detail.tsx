'use client'

import { useState } from 'react'
import { motion } from 'motion/react'
import { ArrowLeft, Heart, Eye, Share2, MessageCircle } from 'lucide-react'
import type { ContentItem } from '@/lib/community-data'
import { CommentSection } from './comment-section'

const typeLabels: Record<string, string> = {
  video: '视频',
  question: '提问',
  discussion: '讨论',
  share: '分享',
}

interface ContentDetailProps {
  item: ContentItem
  onBack: () => void
}

export function ContentDetail({ item, onBack }: ContentDetailProps) {
  const [showComments, setShowComments] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
    >
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-900 transition-colors mb-4"
      >
        <ArrowLeft className="h-4 w-4" />
        返回列表（或说「返回」）
      </button>

      {/* Hero area */}
      <div
        className={`w-full h-48 rounded-xl bg-gradient-to-br ${item.thumbnailColor} flex items-center justify-center mb-6`}
      >
        <span className="text-white/80 text-5xl font-bold">
          {item.type === 'video' ? '▶' : item.type === 'question' ? '❓' : item.type === 'discussion' ? '💬' : '📤'}
        </span>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-2 mb-3">
        <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] text-neutral-500">
          {typeLabels[item.type]}
        </span>
        <span className="text-[10px] text-neutral-400">{item.createdAt}</span>
        <span className="flex-1" />
        <button className="inline-flex items-center gap-1 text-[10px] text-neutral-400 hover:text-neutral-600">
          <Share2 className="h-3 w-3" />
          分享
        </button>
      </div>

      {/* Title */}
      <h1 className="text-xl font-bold text-neutral-900 mb-2">{item.title}</h1>

      {/* Author */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-800 text-[11px] font-semibold text-white">
          {item.author.avatar}
        </div>
        <span className="text-sm text-neutral-600">{item.author.name}</span>
      </div>

      {/* Content body */}
      <div className="prose prose-sm prose-neutral max-w-none mb-6">
        <p className="text-sm leading-7 text-neutral-600">{item.description}</p>
        {item.videoUrl && (
          <a
            href={item.videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 mt-3 rounded-lg bg-red-50 border border-red-100 px-3 py-2 text-xs text-red-600 hover:bg-red-100 transition-colors"
          >
            <span>▶</span>
            <span>观看相关视频 {item.bvid ? `(${item.bvid})` : ''}</span>
          </a>
        )}
        <p className="text-sm leading-7 text-neutral-600 mt-4">
          语音控制提示：说「<strong>返回</strong>」回到列表，说「<strong>打开评论</strong>」查看讨论。
        </p>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {item.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-full bg-neutral-100 px-2.5 py-1 text-[10px] text-neutral-500"
          >
            #{tag}
          </span>
        ))}
      </div>

      {/* Action bar */}
      <div className="flex items-center gap-4 py-3 border-t border-b border-neutral-100 mb-4">
        <button className="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-rose-500 transition-colors">
          <Heart className="h-4 w-4" />
          {item.likes} 赞
        </button>
        <button
          onClick={() => setShowComments(!showComments)}
          className={`inline-flex items-center gap-1.5 text-sm transition-colors ${
            showComments
              ? 'text-blue-600'
              : 'text-neutral-500 hover:text-blue-500'
          }`}
        >
          <MessageCircle className="h-4 w-4" />
          {item.commentCount} 评论
        </button>
        <button className="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-700 transition-colors">
          <Eye className="h-4 w-4" />
          浏览
        </button>
      </div>

      {/* Voice hint for comments */}
      {!showComments && (
        <button
          onClick={() => setShowComments(true)}
          className="w-full rounded-lg bg-blue-50 border border-blue-100 px-4 py-2.5 text-xs text-blue-600 hover:bg-blue-100 transition-colors mb-4"
        >
          💬 说「<strong>打开评论</strong>」或点击此处查看 {item.commentCount} 条评论
        </button>
      )}

      {/* Comment section */}
      <CommentSection
        contentId={item.id}
        commentCount={item.commentCount}
        visible={showComments}
        onClose={() => setShowComments(false)}
      />
    </motion.div>
  )
}

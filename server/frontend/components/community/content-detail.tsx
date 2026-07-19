'use client'

import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { ArrowLeft, Heart, Eye, Share2, MessageCircle } from 'lucide-react'
import type { ContentItem, Comment } from '@/lib/community-data'
import { fetchTopicDetail, buildReplyTree } from '@/lib/community-api'
import { CommentSection } from './comment-section'

const typeLabels: Record<string, string> = {
  video: '展示',
  question: '提问',
  discussion: '讨论',
  share: '反馈',
}

interface ContentDetailProps {
  item: ContentItem
  topicId: string
  onBack: () => void
}

export function ContentDetail({ item, topicId, onBack }: ContentDetailProps) {
  const [showComments, setShowComments] = useState(false)
  const [comments, setComments] = useState<Comment[]>([])
  const [viewCount, setViewCount] = useState(0)

  useEffect(() => {
    if (item.source === 'blog' && item.href) {
      window.location.href = item.href
    }
  }, [item])

  useEffect(() => {
    if (!showComments) return
    fetchTopicDetail(topicId)
      .then((data) => {
        setViewCount(data.topic.view_count)
        const tree = buildReplyTree(data.replies).map((r) => ({
          id: r.id,
          contentId: r.topic_id,
          parentId: r.parent_reply_id,
          author: { name: r.author_name, avatar: r.author_name.slice(0, 2).toUpperCase() },
          content: r.content,
          createdAt: r.created_at,
          likes: r.like_count,
          replies: r.replies.map((sub) => ({
            id: sub.id,
            contentId: sub.topic_id,
            parentId: sub.parent_reply_id,
            author: { name: sub.author_name, avatar: sub.author_name.slice(0, 2).toUpperCase() },
            content: sub.content,
            createdAt: sub.created_at,
            likes: sub.like_count,
            replies: [],
          })),
        }))
        setComments(tree)
      })
      .catch(() => {})
  }, [showComments, topicId])

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
    >
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-900 transition-colors mb-4"
      >
        <ArrowLeft className="h-4 w-4" />
        返回列表
      </button>

      <div className={`w-full h-48 rounded-xl bg-gradient-to-br ${item.thumbnailColor} flex items-center justify-center mb-6`}>
        <span className="text-white/80 text-5xl font-bold">{item.icon ?? '💬'}</span>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] text-neutral-500">
          {typeLabels[item.type] ?? item.type}
        </span>
        <span className="text-[10px] text-neutral-400">{item.createdAt}</span>
        <span className="flex-1" />
        <button className="inline-flex items-center gap-1 text-[10px] text-neutral-400 hover:text-neutral-600">
          <Share2 className="h-3 w-3" />
          分享
        </button>
      </div>

      <h1 className="text-xl font-bold text-neutral-900 mb-2">{item.title}</h1>

      <div className="flex items-center gap-2 mb-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-800 text-[11px] font-semibold text-white">
          {item.author.avatar}
        </div>
        <span className="text-sm text-neutral-600">{item.author.name}</span>
      </div>

      <div className="prose prose-sm prose-neutral max-w-none mb-6">
        <p className="text-sm leading-7 text-neutral-600">{item.description}</p>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-4">
        {item.tags.map((tag) => (
          <span key={tag} className="rounded-full bg-neutral-100 px-2.5 py-1 text-[10px] text-neutral-500">
            #{tag}
          </span>
        ))}
      </div>

      <div className="flex items-center gap-4 py-3 border-t border-b border-neutral-100 mb-4">
        <button className="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-rose-500 transition-colors">
          <Heart className="h-4 w-4" />
          {item.likes} 赞
        </button>
        <button
          onClick={() => setShowComments(!showComments)}
          className={`inline-flex items-center gap-1.5 text-sm transition-colors ${
            showComments ? 'text-blue-600' : 'text-neutral-500 hover:text-blue-500'
          }`}
        >
          <MessageCircle className="h-4 w-4" />
          {item.commentCount} 评论
        </button>
        <button className="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-700 transition-colors">
          <Eye className="h-4 w-4" />
          {viewCount || '—'} 浏览
        </button>
      </div>

      {!showComments && (
        <button
          onClick={() => setShowComments(true)}
          className="w-full rounded-lg bg-blue-50 border border-blue-100 px-4 py-2.5 text-xs text-blue-600 hover:bg-blue-100 transition-colors mb-4"
        >
          💬 查看 {item.commentCount} 条评论
        </button>
      )}

      <CommentSection
        comments={comments}
        commentCount={item.commentCount}
        visible={showComments}
        onClose={() => setShowComments(false)}
      />
    </motion.div>
  )
}

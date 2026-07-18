'use client'

import { useState } from 'react'
import { motion } from 'motion/react'
import { MessageCircle, ChevronUp } from 'lucide-react'
import type { Comment } from '@/lib/community-data'
import { CommentItem } from './comment-item'

interface CommentSectionProps {
  comments: Comment[]
  commentCount: number
  visible: boolean
  onClose: () => void
}

export function CommentSection({ comments, commentCount, visible, onClose }: CommentSectionProps) {
  const [allExpanded, setAllExpanded] = useState(false)

  if (!visible) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="border-t border-neutral-200 pt-4"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <MessageCircle className="h-4 w-4 text-neutral-500" />
          <span className="text-sm font-semibold text-neutral-700">
            评论 ({commentCount})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAllExpanded(!allExpanded)}
            className="text-[10px] text-blue-500 hover:text-blue-600 transition-colors"
          >
            {allExpanded ? '收起全部回复' : '展开全部回复'}
          </button>
          <button
            onClick={onClose}
            className="flex items-center gap-1 text-[10px] text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            <ChevronUp className="h-3 w-3" />
            收起评论
          </button>
        </div>
      </div>

      <div className="divide-y divide-neutral-100">
        {comments.map((comment) => (
          <CommentItem key={comment.id} comment={comment} allExpanded={allExpanded} />
        ))}
      </div>

      {comments.length === 0 && (
        <p className="text-center text-sm text-neutral-400 py-6">暂无评论，来说两句吧</p>
      )}
    </motion.div>
  )
}

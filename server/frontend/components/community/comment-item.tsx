'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { ChevronDown, ChevronRight, Heart, MessageCircle } from 'lucide-react'
import type { Comment } from '@/lib/community-data'

interface CommentItemProps {
  comment: Comment
  depth?: number
  allExpanded: boolean
}

export function CommentItem({ comment, depth = 0, allExpanded }: CommentItemProps) {
  const [expanded, setExpanded] = useState(false)
  const hasReplies = comment.replies.length > 0
  const isExpanded = expanded || allExpanded

  return (
    <div className={`${depth > 0 ? 'ml-6 border-l-2 border-neutral-100 pl-4' : ''}`}>
      <div className="py-3">
        {/* Author header */}
        <div className="flex items-center gap-2 mb-1.5">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-200 text-[10px] font-semibold text-neutral-600">
            {comment.author.avatar}
          </div>
          <span className="text-xs font-medium text-neutral-700">
            {comment.author.name}
          </span>
          <span className="text-[10px] text-neutral-400">{comment.createdAt}</span>
        </div>

        {/* Content */}
        <p className="text-sm text-neutral-600 leading-relaxed">
          {comment.content}
        </p>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-1.5">
          <button className="inline-flex items-center gap-1 text-[10px] text-neutral-400 hover:text-rose-500 transition-colors">
            <Heart className="h-3 w-3" />
            {comment.likes}
          </button>
          <button className="inline-flex items-center gap-1 text-[10px] text-neutral-400 hover:text-blue-500 transition-colors">
            <MessageCircle className="h-3 w-3" />
            回复
          </button>
          {hasReplies && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="inline-flex items-center gap-1 text-[10px] text-blue-500 hover:text-blue-600 transition-colors"
            >
              {isExpanded ? (
                <>
                  <ChevronDown className="h-3 w-3" />
                  收起回复
                </>
              ) : (
                <>
                  <ChevronRight className="h-3 w-3" />
                  {comment.replies.length} 条回复
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Nested replies */}
      <AnimatePresence>
        {isExpanded && hasReplies && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            {comment.replies.map((reply) => (
              <CommentItem
                key={reply.id}
                comment={reply}
                depth={depth + 1}
                allExpanded={allExpanded}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

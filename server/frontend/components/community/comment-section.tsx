'use client'

import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { MessageCircle, ChevronUp } from 'lucide-react'
import { useVoice } from '@/context/voice-context'
import { buildCommentCommands } from '@/lib/voice-commands'
import { getCommentsForContent, type Comment } from '@/lib/community-data'
import { CommentItem } from './comment-item'

interface CommentSectionProps {
  contentId: string
  commentCount: number
  visible: boolean
  onClose: () => void
}

export function CommentSection({
  contentId,
  commentCount,
  visible,
  onClose,
}: CommentSectionProps) {
  const { registerCommands } = useVoice()
  const [allExpanded, setAllExpanded] = useState(false)
  const [comments, setComments] = useState<Comment[]>([])

  useEffect(() => {
    setComments(getCommentsForContent(contentId))
  }, [contentId])

  // Register comment voice commands
  useEffect(() => {
    if (!visible) return
    const cmds = buildCommentCommands(
      () => {}, // "open" — already open
      onClose,
      () => setAllExpanded(true),
      () => setAllExpanded(false),
    )
    const unregister = registerCommands(cmds)
    return unregister
  }, [visible, onClose, registerCommands])

  if (!visible) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="border-t border-neutral-200 pt-4"
    >
      {/* Header */}
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
            收起评论（或说「返回」）
          </button>
        </div>
      </div>

      {/* Comment list */}
      <div className="divide-y divide-neutral-100">
        {comments.map((comment) => (
          <CommentItem
            key={comment.id}
            comment={comment}
            allExpanded={allExpanded}
          />
        ))}
      </div>
    </motion.div>
  )
}

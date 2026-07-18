'use client'

import { motion } from 'motion/react'
import { Play, HelpCircle, MessageSquare, Share2, Heart, MessageCircle } from 'lucide-react'
import type { ContentItem } from '@/lib/community-data'

const typeIcons: Record<string, React.ReactNode> = {
  video: <Play className="h-3.5 w-3.5" />,
  question: <HelpCircle className="h-3.5 w-3.5" />,
  discussion: <MessageSquare className="h-3.5 w-3.5" />,
  share: <Share2 className="h-3.5 w-3.5" />,
}

const typeLabels: Record<string, string> = {
  video: '视频',
  question: '提问',
  discussion: '讨论',
  share: '分享',
}

interface ContentCardProps {
  item: ContentItem
  isSelected: boolean
  onSelect: () => void
  onOpen: () => void
}

export function ContentCard({ item, isSelected, onSelect, onOpen }: ContentCardProps) {
  return (
    <motion.div
      layout
      onClick={onSelect}
      onDoubleClick={onOpen}
      animate={
        isSelected
          ? {
              borderColor: 'rgb(147 197 253)',
              boxShadow: '0 0 0 2px rgba(59, 130, 246, 0.15)',
            }
          : {
              borderColor: 'rgb(229 229 229)',
              boxShadow: '0 0 0 0px rgba(59, 130, 246, 0)',
            }
      }
      transition={{ duration: 0.25 }}
      className="cursor-pointer rounded-xl border bg-white p-4 hover:border-neutral-300 transition-colors"
      role="button"
      tabIndex={0}
      aria-selected={isSelected}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onOpen()
      }}
    >
      <div className="flex gap-4">
        {/* Thumbnail */}
        <div
          className={`h-20 w-28 shrink-0 rounded-lg bg-gradient-to-br ${item.thumbnailColor} flex items-center justify-center`}
        >
          <span className="text-white/80 text-2xl font-bold">
            {item.type === 'video' ? '▶' : item.type === 'question' ? '❓' : item.type === 'discussion' ? '💬' : '📤'}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Type badge */}
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] text-neutral-500">
              {typeIcons[item.type]}
              {typeLabels[item.type]}
            </span>
            {item.videoId && (
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] text-blue-500">
                🔗 视频讨论
              </span>
            )}
            <span className="text-[10px] text-neutral-400">{item.createdAt}</span>
          </div>

          {/* Title */}
          <h3 className="font-semibold text-sm text-neutral-900 truncate">
            {item.title}
          </h3>

          {/* Description */}
          <p className="text-xs text-neutral-500 mt-1 line-clamp-2 leading-relaxed">
            {item.description}
          </p>

          {/* Tags + Meta */}
          <div className="flex items-center gap-2 mt-2">
            {item.tags.slice(0, 2).map((tag) => (
              <span
                key={tag}
                className="text-[10px] text-neutral-400 bg-neutral-50 px-1.5 py-0.5 rounded"
              >
                #{tag}
              </span>
            ))}
            <span className="flex-1" />
            <span className="inline-flex items-center gap-1 text-[10px] text-neutral-400">
              <Heart className="h-3 w-3" />
              {item.likes}
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] text-neutral-400">
              <MessageCircle className="h-3 w-3" />
              {item.commentCount}
            </span>
          </div>
        </div>
      </div>

      {/* Open button — visible when selected */}
      {isSelected && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-3 pt-3 border-t border-neutral-100"
        >
          <button
            onClick={(e) => {
              e.stopPropagation()
              onOpen()
            }}
            className="w-full rounded-lg bg-blue-50 py-2 text-xs font-medium text-blue-600 hover:bg-blue-100 transition-colors"
          >
            查看详情 →
          </button>
        </motion.div>
      )}
    </motion.div>
  )
}

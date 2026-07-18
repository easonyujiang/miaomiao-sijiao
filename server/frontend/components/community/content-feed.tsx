'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { motion } from 'motion/react'
import { useVoice } from '@/context/voice-context'
import { buildContentCommands } from '@/lib/voice-commands'
import { CATEGORIES, MOCK_CONTENT, type ContentItem } from '@/lib/community-data'
import { ContentCard } from './content-card'

interface ContentFeedProps {
  onOpenDetail: (item: ContentItem) => void
}

export function ContentFeed({ onOpenDetail }: ContentFeedProps) {
  const { registerCommands } = useVoice()
  const [activeCategory, setActiveCategory] = useState('all')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const cardRefs = useRef<Map<number, HTMLDivElement>>(new Map())

  // Filter content by category
  const filtered =
    activeCategory === 'all'
      ? MOCK_CONTENT
      : MOCK_CONTENT.filter((item) => item.category === activeCategory)

  // Keep selectedIndex in bounds when filter changes
  const safeIndex = Math.min(selectedIndex, Math.max(0, filtered.length - 1))

  // Scroll selected card into view
  useEffect(() => {
    const el = cardRefs.current.get(safeIndex)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [safeIndex])

  // Voice commands for content navigation
  const handleNext = useCallback(() => {
    setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1))
  }, [filtered.length])

  const handlePrev = useCallback(() => {
    setSelectedIndex((prev) => Math.max(prev - 1, 0))
  }, [])

  const handleOpen = useCallback(() => {
    if (filtered[safeIndex]) {
      onOpenDetail(filtered[safeIndex])
    }
  }, [filtered, safeIndex, onOpenDetail])

  const handleBack = useCallback(() => {
    // No-op in feed view
  }, [])

  useEffect(() => {
    const cmds = buildContentCommands(
      handleNext,
      handlePrev,
      handleOpen,
      handleBack,
    )
    const unregister = registerCommands(cmds)
    return unregister
  }, [registerCommands, handleNext, handlePrev, handleOpen, handleBack])

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

      {/* Voice hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mb-4 flex items-center gap-2 rounded-lg bg-blue-50 border border-blue-100 px-3 py-2 text-[11px] text-blue-600"
      >
        <span>🎤</span>
        <span>
          说「<strong>下一条</strong>」或「<strong>上一条</strong>」选择内容，说「<strong>打开</strong>」查看详情
        </span>
      </motion.div>

      {/* Content cards */}
      <div className="space-y-3">
        {filtered.map((item, index) => (
          <div
            key={item.id}
            ref={(el) => {
              if (el) cardRefs.current.set(index, el)
            }}
          >
            <ContentCard
              item={item}
              isSelected={index === safeIndex}
              onSelect={() => setSelectedIndex(index)}
              onOpen={() => onOpenDetail(item)}
            />
          </div>
        ))}
      </div>

      {/* Empty state */}
      {filtered.length === 0 && (
        <div className="text-center py-12 text-neutral-400">
          <p className="text-4xl mb-3">📭</p>
          <p className="text-sm">该分类暂无内容</p>
        </div>
      )}
    </div>
  )
}

'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { MobilePetAssistant } from '@/src/components/mobile-pet-assistant'

function DouyinContent() {
  const searchParams = useSearchParams()
  const videoId = searchParams.get('video_id') || undefined
  const platform = searchParams.get('platform') || 'douyin'

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 to-orange-50 p-6">
      <div className="mx-auto max-w-md rounded-2xl bg-white/80 p-6 shadow-xl border border-pink-100">
        <h1 className="text-xl font-bold text-pink-900 mb-2">妙喵私教 · 移动学习页</h1>
        <p className="text-sm text-gray-600 mb-4">
          {videoId
            ? `当前视频：${videoId}（平台：${platform}）`
            : '未传入视频 ID。请在抖音视频描述/评论中点击专属链接打开。'}
        </p>

        {!videoId && (
          <div className="rounded-lg bg-orange-50 p-4 text-sm text-orange-800">
            <p className="font-medium mb-1">测试链接示例：</p>
            <code className="block break-all text-xs">
              http://localhost:3000/douyin/?video_id=BV1mJ4m147PG&platform=bilibili
            </code>
          </div>
        )}
      </div>

      {videoId && <MobilePetAssistant videoId={videoId} platform={platform} />}
    </div>
  )
}

export default function DouyinPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center text-pink-500">加载中…</div>
    }>
      <DouyinContent />
    </Suspense>
  )
}

import type { Metadata } from 'next'
import { getSite } from '@/lib/site'

export const metadata: Metadata = {
  title: 'Community · 共创社区',
  description: '围绕博主内容的讨论社区——问答、分享、反馈。',
}

export default async function CommunityPage() {
  const profile = await getSite()
  const apiOrigin = process.env.API_BASE_URL || ''

  let topics: Array<Record<string, unknown>> = []
  if (apiOrigin) {
    try {
      const res = await fetch(`${apiOrigin}/api/community/topics?limit=20`, {
        next: { revalidate: 60 },
      })
      if (res.ok) {
        const data = await res.json()
        topics = data.items || []
      }
    } catch {
      // API 不可用，显示空状态
    }
  }

  return (
    <main className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold mb-2">💬 共创社区</h1>
      <p className="text-gray-500 mb-8">
        围绕 {profile.identity.name} 的内容讨论、提问、分享和反馈。妙喵也会参与话题哦~
      </p>

      <div className="mb-8 p-6 bg-amber-50 border border-amber-200 rounded-xl text-center">
        <p className="text-amber-800 text-lg mb-2">🚧 社区功能即将上线</p>
        <p className="text-amber-600 text-sm">
          话题发布、回复讨论、宠物参与等功能正在建设中。
          目前可通过管理后台手动管理话题和回复。
        </p>
      </div>

      {topics.length > 0 ? (
        <div className="space-y-4">
          {topics.map((topic: Record<string, unknown>) => (
            <div
              key={topic.id as string}
              className="p-4 bg-white border border-gray-200 rounded-lg hover:border-amber-300 transition-colors"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">
                  {topic.category as string}
                </span>
                <span className="text-xs text-gray-400">{topic.created_at as string}</span>
              </div>
              <h3 className="font-semibold mb-1">{topic.title as string}</h3>
              <p className="text-sm text-gray-600 line-clamp-2">{topic.content as string}</p>
              <div className="flex gap-4 mt-2 text-xs text-gray-400">
                <span>👤 {topic.author_name as string}</span>
                <span>💬 {topic.reply_count as number} 回复</span>
                <span>👁 {topic.view_count as number} 浏览</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-400">
          <p className="text-4xl mb-4">💬</p>
          <p>还没有话题，敬请期待~</p>
        </div>
      )}
    </main>
  )
}

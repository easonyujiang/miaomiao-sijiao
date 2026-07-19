import Link from 'next/link'
import { getSite } from '@/lib/site'
import { posts } from '@/lib/posts'

async function getAllTopics() {
  try {
    const res = await fetch(`${process.env.EWA_PUBLIC_URL || 'http://localhost:8000'}/api/community/topics?limit=50`, { next: { revalidate: 60 } })
    if (!res.ok) return []
    const data = await res.json()
    return data.items ?? []
  } catch {
    return []
  }
}

type FeedItem = {
  id: string
  type: 'blog' | 'community'
  title: string
  summary: string
  date: string
  href: string
  category?: string
  replyCount?: number
}

export default async function HomePage() {
  const profile = await getSite()
  const topics = await getAllTopics()

  const blogItems: FeedItem[] = posts.map((post) => ({
    id: post.meta.slug,
    type: 'blog',
    title: post.meta.title,
    summary: post.meta.summary,
    date: post.meta.date,
    href: `/blog/${post.meta.slug}`,
  }))

  const communityItems: FeedItem[] = topics.map((t: { id: string; title: string; content: string; category: string; created_at: string; reply_count: number }) => ({
    id: t.id,
    type: 'community',
    title: t.title,
    summary: t.content,
    date: t.created_at.slice(0, 10),
    href: '/community',
    category: t.category,
    replyCount: t.reply_count,
  }))

  const feed = [...communityItems, ...blogItems].sort((a, b) => b.date.localeCompare(a.date))

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">动态</h1>
        <p className="mt-1 text-sm text-neutral-500">社区讨论与最新内容</p>
      </div>

      <div className="flex gap-2 mb-6">
        <Link href="/community" className="rounded-full bg-neutral-900 px-4 py-1.5 text-xs font-medium text-white">
          全部
        </Link>
        <Link href="/blog" className="rounded-full bg-neutral-100 px-4 py-1.5 text-xs text-neutral-600 hover:bg-neutral-200">
          文章
        </Link>
        <Link href="/projects" className="rounded-full bg-neutral-100 px-4 py-1.5 text-xs text-neutral-600 hover:bg-neutral-200">
          项目
        </Link>
      </div>

      {feed.length === 0 ? (
        <p className="text-neutral-400 text-sm py-10 text-center">暂无内容</p>
      ) : (
        <div className="space-y-3">
          {feed.map((item) => (
            <Link
              key={`${item.type}-${item.id}`}
              href={item.href}
              className="block rounded-lg border border-neutral-200 bg-white p-4 hover:border-neutral-300 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1.5">
                    {item.type === 'blog' ? (
                      <span className="shrink-0 rounded bg-violet-50 px-1.5 py-0.5 text-[10px] font-medium text-violet-600">文章</span>
                    ) : (
                      <span className="shrink-0 rounded bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-600">讨论</span>
                    )}
                    {item.category && item.type === 'community' && (
                      <span className="text-[11px] text-neutral-400">{item.category}</span>
                    )}
                  </div>
                  <h3 className="font-medium text-sm leading-snug line-clamp-2">{item.title}</h3>
                  <p className="mt-1.5 text-xs leading-5 text-neutral-500 line-clamp-2">{item.summary}</p>
                </div>
                <div className="shrink-0 text-right">
                  <time className="text-[11px] text-neutral-400">{item.date}</time>
                  {item.replyCount !== undefined && item.replyCount > 0 && (
                    <p className="mt-1 text-[11px] text-neutral-400">{item.replyCount} 回复</p>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

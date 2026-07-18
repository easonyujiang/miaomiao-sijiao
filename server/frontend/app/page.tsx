import Link from 'next/link'
import { BlurFade } from '@/components/magicui/blur-fade'
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
  extra?: string
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
    extra: `${t.category} · ${t.reply_count} 条回复`,
  }))

  const feed = [...blogItems, ...communityItems].sort((a, b) => b.date.localeCompare(a.date))

  const typeBadge = (type: string) => {
    if (type === 'blog') return <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[10px] text-violet-500">文章</span>
    return <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] text-sky-500">讨论</span>
  }

  return (
    <>
      <BlurFade>
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-neutral-900 text-xl font-semibold text-white">{profile.identity.initials}</div>
        <h1 className="mt-8 text-3xl font-semibold tracking-tight sm:text-4xl">Hey, I&apos;m {profile.identity.name}.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-neutral-600">{profile.identity.summary}</p>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-neutral-600">这里是她的端点验证：让一只叫妙喵的小猫，把视频、文字和记忆连起来——能回答、能带路、也能记住每一位访客来过。</p>
        <div className="mt-6 flex flex-wrap gap-2">{profile.identity.tags.map((tag) => <span key={tag} className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600">{tag}</span>)}</div>
      </BlurFade>

      <section className="mt-20">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xl font-semibold tracking-tight">动态</h2>
          <Link href="/community" className="text-sm text-neutral-500 hover:text-neutral-950">去社区 →</Link>
        </div>
        {feed.length === 0 ? (
          <p className="text-neutral-400 text-sm">暂无内容</p>
        ) : (
          <div>{feed.map((item) => (
            <Link key={`${item.type}-${item.id}`} href={item.href} className="group grid gap-1 border-b border-neutral-200 py-5 sm:grid-cols-[120px_1fr]">
              <div className="flex flex-col gap-1">
                <time className="text-sm text-neutral-400">{item.date}</time>
                {typeBadge(item.type)}
              </div>
              <div>
                <h3 className="font-medium group-hover:underline">{item.title}</h3>
                <p className="mt-1 text-sm leading-6 text-neutral-500 line-clamp-2">{item.summary}</p>
                {item.extra && <p className="mt-1 text-xs text-neutral-400">{item.extra}</p>}
              </div>
            </Link>
          ))}</div>
        )}
      </section>
    </>
  )
}

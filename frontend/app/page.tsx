import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { BlurFade } from '@/components/magicui/blur-fade'
import { getSite } from '@/lib/site'
import { posts } from '@/lib/posts'
import { formatDate } from '@/components/diary-card'

export default async function HomePage() {
  const profile = await getSite()
  const recentDiary = (profile.diary ?? []).slice(0, 3)
  return <>
    <BlurFade>
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-neutral-900 text-xl font-semibold text-white">{profile.identity.initials}</div>
      <h1 className="mt-8 text-3xl font-semibold tracking-tight sm:text-4xl">Hey, I’m {profile.identity.name}.</h1>
      <p className="mt-5 max-w-2xl text-lg leading-8 text-neutral-600">{profile.identity.summary}</p>
      <p className="mt-4 max-w-2xl text-lg leading-8 text-neutral-600">这里是她的端点验证：让一只叫妙喵的小猫，把视频、文字和记忆连起来——能回答、能带路、也能记住每一位访客来过。</p>
      <div className="mt-6 flex flex-wrap gap-2">{profile.identity.tags.map((tag) => <span key={tag} className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600">{tag}</span>)}</div>
    </BlurFade>

    {recentDiary.length > 0 && (
      <section className="mt-20">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold tracking-tight">最近在做什么</h2>
          <Link href="/diary" className="text-sm text-neutral-500 hover:text-neutral-950">查看日记 →</Link>
        </div>
        <div className="grid gap-3">
          {recentDiary.map((entry, index) => (
            <BlurFade key={entry.id} delay={0.06 * (index + 1)}>
              <Link href="/diary" className="group grid gap-1 border-b border-neutral-200 py-4 sm:grid-cols-[140px_1fr]">
                <time className="text-sm text-neutral-400" dateTime={entry.date}>{formatDate(entry.date)}</time>
                <div>
                  <h3 className="font-medium tracking-tight group-hover:underline">{entry.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-neutral-500">{entry.summary}</p>
                </div>
              </Link>
            </BlurFade>
          ))}
        </div>
      </section>
    )}

    <section className="mt-20">
      <div className="mb-6 flex items-center justify-between"><h2 className="text-xl font-semibold tracking-tight">Selected work</h2><Link href="/projects" className="text-sm text-neutral-500 hover:text-neutral-950">View all →</Link></div>
      <div className="grid gap-4 sm:grid-cols-2">{profile.projects.slice(0, 2).map((project, index) => <BlurFade key={project.id} delay={0.08 * (index + 1)}><Link href="/projects" className="group block rounded-xl border border-neutral-200 bg-white p-5 transition hover:border-neutral-300 hover:shadow-sm"><div className="flex items-center justify-between"><span className="text-xs text-neutral-400">{project.stage}</span><ArrowUpRight className="h-4 w-4 text-neutral-300 transition group-hover:text-neutral-700" /></div><h3 className="mt-8 font-semibold tracking-tight">{project.name}</h3><p className="mt-2 text-sm leading-6 text-neutral-500">{project.summary}</p></Link></BlurFade>)}</div>
    </section>

    <section className="mt-20">
      <div className="mb-2 flex items-center justify-between"><h2 className="text-xl font-semibold tracking-tight">Recent writing</h2><Link href="/blog" className="text-sm text-neutral-500 hover:text-neutral-950">All posts →</Link></div>
      <div>{posts.map((post) => <Link key={post.meta.slug} href={`/blog/${post.meta.slug}`} className="group grid gap-1 border-b border-neutral-200 py-5 sm:grid-cols-[120px_1fr]"><time className="text-sm text-neutral-400">{post.meta.date}</time><div><h3 className="font-medium group-hover:underline">{post.meta.title}</h3><p className="mt-1 text-sm leading-6 text-neutral-500">{post.meta.summary}</p></div></Link>)}</div>
    </section>
  </>
}

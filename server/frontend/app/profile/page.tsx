import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { BlurFade } from '@/components/magicui/blur-fade'
import { getSite } from '@/lib/site'
import { DiaryCard } from '@/components/diary-card'
import { PrintButton } from '@/components/print-button'

export const metadata: Metadata = {
  title: 'Profile',
  description: '个人主页——日记、项目与简历。',
}

export default async function ProfilePage() {
  const profile = await getSite()
  const diary = profile.diary ?? []
  const pinned = diary.filter((d) => d.pinned)
  const rest = diary.filter((d) => !d.pinned)

  return (
    <>
      <BlurFade>
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-neutral-900 text-xl font-semibold text-white">{profile.identity.initials}</div>
        <h1 className="mt-8 text-3xl font-semibold tracking-tight sm:text-4xl">{profile.identity.name}</h1>
        <p className="mt-3 text-neutral-500">{profile.identity.role}</p>
        <p className="mt-1 text-sm text-neutral-400">{profile.identity.location} · {profile.identity.status}</p>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-neutral-600">{profile.identity.summary}</p>
        <div className="mt-6 flex flex-wrap gap-2">{profile.identity.tags.map((tag) => <span key={tag} className="rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600">{tag}</span>)}</div>
        <div className="mt-6 flex flex-wrap gap-3">
          {profile.links.filter((l) => l.visibility === 'public').map((link) => (
            <a key={link.label} href={link.href} target="_blank" rel="noopener noreferrer" className="text-sm text-neutral-500 hover:text-neutral-950 transition">{link.label} →</a>
          ))}
        </div>
      </BlurFade>

      <section className="mt-20">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold tracking-tight">Selected work</h2>
          <Link href="/projects" className="text-sm text-neutral-500 hover:text-neutral-950">View all →</Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {profile.projects.filter((p) => p.featured).slice(0, 4).map((project, index) => (
            <BlurFade key={project.id} delay={0.08 * (index + 1)}>
              <Link href="/projects" className="group block rounded-xl border border-neutral-200 bg-white p-5 transition hover:border-neutral-300 hover:shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-neutral-400">{project.stage}</span>
                  <ArrowUpRight className="h-4 w-4 text-neutral-300 transition group-hover:text-neutral-700" />
                </div>
                <h3 className="mt-8 font-semibold tracking-tight">{project.name}</h3>
                <p className="mt-2 text-sm leading-6 text-neutral-500">{project.summary}</p>
              </Link>
            </BlurFade>
          ))}
        </div>
      </section>

      {pinned.length > 0 && (
        <section className="mt-20">
          <h2 className="mb-4 text-xs font-medium uppercase tracking-wide text-neutral-400">当前重点</h2>
          <div className="grid gap-4">
            {pinned.map((entry, index) => (
              <BlurFade key={entry.id} delay={0.08 * (index + 1)}>
                <DiaryCard entry={entry} />
              </BlurFade>
            ))}
          </div>
        </section>
      )}

      <section className="mt-12">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xs font-medium uppercase tracking-wide text-neutral-400">最近</h2>
          <Link href="/diary" className="text-sm text-neutral-500 hover:text-neutral-950">查看全部 →</Link>
        </div>
        {rest.length === 0 ? (
          <p className="text-neutral-400">暂无日记。</p>
        ) : (
          <div className="grid gap-4">
            {rest.slice(0, 3).map((entry, index) => (
              <BlurFade key={entry.id} delay={0.04 * (index + 1)}>
                <DiaryCard entry={entry} />
              </BlurFade>
            ))}
          </div>
        )}
      </section>

      <section className="mt-20">
        <div className="flex items-end justify-between gap-4">
          <h2 className="text-xl font-semibold tracking-tight">Resume</h2>
          <PrintButton />
        </div>
        <section className="mt-8">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400">Current</h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-[140px_1fr]">
            <span className="text-sm text-neutral-400">2026 — Now</span>
            <div>
              <h3 className="font-medium">妙喵 · Creator Video Agent</h3>
              <p className="mt-2 leading-7 text-neutral-500">{profile.product.finalGoal}</p>
              <p className="mt-1 text-sm text-neutral-400">验证端点：先用我的个人网站、资料和视频跑通端到端体验。</p>
            </div>
          </div>
        </section>
        <section className="mt-10">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400">Education</h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-[140px_1fr]">
            <span className="text-sm text-neutral-400">2025 — 2028（计划）</span>
            <div>
              <h3 className="font-medium">宁波大学阳明学院 · 金融工程</h3>
              <p className="mt-2 leading-7 text-neutral-500">大一已转专业到金融工程，计划大二修完全部学分，提前一年 2028 年毕业。短期准备暑假北京实习面试，中期目标是大三字节实习，长期目标是大学毕业创业 → 援助非洲。</p>
            </div>
          </div>
        </section>
        <section className="mt-10">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400">Selected experience</h2>
          <div className="mt-5 space-y-8">
            {profile.projects.map((project) => (
              <div key={project.id} className="grid gap-3 sm:grid-cols-[140px_1fr]">
                <span className="text-sm text-neutral-400">{project.stage}</span>
                <div>
                  <h3 className="font-medium">{project.name}</h3>
                  <p className="mt-2 leading-7 text-neutral-500">{project.result}</p>
                  {project.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {project.tags.map((tag) => <span key={tag} className="rounded-md bg-neutral-100 px-2 py-0.5 text-xs text-neutral-500">{tag}</span>)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className="mt-20 rounded-xl border border-neutral-200 bg-neutral-50 p-6">
        <p className="text-sm leading-7 text-neutral-600">
          想知道更多？右下角的<span className="font-medium">妙喵🐱</span>会读最近的日记来回答你。
        </p>
        <p className="mt-3 text-sm leading-7 text-neutral-600">
          我相信记忆要握在自己手里——日记数据存在自己的数据库里，不依赖任何平台。{' '}
          <Link href="/projects" className="text-neutral-900 underline-offset-2 hover:underline">
            Cline 跨平台 AI 记忆中枢
          </Link>{' '}
          是同样思路的底座。
        </p>
      </section>
    </>
  )
}

import type { Metadata } from 'next'
import Link from 'next/link'
import { getSite } from '@/lib/site'
import { BlurFade } from '@/components/magicui/blur-fade'
import { DiaryCard } from '@/components/diary-card'

export const metadata: Metadata = {
  title: 'Diary · 日记',
  description: '博主日记时间线——让数字名片成为持续在更新的人。',
}

export default async function DiaryPage() {
  const profile = await getSite()
  const diary = profile.diary ?? []
  const pinned = diary.filter((d) => d.pinned)
  const rest = diary.filter((d) => !d.pinned)

  return (
    <>
      <BlurFade>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Diary</h1>
        <p className="mt-5 max-w-2xl leading-8 text-neutral-600">
          每天在做什么、想了什么、做了什么。这是让数字名片从「静态介绍页」变成「持续在更新的人」的地方——
          妙喵被问「最近在忙什么」时，会从这里取最近的几条作答。
        </p>
        <p className="mt-3 text-sm text-neutral-400">
          最近 {diary.length} 条 · 最近更新 {diary[0]?.date ?? '—'}
        </p>
      </BlurFade>

      {pinned.length > 0 && (
        <section className="mt-12">
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
        <h2 className="mb-4 text-xs font-medium uppercase tracking-wide text-neutral-400">最近</h2>
        {rest.length === 0 ? (
          <p className="text-neutral-400">暂无日记。</p>
        ) : (
          <div className="grid gap-4">
            {rest.map((entry, index) => (
              <BlurFade key={entry.id} delay={0.04 * (index + 1)}>
                <DiaryCard entry={entry} />
              </BlurFade>
            ))}
          </div>
        )}
      </section>

      <section className="mt-20 rounded-xl border border-neutral-200 bg-neutral-50 p-6">
        <p className="text-sm leading-7 text-neutral-600">
          想知道更多？右下角的<span className="font-medium">妙喵🐱</span>会读最近的日记来回答你。
        </p>
        <p className="mt-3 text-sm leading-7 text-neutral-600">
          我相信记忆要握在自己手里——日记数据存在自己的数据库里，不依赖任何平台。{' '}
          <Link href="/projects#cline-memory-hub" className="text-neutral-900 underline-offset-2 hover:underline">
            Cline 跨平台 AI 记忆中枢
          </Link>{' '}
          是同样思路的底座。
        </p>
      </section>
    </>
  )
}

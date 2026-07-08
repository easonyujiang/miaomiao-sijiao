import type { Metadata } from 'next'
import { Suspense } from 'react'
import { getSite } from '@/lib/site'
import { ProjectVideo } from '@/components/project-video'

export const metadata: Metadata = { title: 'Projects', description: 'AI Agent、视频内容重构与创作者工具项目。' }

export default async function ProjectsPage() {
  const profile = await getSite()
  return <><h1 className="text-3xl font-semibold tracking-tight">Projects</h1><p className="mt-3 max-w-2xl leading-7 text-neutral-500">从原型验证到完整产品端点，以下项目都围绕一个问题：怎样让 AI 真正进入用户的工作和学习过程。</p><div className="mt-12 space-y-10">{profile.projects.map((project) => <article key={project.id} className="border-b border-neutral-200 pb-10"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-xl font-semibold tracking-tight">{project.name}</h2><span className="text-xs text-neutral-400">{project.stage}</span></div><p className="mt-3 leading-7 text-neutral-600">{project.summary}</p><p className="mt-3 text-sm leading-6 text-neutral-500">{project.result}</p><div className="mt-4 flex flex-wrap gap-2">{project.tags.map((tag) => <span key={tag} className="rounded-md bg-neutral-100 px-2 py-1 text-xs text-neutral-500">{tag}</span>)}</div></article>)}</div><Suspense fallback={<div className="mt-16 h-64 animate-pulse rounded-xl bg-neutral-100" />}><ProjectVideo videos={profile.videos} /></Suspense></>
}

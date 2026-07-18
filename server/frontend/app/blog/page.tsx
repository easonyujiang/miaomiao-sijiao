import type { Metadata } from 'next'
import Link from 'next/link'
import { posts } from '@/lib/posts'

export const dynamic = 'force-dynamic'

export const metadata: Metadata = { title: 'Blog', description: '关于 AI Agent、视频产品和独立开发的文章。' }

export default function BlogPage() {
  return <><h1 className="text-3xl font-semibold tracking-tight">Blog</h1><p className="mt-3 text-neutral-500">记录产品判断、技术实现和公开构建过程。</p><div className="mt-10">{posts.map((post) => <Link key={post.meta.slug} href={`/blog/${post.meta.slug}`} className="group grid gap-2 border-b border-neutral-200 py-6 sm:grid-cols-[130px_1fr]"><time className="text-sm text-neutral-400">{post.meta.date}</time><div><h2 className="font-medium group-hover:underline">{post.meta.title}</h2><p className="mt-1 text-sm leading-6 text-neutral-500">{post.meta.summary}</p><div className="mt-3 flex flex-wrap gap-2">{post.meta.tags.map((tag) => <span key={tag} className="text-xs text-neutral-400">#{tag}</span>)}</div></div></Link>)}</div></>
}

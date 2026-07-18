import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getPost, posts } from '@/lib/posts'

export const dynamic = 'force-dynamic'

export function generateStaticParams() {
  return posts.map((post) => ({ slug: post.meta.slug }))
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params
  const post = getPost(slug)
  if (!post) return {}
  return { title: post.meta.title, description: post.meta.summary, openGraph: { type: 'article', publishedTime: post.meta.date } }
}

export default async function PostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const post = getPost(slug)
  if (!post) notFound()
  const { Component } = post
  return <article><Link href="/blog" className="text-sm text-neutral-500 hover:text-neutral-950">← Back to blog</Link><div className="mt-10 border-b border-neutral-200 pb-8"><time className="text-sm text-neutral-400">{post.meta.date}</time><p className="mt-3 text-sm text-neutral-500">{post.meta.summary}</p></div><div className="mt-10"><Component /></div></article>
}

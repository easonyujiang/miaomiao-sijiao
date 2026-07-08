import type { MetadataRoute } from 'next'
import { posts } from '@/lib/posts'

export const dynamic = 'force-static'

export default function sitemap(): MetadataRoute.Sitemap {
  const origin = process.env.NEXT_PUBLIC_SITE_URL || 'http://127.0.0.1:3000'
  return ['/', '/blog', '/projects', '/resume'].map((path) => ({ url: `${origin}${path}`, lastModified: new Date() })).concat(posts.map((post) => ({ url: `${origin}/blog/${post.meta.slug}`, lastModified: new Date(post.meta.date) })))
}

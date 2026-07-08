import { posts } from '@/lib/posts'

export const dynamic = 'force-static'

function escape(value: string) {
  return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
}

export function GET() {
  const origin = process.env.NEXT_PUBLIC_SITE_URL || 'http://127.0.0.1:3000'
  const items = posts.map((post) => `<item><title>${escape(post.meta.title)}</title><link>${origin}/blog/${post.meta.slug}</link><guid>${origin}/blog/${post.meta.slug}</guid><pubDate>${new Date(post.meta.date).toUTCString()}</pubDate><description>${escape(post.meta.summary)}</description></item>`).join('')
  const xml = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>AI Product Builder</title><link>${origin}</link><description>AI Agent、视频产品和独立开发。</description>${items}</channel></rss>`
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } })
}

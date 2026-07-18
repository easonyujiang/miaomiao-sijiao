import type { Metadata } from 'next'
import { getSite } from '@/lib/site'
import { SiteHeader } from '@/components/site-header'
import { PetAssistant } from '@/components/pet-assistant'
import { AppWrapper } from '@/components/app-wrapper'
import './globals.css'

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'http://127.0.0.1:3000'),
  title: { default: 'AI Product Builder', template: '%s — AI Product Builder' },
  description: '关于 AI Agent、视频内容重构和创作者工具的项目与文章。',
  openGraph: { type: 'website', locale: 'zh_CN', title: 'AI Product Builder', description: '关于 AI Agent、视频内容重构和创作者工具的项目与文章。' },
  twitter: { card: 'summary', title: 'AI Product Builder' },
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const profile = await getSite()
  return <html lang="zh-CN"><body><AppWrapper><SiteHeader name={profile.identity.name} /><main className="mx-auto min-h-[calc(100vh-10rem)] w-full max-w-3xl px-5 pb-24 pt-10 sm:px-8">{children}</main><footer className="mx-auto flex w-full max-w-3xl justify-between border-t border-neutral-200 px-5 py-8 text-sm text-neutral-500 sm:px-8"><span>© 2026 {profile.identity.name}</span><span>Next.js 15 · MDX</span></footer><PetAssistant profile={profile} /></AppWrapper></body></html>
}

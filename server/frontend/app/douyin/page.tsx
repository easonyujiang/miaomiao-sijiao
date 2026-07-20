import type { Metadata, Viewport } from 'next'
import DouyinContent from './douyin-content'

export const metadata: Metadata = {
  title: '妙喵私教 · 移动学习页',
  description: '把抖音/B站教学视频变成一对一私教——妙喵帮你看视频、出题、纠错、跳片段',
  manifest: '/manifest-douyin.json',
  appleWebApp: {
    capable: true,
    title: '妙喵私教',
    statusBarStyle: 'black-translucent',
  },
  icons: {
    icon: '/cat-icon.svg',
    apple: '/cat-icon.svg',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#f472b6',
}

export default function DouyinPage() {
  return <DouyinContent />
}

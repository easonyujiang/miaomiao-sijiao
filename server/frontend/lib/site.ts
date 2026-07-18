import { readFileSync } from 'fs'
import { join } from 'path'
import { cache } from 'react'
import { siteProfile, type SiteProfile } from '@/src/data/siteProfile'

const SITE_SLUG = process.env.NEXT_PUBLIC_SITE_SLUG || 'ashley'

export const getSite = cache(async (): Promise<SiteProfile> => {
  // 1. 优先从后端 API 获取（仅运行时可用）
  if (process.env.API_BASE_URL && typeof window === 'undefined') {
    try {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), 5000)
      const response = await fetch(`${process.env.API_BASE_URL}/api/site/${SITE_SLUG}`, { next: { revalidate: 60 }, signal: controller.signal })
      clearTimeout(timer)
      if (response.ok) {
        return await response.json() as SiteProfile
      }
    } catch {
      // API 不可用，继续降级
    }
  }

  // 2. 直接读取本地 fallback 文件（构建和运行时均可用）
  try {
    const data = readFileSync(join(process.cwd(), 'public', 'fallback.json'), 'utf-8')
    return JSON.parse(data) as SiteProfile
  } catch {
    // fallback.json 不存在，继续最终降级
  }

  // 3. 最终回退：静态 siteProfile 数据
  return siteProfile
})

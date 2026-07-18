import { cache } from 'react'
import { siteProfile, type SiteProfile } from '@/src/data/siteProfile'

const SITE_SLUG = process.env.NEXT_PUBLIC_SITE_SLUG || 'ashley'

export const getSite = cache(async (): Promise<SiteProfile> => {
  // 1. 优先从后端 API 获取
  const origin = process.env.API_BASE_URL
  if (origin) {
    try {
      const response = await fetch(`${origin}/api/site/${SITE_SLUG}`, { next: { revalidate: 60 } })
      if (response.ok) {
        return await response.json() as SiteProfile
      }
    } catch {
      // API 不可用，继续降级
    }
  }

  // 2. 尝试从 public/fallback.json 加载
  try {
    const response = await fetch('/fallback.json')
    if (response.ok) {
      return await response.json() as SiteProfile
    }
  } catch {
    // fallback.json 不存在，继续最终降级
  }

  // 3. 最终回退：静态 siteProfile 数据
  return siteProfile
})

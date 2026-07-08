import { cache } from 'react'
import { siteProfile, type SiteProfile } from '@/src/data/siteProfile'

export const getSite = cache(async (): Promise<SiteProfile> => {
  // 1. 优先从后端 API 获取（需要设置 API_BASE_URL 环境变量）
  const origin = process.env.API_BASE_URL
  if (origin) {
    try {
      const response = await fetch(`${origin}/api/site/ashley`, { next: { revalidate: 60 } })
      if (response.ok) {
        return await response.json() as SiteProfile
      }
    } catch {
      // API 不可用，继续降级
    }
  }

  // 2. P1-4: 尝试从 public/fallback.json 加载（运行 scripts/generate_fallback.py 生成）
  try {
    const response = await fetch('/fallback.json')
    if (response.ok) {
      return await response.json() as SiteProfile
    }
  } catch {
    // fallback.json 不存在，继续最终降级
  }

  // 3. 最终回退：硬编码的静态 siteProfile 数据
  return siteProfile
})

import { cache } from 'react'
import { siteProfile, type SiteProfile } from '@/src/data/siteProfile'

export const getSite = cache(async (): Promise<SiteProfile> => {
  const origin = process.env.API_BASE_URL
  if (!origin) return siteProfile
  try {
    const response = await fetch(`${origin}/api/site/ashley`, { next: { revalidate: 60 } })
    if (!response.ok) return siteProfile
    return await response.json() as SiteProfile
  } catch {
    return siteProfile
  }
})

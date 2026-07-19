'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function HomePage() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/community')
  }, [router])

  return (
    <div className="flex min-h-[40vh] items-center justify-center text-sm text-neutral-500">
      正在跳转…
    </div>
  )
}

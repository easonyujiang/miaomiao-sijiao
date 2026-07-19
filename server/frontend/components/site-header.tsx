import Link from 'next/link'

export function SiteHeader() {
  return <header className="mx-auto flex h-20 w-full max-w-3xl items-center justify-between px-5 sm:px-8">
    <Link href="/community" className="font-semibold tracking-tight">妙喵社区</Link>
    <nav className="flex items-center gap-5 text-sm text-neutral-500 sm:gap-7">
      <Link href="/community" className="transition hover:text-neutral-950">首页</Link>
      <Link href="/profile" className="transition hover:text-neutral-950">主页</Link>
      <Link href="/admin/" className="transition hover:text-neutral-950">管理</Link>
    </nav>
  </header>
}

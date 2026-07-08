import Link from 'next/link'

export function SiteHeader({ name }: { name: string }) {
  return <header className="mx-auto flex h-20 w-full max-w-3xl items-center justify-between px-5 sm:px-8">
    <Link href="/" className="font-semibold tracking-tight">{name}</Link>
    <nav className="flex items-center gap-5 text-sm text-neutral-500 sm:gap-7">
      <Link href="/" className="transition hover:text-neutral-950">Home</Link>
      <Link href="/diary" className="transition hover:text-neutral-950">Diary</Link>
      <Link href="/blog" className="transition hover:text-neutral-950">Blog</Link>
      <Link href="/projects" className="transition hover:text-neutral-950">Projects</Link>
      <Link href="/resume" className="transition hover:text-neutral-950">Resume</Link>
    </nav>
  </header>
}

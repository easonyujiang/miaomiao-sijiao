import Link from 'next/link'

export default function NotFound() {
  return <div className="py-24 text-center"><p className="text-sm text-neutral-400">404</p><h1 className="mt-3 text-2xl font-semibold">Page not found</h1><Link href="/" className="mt-6 inline-block text-sm underline">Go home</Link></div>
}

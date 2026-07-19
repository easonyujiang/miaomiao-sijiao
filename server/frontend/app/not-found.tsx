import Link from 'next/link'
import { CatLottie } from '@/src/components/cat-lottie'

export default function NotFound() {
  return (
    <div className="py-24 text-center">
      <div className="mx-auto w-fit"><CatLottie state="notFound" size={200} /></div>
      <h1 className="mt-3 text-2xl font-semibold">Page not found</h1>
      <Link href="/" className="mt-6 inline-block text-sm underline">Go home</Link>
    </div>
  )
}

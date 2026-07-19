import { CatLottie } from '@/src/components/cat-lottie'

export default function Loading() {
  return (
    <div className="flex justify-center py-24">
      <CatLottie state="loading" size={80} />
    </div>
  )
}

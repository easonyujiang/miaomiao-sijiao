'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import type { CreatorVideo } from '@/src/data/siteProfile'

function formatTime(seconds: number) {
  const safe = Math.max(0, Math.floor(seconds))
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, '0')}`
}

export function ProjectVideo({ videos }: { videos: CreatorVideo[] }) {
  const params = useSearchParams()
  const initialId = params.get('video')
  const initialTime = Number(params.get('t') || 0)
  const [selectedId, setSelectedId] = useState(initialId && videos.some((item) => item.id === initialId) ? initialId : videos[0].id)
  const [currentTime, setCurrentTime] = useState(initialTime)
  const videoRef = useRef<HTMLVideoElement>(null)
  const selected = useMemo(() => videos.find((video) => video.id === selectedId) ?? videos[0], [selectedId, videos])
  const segment = selected.segments.find((item) => currentTime >= item.start && currentTime < item.end) ?? selected.segments[0]

  useEffect(() => {
    if (videoRef.current && initialTime > 0) {
      videoRef.current.currentTime = initialTime
      void videoRef.current.play().catch(() => undefined)
    }
  }, [initialTime, selectedId])

  function seek(seconds: number) {
    setCurrentTime(seconds)
    if (videoRef.current) { videoRef.current.currentTime = seconds; void videoRef.current.play().catch(() => undefined) }
  }

  return <section className="mt-16"><h2 className="text-xl font-semibold tracking-tight">Video demo</h2><div className="mt-5 flex gap-2 overflow-x-auto">{videos.map((video) => <button key={video.id} onClick={() => { setSelectedId(video.id); setCurrentTime(0) }} className={`shrink-0 rounded-full px-3 py-1.5 text-xs ${video.id === selected.id ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-500'}`}>{video.title}</button>)}</div><div className="mt-5 rounded-xl border border-neutral-200 bg-white p-4">{selected.duration > 0 ? <div className="grid gap-5 sm:grid-cols-[220px_1fr]"><video ref={videoRef} src={selected.source || '/ai-tutorial-demo.mp4'} controls playsInline className="aspect-[7/16] max-h-[480px] w-full rounded-lg bg-black object-contain" onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)} /><div><p className="text-xs text-neutral-400">{formatTime(currentTime)} / {formatTime(selected.duration)}</p><h3 className="mt-2 font-semibold">{selected.title}</h3><p className="mt-2 text-sm leading-6 text-neutral-500">{segment?.summary}</p><div className="mt-5">{selected.segments.map((item) => <button key={item.id} onClick={() => seek(item.start)} className={`grid w-full grid-cols-[50px_1fr] border-t border-neutral-100 py-3 text-left text-sm ${item.id === segment?.id ? 'text-neutral-950' : 'text-neutral-400 hover:text-neutral-950'}`}><span>{formatTime(item.start)}</span><span>{item.title}</span></button>)}</div></div></div> : <div className="py-6"><h3 className="font-semibold">{selected.title}</h3><p className="mt-2 leading-7 text-neutral-500">{selected.summary}</p><div className="mt-5 space-y-3">{selected.segments.map((item) => <div key={item.id} className="rounded-lg bg-neutral-50 p-4"><h4 className="text-sm font-medium">{item.title}</h4><p className="mt-1 text-sm leading-6 text-neutral-500">{item.summary}</p></div>)}</div></div>}</div></section>
}

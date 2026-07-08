import Link from 'next/link'
import type { DiaryEntry } from '@/src/data/siteProfile'

const MOOD_LABEL: Record<string, string> = {
  focused: '专注',
  excited: '兴奋',
  tired: '疲惫',
  curious: '好奇',
  proud: '自豪',
}

const MOOD_EMOJI: Record<string, string> = {
  focused: '🎯',
  excited: '✨',
  tired: '🌧',
  curious: '🌱',
  proud: '🌟',
}

function formatDate(date: string) {
  // YYYY-MM-DD -> 6月29日 · 周一
  const d = new Date(date + 'T00:00:00+08:00')
  const month = d.getMonth() + 1
  const day = d.getDate()
  const weekday = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()]
  return `${month}月${day}日 · ${weekday}`
}

export function DiaryCard({ entry }: { entry: DiaryEntry }) {
  return (
    <article className="rounded-xl border border-neutral-200 bg-white p-5 transition hover:border-neutral-300 hover:shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <time className="text-xs uppercase tracking-wide text-neutral-400" dateTime={entry.date}>
          {formatDate(entry.date)}
        </time>
        <div className="flex items-center gap-2">
          {entry.pinned && (
            <span className="rounded-md bg-amber-50 px-2 py-0.5 text-xs text-amber-700">置顶</span>
          )}
          {entry.mood && (
            <span className="rounded-md bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600">
              {MOOD_EMOJI[entry.mood] || '📝'} {MOOD_LABEL[entry.mood] || entry.mood}
            </span>
          )}
        </div>
      </div>

      <h3 className="mt-3 text-lg font-semibold tracking-tight">{entry.title}</h3>
      <p className="mt-2 leading-7 text-neutral-600">{entry.summary}</p>

      {entry.highlights.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {entry.highlights.map((h, i) => (
            <li key={i} className="flex gap-2 text-sm leading-6 text-neutral-700">
              <span className="mt-0.5 select-none text-neutral-400">·</span>
              <span>{h}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex flex-wrap gap-1.5">
        {entry.tags.map((tag) => (
          <span key={tag} className="rounded-md bg-neutral-100 px-2 py-0.5 text-xs text-neutral-500">
            #{tag}
          </span>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-400">
        {entry.location && <span>📍 {entry.location}</span>}
        {entry.weather && <span>天气 {entry.weather}</span>}
      </div>

      {entry.links.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 border-t border-neutral-100 pt-3 text-sm">
          <span className="text-xs text-neutral-400">关联</span>
          {entry.links.map((link, i) => {
            const inner = <span className="text-neutral-600 hover:text-neutral-950">{link.label}</span>
            return link.url ? (
              <a key={i} href={link.url} target="_blank" rel="noreferrer" className="transition hover:underline">
                {inner}
              </a>
            ) : link.id ? (
              <Link key={i} href={`/projects#${link.id}`} className="transition hover:underline">
                {inner}
              </Link>
            ) : (
              <span key={i}>{inner}</span>
            )
          })}
        </div>
      )}
    </article>
  )
}

export { MOOD_LABEL, MOOD_EMOJI, formatDate }

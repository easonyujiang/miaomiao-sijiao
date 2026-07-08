import SongZhiqiuArchive, { meta as songZhiqiuArchiveMeta } from '@/src/content/posts/song-zhiqiu-archive.mdx'

export type PostMeta = {
  title: string
  summary: string
  date: string
  slug: string
  tags: string[]
}

export const posts = [
  { meta: songZhiqiuArchiveMeta as PostMeta, Component: SongZhiqiuArchive },
].sort((a, b) => b.meta.date.localeCompare(a.meta.date))

export function getPost(slug: string) {
  return posts.find((post) => post.meta.slug === slug)
}

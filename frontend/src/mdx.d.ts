declare module '*.mdx' {
  import type { ComponentType } from 'react'

  export const meta: {
    title: string
    summary: string
    date: string
    slug: string
    tags: string[]
  }

  const MDXComponent: ComponentType
  export default MDXComponent
}

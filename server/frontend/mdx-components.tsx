import type { MDXComponents } from 'mdx/types'

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    h1: (props) => <h1 className="mb-8 text-3xl font-semibold tracking-tight sm:text-4xl" {...props} />,
    h2: (props) => <h2 className="mb-3 mt-12 text-xl font-semibold tracking-tight" {...props} />,
    p: (props) => <p className="my-5 leading-8 text-neutral-700" {...props} />,
    ul: (props) => <ul className="my-5 list-disc space-y-2 pl-6 text-neutral-700" {...props} />,
    ol: (props) => <ol className="my-5 list-decimal space-y-2 pl-6 text-neutral-700" {...props} />,
    pre: (props) => <pre className="my-6 overflow-x-auto rounded-lg bg-neutral-950 p-4 text-sm text-neutral-100" {...props} />,
    table: (props) => <div className="my-6 overflow-x-auto"><table className="w-full border-collapse text-sm" {...props} /></div>,
    th: (props) => <th className="border-b border-neutral-300 p-3 text-left" {...props} />,
    td: (props) => <td className="border-b border-neutral-200 p-3 text-left text-neutral-600" {...props} />,
    ...components,
  }
}

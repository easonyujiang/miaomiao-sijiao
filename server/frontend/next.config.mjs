import createMDX from '@next/mdx'

const withMDX = createMDX({
  extension: /\.mdx?$/,
  options: {
    remarkPlugins: ['remark-gfm'],
  },
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  pageExtensions: ['js', 'jsx', 'md', 'mdx', 'ts', 'tsx'],
  poweredByHeader: false,
  staticPageGenerationTimeout: 300,
  async redirects() {
    return [
      { source: '/', destination: '/community', permanent: true },
    ]
  },
  // 静态导出不支持 rewrites；dev 模式下保留以便 /api/* 代理到后端
  ...(process.env.NODE_ENV === 'production'
    ? {}
    : {
        async rewrites() {
          const backend = process.env.FASTAPI_ORIGIN || 'http://127.0.0.1:8000'
          return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }]
        },
      }),
}

export default withMDX(nextConfig)

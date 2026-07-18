// Voice command system for the Co-Creation Community demo
// Uses keyword substring matching against Web Speech API transcripts

export type VoiceStatus = 'idle' | 'listening' | 'recognized' | 'executing' | 'error'

export interface VoiceCommand {
  id: string
  keywords: string[]
  category: 'navigation' | 'voice' | 'content' | 'comment'
  description: string
  handler: () => void
}

export interface CommandGroup {
  category: VoiceCommand['category']
  label: string
  icon: string
}

export const COMMAND_CATEGORIES: CommandGroup[] = [
  { category: 'voice', label: '语音控制', icon: '🎤' },
  { category: 'navigation', label: '页面导航', icon: '🧭' },
  { category: 'content', label: '内容浏览', icon: '📱' },
  { category: 'comment', label: '评论互动', icon: '💬' },
]

// Match a transcript against a list of commands
// Returns the first command whose keywords match the transcript
export function matchCommand(
  transcript: string,
  commands: VoiceCommand[],
): VoiceCommand | null {
  const normalized = transcript.toLowerCase().trim()
  if (!normalized) return null

  // Score each command by longest keyword match
  let bestMatch: VoiceCommand | null = null
  let bestLength = 0

  for (const cmd of commands) {
    for (const kw of cmd.keywords) {
      const kwLower = kw.toLowerCase()
      if (normalized.includes(kwLower) && kwLower.length > bestLength) {
        bestMatch = cmd
        bestLength = kwLower.length
      }
    }
  }

  return bestMatch
}

// Build global navigation commands (router.push based)
export function buildNavCommands(
  push: (path: string) => void,
): VoiceCommand[] {
  return [
    {
      id: 'nav-home',
      keywords: ['首页', '回到首页', '主页'],
      category: 'navigation',
      description: '跳转到首页',
      handler: () => push('/'),
    },
    {
      id: 'nav-community',
      keywords: ['社区', '共创社区', '社区页面'],
      category: 'navigation',
      description: '跳转到共创社区',
      handler: () => push('/community'),
    },
    {
      id: 'nav-projects',
      keywords: ['项目', '我的项目'],
      category: 'navigation',
      description: '查看项目展示',
      handler: () => push('/projects'),
    },
    {
      id: 'nav-diary',
      keywords: ['日记', '我的日记'],
      category: 'navigation',
      description: '查看日记',
      handler: () => push('/diary'),
    },
    {
      id: 'nav-blog',
      keywords: ['博客', '文章'],
      category: 'navigation',
      description: '查看博客文章',
      handler: () => push('/blog'),
    },
    {
      id: 'nav-resume',
      keywords: ['简历', '关于我'],
      category: 'navigation',
      description: '查看个人简历',
      handler: () => push('/resume'),
    },
  ]
}

// Build voice control commands (start/stop/help)
export function buildVoiceCommands(
  startFn: () => void,
  stopFn: () => void,
  helpFn: () => void,
): VoiceCommand[] {
  return [
    {
      id: 'voice-start',
      keywords: ['打开语音', '开始语音', '你好妙喵', '妙喵'],
      category: 'voice',
      description: '开启语音控制',
      handler: startFn,
    },
    {
      id: 'voice-stop',
      keywords: ['关闭语音', '停止语音', '静音'],
      category: 'voice',
      description: '关闭语音控制',
      handler: stopFn,
    },
    {
      id: 'voice-help',
      keywords: ['帮助', '语音命令', '能说什么', '怎么用'],
      category: 'voice',
      description: '显示语音命令帮助',
      handler: helpFn,
    },
  ]
}

// Build content navigation commands
export function buildContentCommands(
  onNext: () => void,
  onPrev: () => void,
  onOpen: () => void,
  onBack: () => void,
): VoiceCommand[] {
  return [
    {
      id: 'content-next',
      keywords: ['下一条', '下一个', '往下'],
      category: 'content',
      description: '选择下一个内容',
      handler: onNext,
    },
    {
      id: 'content-prev',
      keywords: ['上一条', '上一个', '往上'],
      category: 'content',
      description: '选择上一个内容',
      handler: onPrev,
    },
    {
      id: 'content-open',
      keywords: ['打开', '查看', '详情', '查看详情'],
      category: 'content',
      description: '打开内容详情',
      handler: onOpen,
    },
    {
      id: 'content-back',
      keywords: ['返回', '关闭', '回到列表', '退出'],
      category: 'content',
      description: '返回内容列表',
      handler: onBack,
    },
  ]
}

// Build comment interaction commands
export function buildCommentCommands(
  onOpen: () => void,
  onClose: () => void,
  onExpand: () => void,
  onCollapse: () => void,
): VoiceCommand[] {
  return [
    {
      id: 'comment-open',
      keywords: ['打开评论', '查看评论', '看评论', '评论'],
      category: 'comment',
      description: '打开评论区',
      handler: onOpen,
    },
    {
      id: 'comment-close',
      keywords: ['关闭评论', '收起评论'],
      category: 'comment',
      description: '关闭评论区',
      handler: onClose,
    },
    {
      id: 'comment-expand',
      keywords: ['展开回复', '查看回复', '展开'],
      category: 'comment',
      description: '展开所有子回复',
      handler: onExpand,
    },
    {
      id: 'comment-collapse',
      keywords: ['收起回复', '折叠回复', '收起'],
      category: 'comment',
      description: '收起所有子回复',
      handler: onCollapse,
    },
  ]
}

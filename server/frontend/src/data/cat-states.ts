/**
 * 妙喵状态注册表 —— 单一事实源
 * 状态 key → Lottie JSON 路径 + 联动音效 + 循环策略 + 情绪标签
 *
 * 资产来源见《前端与音效购置方案》§一（Lottie Simple License）
 */

export type CatStateKey =
  | 'idle'         // 待命（Lovely Cats · 毛线球）
  | 'watching'     // 听课（Cat Playing · 毛线球）
  | 'listening'    // 听你说（Cat Meow）
  | 'analyzing'    // 判卷中（Cat Loading · 转毛线球）
  | 'correcting'   // 纠错（Cat Typing · 黑猫敲电脑）
  | 'celebrating'  // 庆祝（Dance cat · 跳舞）
  | 'reward'       // 小鱼干奖励（Cat Eating Fish）
  | 'failed'       // 答错安慰（Sad Cat）
  | 'notFound'     // 404（404 Error Page with Cat）
  | 'loading'      // 全局加载（Cat Loader）
  | 'levelup'      // 课程完成（复用 Dance cat）
  | 'seeking'      // 跳转/指向
  | 'sleepy'       // 困倦/打哈欠
  | 'stretch'      // 伸懒腰
  | 'tail'         // 甩尾巴

export type SoundKey =
  | 'pop-open' | 'pop-close' | 'send' | 'receive' | 'thinking'
  | 'meow' | 'pass' | 'perfect' | 'fail' | 'seek'
  | 'level-up' | 'click' | 'badge' | 'yawn'

export type Mood = 'happy' | 'sad' | 'curious' | 'alert' | 'neutral' | 'sleepy'

export type CatStateDef = {
  /** frontend/public/lottie/ 下的文件名 */
  file: string
  /** 进入该状态时播放的音效（undefined = 安静） */
  sound?: SoundKey
  /** thinking 循环音效：进入时 start、离开时 stop */
  thinkingLoop?: boolean
  /** lottie-react 的 loop 参数 */
  loop: boolean
  /** 状态中文名（无障碍 label） */
  label: string
  /** 情绪标签，用于生活化语气 */
  mood: Mood
}

export const CAT_STATES: Record<CatStateKey, CatStateDef> = {
  idle:        { file: 'cat-lovely.json',  sound: undefined,  loop: true,  label: '妙喵待命中', mood: 'neutral' },
  watching:    { file: 'cat-playing.json', sound: undefined,  loop: true,  label: '妙喵听课中', mood: 'alert' },
  listening:   { file: 'cat-meow.json',    sound: 'meow',     loop: true,  label: '妙喵在听你说', mood: 'curious' },
  analyzing:   { file: 'cat-loading.json', thinkingLoop: true, loop: true, label: '妙喵正在判卷', mood: 'alert' },
  correcting:  { file: 'cat-typing.json',  sound: 'fail',     loop: true,  label: '妙喵帮你纠错', mood: 'alert' },
  celebrating: { file: 'cat-dance.json',   sound: 'pass',     loop: true,  label: '妙喵为你开心', mood: 'happy' },
  reward:      { file: 'cat-eating-fish.json', sound: 'badge', loop: false, label: '获得小鱼干', mood: 'happy' },
  failed:      { file: 'cat-sad.json',     sound: 'fail',     loop: true,  label: '妙喵安慰你', mood: 'sad' },
  notFound:    { file: 'cat-404.json',     sound: undefined,  loop: true,  label: '页面走丢了', mood: 'curious' },
  loading:     { file: 'cat-loader.json',  sound: undefined,  loop: true,  label: '加载中', mood: 'neutral' },
  levelup:     { file: 'cat-dance.json',   sound: 'level-up', loop: false, label: '课程完成', mood: 'happy' },
  seeking:     { file: 'cat-playing.json', sound: 'seek',     loop: true,  label: '妙喵跳转中', mood: 'alert' },
  sleepy:      { file: 'cat-sleepy.json',  sound: 'yawn',     loop: true,  label: '妙喵困了', mood: 'sleepy' },
  stretch:     { file: 'cat-stretch.json', sound: undefined,  loop: false, label: '妙喵伸懒腰', mood: 'neutral' },
  tail:        { file: 'cat-tail.json',    sound: undefined,  loop: true,  label: '妙喵摇尾巴', mood: 'neutral' },
}

/** 3 星完美通过时，celebrating 的音效换成 perfect（在组件调用处覆盖 sound） */
export const PERFECT_SOUND: SoundKey = 'perfect'

/** 保护状态：播放期间不被 idle 闲聊打断 */
export const FORM_PROTECTED: CatStateKey[] = ['analyzing', 'celebrating', 'failed', 'levelup']

/** 本地兜底形态映射：当后端没给 form 时按关键词猜 */
export function moodFor(text: string): CatStateKey {
  if (!text) return 'idle'
  const t = text
  if (/答对|通过|好棒|完美|厉害|恭喜/.test(t)) return 'celebrating'
  if (/小鱼干|奖励/.test(t)) return 'reward'
  if (/不对|错了|失败|安慰|别灰心/.test(t)) return 'failed'
  if (/关键|注意|讲解|法条|条款|构成/.test(t)) return 'watching'
  if (/想想|分析|思考一下/.test(t)) return 'analyzing'
  if (/好问题|你说|呢\?|吗\?/.test(t)) return 'listening'
  if (/跳回|回到|SEEK/.test(t)) return 'seeking'
  if (/困|休息|zzz/.test(t)) return 'sleepy'
  return 'idle'
}

export function calcDuration(text: string, msPerChar = 50, minMs = 1200): number {
  if (!text) return minMs
  const extra = (text.match(/[，。！？；、：]/g) || []).length
  return Math.max(minMs, (text.length + extra) * msPerChar)
}

export type SpeechSegment = {
  text: string
  form?: CatStateKey
  duration_ms?: number
  seek_to_sec?: number
}

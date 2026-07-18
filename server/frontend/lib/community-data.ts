// Mock data for the Co-Creation Community demo
// Provides realistic content for roadshow demos without backend dependency

export interface ContentItem {
  id: string
  type: 'video' | 'question' | 'discussion' | 'share'
  title: string
  description: string
  author: { name: string; avatar: string }
  thumbnailColor: string  // CSS gradient for demo thumbnail
  category: string
  tags: string[]
  createdAt: string
  likes: number
  commentCount: number
  videoUrl?: string       // B站视频链接
  bvid?: string           // B站 BV 号
}

export interface Comment {
  id: string
  contentId: string
  parentId: string | null
  author: { name: string; avatar: string }
  content: string
  createdAt: string
  likes: number
  replies: Comment[]
}

export const CATEGORIES = [
  { key: 'all', label: '全部' },
  { key: 'video-qa', label: '🎬 视频问答' },
  { key: 'course-discussion', label: '📚 课程讨论' },
  { key: 'experience-share', label: '💡 经验分享' },
]

export const MOCK_CONTENT: ContentItem[] = [
  {
    id: 'content-1',
    type: 'video',
    title: '正当防卫的构成要件 — 罗翔刑法精讲',
    description: '张三深夜回家误伤物业工人，是否构成正当防卫？本视频讲解正当防卫的五个核心要件，配套闯关答题助你掌握知识点。',
    author: { name: '罗翔说刑法', avatar: 'LX' },
    thumbnailColor: 'from-indigo-500 to-purple-600',
    category: 'video-qa',
    tags: ['刑法', '正当防卫', '闯关答题'],
    createdAt: '2026-07-15',
    likes: 128,
    commentCount: 23,
    videoUrl: 'https://www.bilibili.com/video/BV1mJ4m147PG',
    bvid: 'BV1mJ4m147PG',
  },
  {
    id: 'content-2',
    type: 'question',
    title: '假想防卫和防卫过当有什么区别？',
    description: '看完罗翔老师的正当防卫视频后，对假想防卫和防卫过当的概念有些混淆，能详细解释一下两者的区别吗？',
    author: { name: '法学萌新', avatar: 'FX' },
    thumbnailColor: 'from-rose-500 to-pink-600',
    category: 'video-qa',
    tags: ['刑法', '正当防卫', '假想防卫'],
    createdAt: '2026-07-14',
    likes: 45,
    commentCount: 8,
    videoUrl: 'https://www.bilibili.com/video/BV1mJ4m147PG',
    bvid: 'BV1mJ4m147PG',
  },
  {
    id: 'content-3',
    type: 'video',
    title: 'AI Agent 端点验证全流程演示',
    description: '从视频上传、知识库构建到宠物问答的完整流程展示。包含视频片段导航、FAQ 匹配和 LLM 风格改写三个核心环节。',
    author: { name: '钟笑咪', avatar: 'ZXM' },
    thumbnailColor: 'from-emerald-500 to-teal-600',
    category: 'video-qa',
    tags: ['Agent', '视频 RAG', '妙喵'],
    createdAt: '2026-07-13',
    likes: 67,
    commentCount: 12,
    videoUrl: 'https://www.bilibili.com/video/BV1mJ4m147PG',
    bvid: 'BV1mJ4m147PG',
  },
  {
    id: 'content-4',
    type: 'question',
    title: '视频字幕分段的准确率怎么提高到 92% 的？',
    description: '看到分享中提到关键帧检测 + OCR 字幕提取 + 转写文本多模态分段，具体是怎么实现的？关键帧检测用的什么算法？',
    author: { name: 'AI 开发者小林', avatar: 'XL' },
    thumbnailColor: 'from-amber-500 to-orange-600',
    category: 'video-qa',
    tags: ['字幕', '多模态', '分段算法'],
    createdAt: '2026-07-12',
    likes: 34,
    commentCount: 6,
    videoUrl: 'https://www.bilibili.com/video/BV1mJ4m147PG',
    bvid: 'BV1mJ4m147PG',
  },
  {
    id: 'content-5',
    type: 'discussion',
    title: '闯关答题模式对学习效果有帮助吗？',
    description: '课程闯关答题的设计思路是「看视频 → 答题 → 反馈 → 跳回视频片段」，大家觉得这种学习闭环有效吗？有什么改进建议？',
    author: { name: '教育技术研究生', avatar: 'JY' },
    thumbnailColor: 'from-sky-500 to-blue-600',
    category: 'course-discussion',
    tags: ['闯关答题', '学习闭环', '教育技术'],
    createdAt: '2026-07-11',
    likes: 52,
    commentCount: 15,
    videoUrl: 'https://www.bilibili.com/video/BV1mJ4m147PG',
    bvid: 'BV1mJ4m147PG',
  },
  {
    id: 'content-6',
    type: 'video',
    title: '《献书》互动叙事游戏演示',
    description: '东晋历史题材 AI 互动叙事游戏实机演示，展示 4 个关键选择节点和对应的 AI 生成视频片段。',
    author: { name: '钟笑咪', avatar: 'ZXM' },
    thumbnailColor: 'from-red-600 to-rose-800',
    category: 'video-qa',
    tags: ['献书', 'AI 视频', '互动叙事'],
    createdAt: '2026-07-10',
    likes: 89,
    commentCount: 18,
    videoUrl: 'https://www.bilibili.com/video/BV1mJ4m147PG',
    bvid: 'BV1mJ4m147PG',
  },
  {
    id: 'content-7',
    type: 'share',
    title: 'Cline 跨平台 AI 记忆中枢架构分享',
    description: '分享在 Trae/Claude/Codex/Cursor 多个 AI 平台间搭建共享记忆系统的经验。本地快照 + 云端 SQLite 双层存储，自动同步。',
    author: { name: '钟笑咪', avatar: 'ZXM' },
    thumbnailColor: 'from-violet-500 to-purple-600',
    category: 'experience-share',
    tags: ['记忆中枢', '多 Agent', 'SQLite'],
    createdAt: '2026-07-09',
    likes: 76,
    commentCount: 11,
  },
  {
    id: 'content-8',
    type: 'discussion',
    title: '从校园到黑客松：AI 创业踩坑记录',
    description: '作为宁波大学大一学生，分享参与黑客松、运营社群、做产品的真实经历和思考。希望能帮助到同样在探索的同学。',
    author: { name: '钟笑咪', avatar: 'ZXM' },
    thumbnailColor: 'from-cyan-500 to-teal-600',
    category: 'experience-share',
    tags: ['创业', '黑客松', '校园'],
    createdAt: '2026-07-08',
    likes: 103,
    commentCount: 20,
  },
]

// Helper to build nested comment trees
function buildCommentTree(flatComments: Comment[]): Comment[] {
  const map = new Map<string, Comment>()
  const roots: Comment[] = []

  for (const c of flatComments) {
    map.set(c.id, { ...c, replies: [] })
  }

  for (const c of flatComments) {
    const node = map.get(c.id)!
    if (c.parentId && map.has(c.parentId)) {
      map.get(c.parentId)!.replies.push(node)
    } else {
      roots.push(node)
    }
  }

  return roots
}

// Raw flat comments — will be converted to trees per content item
const FLAT_COMMENTS: Comment[] = [
  // Comments for content-1 (正当防卫)
  {
    id: 'c1',
    contentId: 'content-1',
    parentId: null,
    author: { name: '法学萌新', avatar: 'FX' },
    content: '这个视频把正当防卫的五个要件讲得很清楚！特别是「防卫时机」那部分，以前一直搞不懂。',
    createdAt: '2026-07-15T14:30',
    likes: 12,
    replies: [],
  },
  {
    id: 'c2',
    contentId: 'content-1',
    parentId: 'c1',
    author: { name: '罗翔说刑法', avatar: 'LX' },
    content: '谢谢！时机要件确实是考试重点，建议结合案例反复理解。',
    createdAt: '2026-07-15T15:00',
    likes: 8,
    replies: [],
  },
  {
    id: 'c3',
    contentId: 'content-1',
    parentId: null,
    author: { name: '法考二战人', avatar: 'FZ' },
    content: '闯关答题太有用了！第一题那个张三误伤物业工人的案例，答完之后印象特别深。',
    createdAt: '2026-07-16T09:00',
    likes: 15,
    replies: [],
  },
  // Comments for content-2 (假想防卫)
  {
    id: 'c4',
    contentId: 'content-2',
    parentId: null,
    author: { name: '刑法课代表', avatar: 'FK' },
    content: '假想防卫：客观上不存在不法侵害，但行为人误以为存在；防卫过当：客观上存在不法侵害，但防卫行为超过了必要限度。核心区别在于「侵害是否真实存在」。',
    createdAt: '2026-07-14T16:00',
    likes: 22,
    replies: [],
  },
  {
    id: 'c5',
    contentId: 'content-2',
    parentId: 'c4',
    author: { name: '法学萌新', avatar: 'FX' },
    content: '原来如此！那假想防卫如果致人重伤，怎么定性？',
    createdAt: '2026-07-14T16:30',
    likes: 6,
    replies: [],
  },
  {
    id: 'c6',
    contentId: 'content-2',
    parentId: 'c5',
    author: { name: '刑法课代表', avatar: 'FK' },
    content: '一般按过失致人重伤罪处理，因为行为人主观上没有犯罪故意。',
    createdAt: '2026-07-14T17:00',
    likes: 9,
    replies: [],
  },
  // Comments for content-3 (Agent演示)
  {
    id: 'c7',
    contentId: 'content-3',
    parentId: null,
    author: { name: '视频创作者阿杰', avatar: 'AJ' },
    content: '视频片段导航功能太实用了！能详细说说怎么做的时间轴分段吗？',
    createdAt: '2026-07-13T20:00',
    likes: 10,
    replies: [],
  },
  {
    id: 'c8',
    contentId: 'content-3',
    parentId: 'c7',
    author: { name: '钟笑咪', avatar: 'ZXM' },
    content: '目前是用 Whisper 做语音转写，然后让 LLM 根据转写文本自动识别知识点边界，再映射到视频时间戳。准确率大概在 85% 左右。',
    createdAt: '2026-07-13T21:00',
    likes: 7,
    replies: [],
  },
  // Comments for content-5 (闯关答题)
  {
    id: 'c9',
    contentId: 'content-5',
    parentId: null,
    author: { name: '教育技术研究生', avatar: 'JY' },
    content: '学习闭环的设计很合理。建议增加「错题回顾」功能，让学习者可以重做错过的题目。',
    createdAt: '2026-07-11T19:00',
    likes: 14,
    replies: [],
  },
  {
    id: 'c10',
    contentId: 'content-5',
    parentId: 'c9',
    author: { name: '钟笑咪', avatar: 'ZXM' },
    content: '好建议！已经加到 roadmap 了，会支持「错题本 + 重做」功能。',
    createdAt: '2026-07-11T20:00',
    likes: 11,
    replies: [],
  },
  // Comments for content-6 (献书)
  {
    id: 'c11',
    contentId: 'content-6',
    parentId: null,
    author: { name: '游戏策划阿文', avatar: 'AW' },
    content: '东晋历史题材选得好！市面上三国太多，东晋的 AI 互动游戏还是第一次见。',
    createdAt: '2026-07-10T22:00',
    likes: 16,
    replies: [],
  },
  {
    id: 'c12',
    contentId: 'content-6',
    parentId: 'c11',
    author: { name: '钟笑咪', avatar: 'ZXM' },
    content: '谢谢！立绘用的是 Midjourney + Stable Diffusion 组合，服装和场景参考了大量东晋出土文物。',
    createdAt: '2026-07-10T23:00',
    likes: 13,
    replies: [],
  },
]

export function getCommentsForContent(contentId: string): Comment[] {
  const flat = FLAT_COMMENTS.filter(c => c.contentId === contentId)
  return buildCommentTree(flat)
}

export function getAllCommentCount(contentId: string): number {
  return FLAT_COMMENTS.filter(c => c.contentId === contentId).length
}

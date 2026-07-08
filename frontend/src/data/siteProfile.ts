export type Visibility = 'public' | 'unlisted' | 'private' | 'restricted'

export type SiteLink = {
  label: string
  value: string
  href: string
  visibility: Visibility
}

export type Project = {
  id: string
  name: string
  stage: string
  summary: string
  result: string
  tags: string[]
  href: string
  featured: boolean
}

export type VideoSegment = {
  id: string
  start: number
  end: number
  title: string
  summary: string
  kind: 'hook' | 'knowledge' | 'step' | 'highlight'
}

export type CreatorVideo = {
  id: string
  title: string
  type: string
  duration: number
  source: string
  summary: string
  tags: string[]
  segments: VideoSegment[]
}

export type FrequentlyAskedQuestion = {
  id: string
  question: string
  answer: string
  target?: string
  videoId?: string
  seekTo?: number
}

export type KnowledgeSource = {
  title: string
  kind: 'document' | 'video' | 'transcript' | 'website'
  location: string
  status: 'indexed' | 'reference-only'
  summary: string
}

export type DiaryLink = {
  type: 'project' | 'video' | 'document' | 'website'
  id?: string
  label: string
  url?: string
}

export type DiaryEntry = {
  id: string
  date: string                 // YYYY-MM-DD
  title: string
  mood: string                // focused / excited / tired / curious / proud ...
  weather: string
  location: string
  summary: string
  body: string                 // Markdown
  tags: string[]
  links: DiaryLink[]
  highlights: string[]
  pinned: boolean
}

export type SiteProfile = {
  identity: {
    name: string
    initials: string
    role: string
    location: string
    status: string
    tagline: string
    summary: string
    tags: string[]
  }
  product: {
    validationEndpoint: string
    finalGoal: string
    competitionTrack: string
  }
  pet: {
    name: string
    role: string
    greeting: string
    traits: string[]
    styleBasis: string
  }
  projects: Project[]
  videos: CreatorVideo[]
  faq: FrequentlyAskedQuestion[]
  links: SiteLink[]
  sources: KnowledgeSource[]
  diary: DiaryEntry[]
}

// 本文件只放已从本次对话、本地文档和本地视频中确认的信息。
// 姓名、头像、城市和联系方式尚未在资料中确认，因此保留占位，不做推测。
export const siteProfile: SiteProfile = {
  identity: {
    name: '钟笑咪',
    initials: 'ZXM',
    role: 'AI 应用开发者 · 校园创业者 · 黑客松组织者 · 创作者',
    location: '浙江 · 宁波',
    status: '宁波大学阳明学院 · 大一升大二 · 暑假北京实习准备中',
    tagline: '写代码，也写故事；做产品，也做梦。',
    summary:
      '我是钟笑咪。白天写代码、做 Agent。我相信文字、影像和代码都是同一种东西——把转瞬即逝的瞬间留下来。所以这个网站不只是一张名片，也是一本一直在写的日记：今天在做什么、想了什么、看见了什么风。我把它们都放在自己手里，因为记忆要握在自己手里，才不会被时间偷走。',
    tags: ['AI Agent', '视频重构', '创作者工具', 'Flutter', 'AI 黑客松', '校园创业'],
  },
  product: {
    validationEndpoint: '先用我的个人网站、我的资料和我的视频跑通端到端体验。',
    finalGoal: '为每位视频博主生成一个有个人色彩的宠物 Agent，让粉丝能围绕视频学习、聊天、追问，并跳转到博主的其他视频和具体片段。',
    competitionTrack: '抖音精选赛道二：内容重构，让视频成为你的生活搭子。',
  },
  pet: {
    name: '妙喵',
    role: '博主宠物、视频私教与内容向导',
    greeting: '你好，我是妙喵，笑咪的数字分身。你可以问主人是谁，也可以直接问某条视频讲了什么、最近在忙什么，我会带你跳到对应片段。',
    traits: ['有博主个人色彩', '先回答再带路', '能定位视频片段', '不冒充本人', '只使用有依据资料', '记得主人最近在做什么'],
    styleBasis: '直接、重视实际复用、用具体场景解释抽象想法、相信记忆要握在自己手里。',
  },
  projects: [
    {
      id: 'miaomiao-creator-agent',
      name: '妙喵：博主与粉丝的互动 Agent',
      stage: '抖音黑客松当前方案',
      summary: '把博主的视频库、公开信息与表达风格做成一只宠物 Agent。它既能陪聊，也能教学、推荐其他视频，并把播放器拉到准确片段。',
      result: '个人网站是首个验证端点，最终形态是可复用到不同视频博主的互动站与平台能力。',
      tags: ['博主 Agent', '粉丝互动', '视频 RAG', '时间轴工具'],
      href: '#videos',
      featured: true,
    },
    {
      id: 'ai-tutorial-demo',
      name: 'AI 教程助手',
      stage: '已完成 Demo 闭环',
      summary: '输入教程视频链接，自动完成视频下载、关键帧抽取、AI 步骤解析，并在 Android 真机通过悬浮层和无障碍能力逐步引导操作。',
      result: '已验证“视频 → 结构化步骤 → 悬浮引导 → 用户操作确认”；OCR 后端已具备，前端精确定位仍待接入。',
      tags: ['Flutter', 'FastAPI', 'OpenAI Vision', 'EasyOCR'],
      href: '#videos',
      featured: true,
    },
    {
      id: 'cline-memory-hub',
      name: 'Cline 跨平台 AI 记忆中枢',
      stage: '已上线运行',
      summary: '跨 Trae/Claude/Codex/Cline/Cursor 多个 AI 平台的共享记忆系统，自部署在阿里云 ECS，通过 API 让不同 Agent 读写同一份记忆。',
      result: '本地快照 + 云端 SQLite 双层存储，自动同步脚本每 2 小时回写，已积累 68 个记忆文件、2.21MB。',
      tags: ['Node.js', '阿里云 ECS', 'SQLite', '多 Agent'],
      href: '#projects',
      featured: true,
    },
    {
      id: 'xianshu-game',
      name: '《献书》· 东晋历史 AI 互动叙事游戏',
      stage: 'MVP 完成',
      summary: '东晋历史题材 AI 互动叙事游戏，包含 40+ AI 视频片段、11 种结局、30+ 交互节点。用 AI 视频生成 + 分支叙事结构还原历史场景，玩家选择决定人物命运走向。',
      result: '40+ 视频片段全部生成、11 种结局分支验证通过、30+ 交互节点测试稳定。',
      tags: ['AI 视频生成', '互动叙事', '历史题材', 'RunwayML'],
      href: '#projects',
      featured: true,
    },
    {
      id: 'subnet-darkflow',
      name: 'Subnet：暗流',
      stage: '游戏设计完成',
      summary: '基于 Bittensor 的非完全信息博弈策略游戏，玩家在去中心化网络中争夺算子与信任。',
      result: '已完成游戏机制设计与博弈树分析，进入原型实现阶段。',
      tags: ['Bittensor', '策略博弈', '非完全信息', '游戏设计'],
      href: '#projects',
      featured: false,
    },
    {
      id: 'song-zhiqiu',
      name: '宋知秋 · 人物创作',
      stage: '持续创作',
      summary: '梦中少女宋知秋的人物设定、剧本、分镜与 AI 立绘，是笑咪的创作核心与精神镜像。用 AI 立绘、剧本与互动游戏构建人物，对抗遗忘、保存记忆。',
      result: '已形成完整人物设定、分镜与 AI 立绘，并接入互动游戏。',
      tags: ['AI 立绘', '人物设定', '剧本', '分镜'],
      href: '#projects',
      featured: false,
    },
    {
      id: 'ningbo-hackathon',
      name: '宁波企业定制化 AI 黑客松大赛',
      stage: '发起人 & 执行方负责人',
      summary: '面向宁波企业的定制化 AI 黑客松大赛，作为发起人和执行方负责人统筹全流程。',
      result: '覆盖赛题设计、参赛招募、技术导师、评审与落地对接。',
      tags: ['黑客松组织', '执行方', 'AI 赛事', '宁波'],
      href: '#projects',
      featured: false,
    },
    {
      id: 'aigc-workshop',
      name: 'AIGC Workshop 课程体系',
      stage: '合作中',
      summary: '与刺猬星球平台合作的 AIGC 课程体系，从入门到实战的完整教学路径。',
      result: '覆盖提示词、AI 视频、AI 应用开发等多个主题模块。',
      tags: ['AIGC 课程', '刺猬星球', '教学体系'],
      href: '#projects',
      featured: false,
    },
    {
      id: 'emerge-community',
      name: 'Emerge甬现 · 高校 AI 创新社群',
      stage: '运营中',
      summary: '运营面向高校学生的 AI 创新社群，组织分享、共学和项目孵化。',
      result: '持续招募与共学活动，连接校园与产业。',
      tags: ['高校社群', 'AI 共学', '宁波大学', '运营'],
      href: '#projects',
      featured: false,
    },
    {
      id: 'vibe-ppt',
      name: 'vibe_ppt · AI PPT 自动生成',
      stage: 'MVP 完成',
      summary: '通过提示词与模板自动生成 PPT 的工具，覆盖选题、大纲、配图与排版。',
      result: '已能根据主题一次性产出可演示的初稿。',
      tags: ['AI 生成', 'PPT', '提示词', '模板'],
      href: '#projects',
      featured: false,
    },
    {
      id: 'resume-parser',
      name: '猎头简历智能解析系统',
      stage: 'MVP 完成',
      summary: '基于 LLM 的猎头简历解析系统，从非结构化简历抽取结构化字段并打分。',
      result: '已能识别教育、经历、技能等核心字段并输出结构化结果。',
      tags: ['LLM', '简历解析', '结构化抽取'],
      href: '#projects',
      featured: false,
    },
  ],
  videos: [
    {
      id: 'device-motion-permission-demo',
      title: 'AI 教程助手：关闭设备动作方向权限',
      type: '本地竖屏演示视频',
      duration: 27,
      source: '/ai-tutorial-demo.mp4',
      summary: '展示 AI 教程助手从技能库进入系统设置，并用悬浮高亮与步骤气泡引导用户关闭设备动作方向权限。',
      tags: ['手机教程', '悬浮引导', '五步操作', '端点样例'],
      segments: [
        { id: 's1', start: 0, end: 4, title: '选择教程', summary: '在 AI 教程助手中选择解析结果并开始演示。', kind: 'hook' },
        { id: 's2', start: 4, end: 9, title: '进入隐私保护', summary: '打开手机系统设置中的隐私保护页面。', kind: 'step' },
        { id: 's3', start: 9, end: 14, title: '进入其他权限', summary: '向下滑动并点击“其他权限”。', kind: 'step' },
        { id: 's4', start: 14, end: 19, title: '打开设备动作权限', summary: '在权限列表中进入“获取设备动作与方向”权限。', kind: 'step' },
        { id: 's5', start: 19, end: 23, title: '打开更多菜单', summary: '点击页面右上角的三个点。', kind: 'step' },
        { id: 's6', start: 23, end: 27, title: '完成关闭', summary: '点击“全部拒绝”，完成操作。', kind: 'highlight' },
      ],
    },
    {
      id: 'product-direction-transcript',
      title: '视频信息转化及 AI 应用方向讨论',
      type: '2026-06-27 录音文稿',
      duration: 0,
      source: '微信录音：钟笑咪_20260627012549.aac（本次对话提供文字稿）',
      summary: '形成从视频信息复用、博主数字宠物、一对一私教，到博主与粉丝长期互动站的产品方向。',
      tags: ['产品决策', '博主分身', '私教', '粉丝互动'],
      segments: [
        { id: 'd1', start: 0, end: 0, title: '内容不是总结，而是复用', summary: '目标是把视频信息转为可直接使用的知识与技能。', kind: 'knowledge' },
        { id: 'd2', start: 0, end: 0, title: '对内分析，对外教学', summary: '对创作者是分析师和教练，对粉丝是有人味的老师与生活搭子。', kind: 'knowledge' },
        { id: 'd3', start: 0, end: 0, title: '宠物是博主入口', summary: '宠物读取博主授权内容，以博主认可的个人色彩回答并导航视频。', kind: 'highlight' },
      ],
    },
  ],
  faq: [
    {
      id: 'who',
      question: '你在做什么？',
      answer: '主人是钟笑咪，宁波大学阳明学院的学生。她在做妙喵：把博主的视频、公开信息和表达风格变成一只可聊天、可教学、可导航视频的宠物 Agent。这个个人网站只是第一阶段验证端点。她最近还在准备暑假北京实习。',
      target: 'about',
    },
    {
      id: 'goal',
      question: '最终产品是什么？',
      answer: '最终不是个人简历站，而是每个视频博主都能拥有的互动站。粉丝可以与宠物聊天、围绕视频追问、跳到具体片段，并继续发现博主的其他内容。',
      target: 'product-path',
    },
    {
      id: 'permission',
      question: '怎么关闭设备动作权限？',
      answer: '演示视频的路径是：隐私保护 → 其他权限 → 获取设备动作与方向 → 右上角三个点 → 全部拒绝。我可以直接带你到关键步骤。',
      target: 'videos',
      videoId: 'device-motion-permission-demo',
      seekTo: 9,
    },
    {
      id: 'video-navigation',
      question: '妙喵怎么理解视频？',
      answer: '视频先被拆成转写、时间片段、步骤、知识点和高光片段。回答时先检索当前视频，再检索博主全量视频库，最后返回答案、依据和播放器动作。',
      target: 'videos',
      videoId: 'device-motion-permission-demo',
      seekTo: 0,
    },
    {
      id: 'related-content',
      question: '为什么要做博主宠物？',
      answer: '产品讨论里形成的判断是：视频仍是最有吸引力的信息载体，但用户需要的不只是看完，而是直接复用、追问和与内容背后的人建立关系。妙喵把这三件事接在同一个入口里。',
      target: 'videos',
      videoId: 'product-direction-transcript',
      seekTo: 0,
    },
    {
      id: 'project',
      question: '有哪些已完成项目？',
      answer: '目前确认的项目包括妙喵博主互动 Agent、已跑通闭环的 AI 教程助手，以及跨平台 AI 记忆中枢。',
      target: 'projects',
    },
    {
      id: 'contact',
      question: '怎么联系你？',
      answer: '主人邮箱是 zhongxiaomi06@gmail.com，GitHub 是 zhongxiaomi06-sudo。合作可以发邮件，或在 GitHub 找到她的更多项目。',
      target: 'contact',
    },
    {
      id: 'diary',
      question: '最近在做什么？',
      answer: '主人最近在准备暑假北京实习，同时推进妙喵 Agent 的端点验证。每天的更新她会写在 /diary 里，我可以告诉你最近这几天她在忙什么。',
      target: 'diary',
    },
    {
      id: 'school',
      question: '主人在哪个学校？',
      answer: '主人在宁波大学阳明学院读金融工程，已经转专业成功。目前大一结束即将大二，计划提前一年在 2028 年毕业。',
      target: 'about',
    },
  ],
  links: [
    { label: '邮箱', value: 'zhongxiaomi06@gmail.com', href: 'mailto:zhongxiaomi06@gmail.com', visibility: 'public' },
    { label: 'GitHub', value: 'zhongxiaomi06-sudo', href: 'https://github.com/zhongxiaomi06-sudo', visibility: 'public' },
    { label: '数字记忆 Blog', value: 'zhongxiaomi06-sudo.github.io', href: 'https://zhongxiaomi06-sudo.github.io/my-memory/blog/', visibility: 'public' },
  ],
  sources: [
    {
      title: 'AI Tutorial Demo 技术说明文档',
      kind: 'document',
      location: '/Users/ashley/Documents/a-igent/07-a-igent技术说明文档-20260531083355.pdf',
      status: 'indexed',
      summary: '已提取产品定位、Flutter/Android/FastAPI 架构、视频理解、OCR、悬浮层和实现边界。',
    },
    {
      title: 'AI 教程助手项目名称与简介',
      kind: 'document',
      location: '/Users/ashley/Documents/a-igent/项目名称与简介-20260531083333.pdf',
      status: 'indexed',
      summary: '确认早期赛道三定位、目标人群和视频教程执行化体验。',
    },
    {
      title: '关闭设备动作方向权限演示',
      kind: 'video',
      location: '/Users/ashley/Documents/a-igent/83fa402ae9f4189e286e7d084e07bd52.mp4',
      status: 'indexed',
      summary: '26.8 秒、560×1280、HEVC/AAC；已按六个可导航片段整理。',
    },
    {
      title: '视频信息转化及 AI 应用方向讨论',
      kind: 'transcript',
      location: '本次对话提供的微信录音文字稿',
      status: 'indexed',
      summary: '已整理端点验证、博主宠物、视频私教、粉丝对话和产品最终目标。',
    },
    {
      title: '抖音精选赛道二与赛道三题目信息',
      kind: 'document',
      location: '本次对话提供的赛题原文',
      status: 'indexed',
      summary: '当前方案以赛道二“内容重构，让视频成为生活搭子”为主，个人站用于验证新的互动视频消费方式。',
    },
    {
      title: 'zero-to-website-psi.vercel.app',
      kind: 'website',
      location: 'https://zero-to-website-psi.vercel.app/',
      status: 'reference-only',
      summary: '当前运行环境无法连接，暂只作为页面框架参考来源，不把未读取内容写成事实。',
    },
    {
      title: 'AI 教程助手 Android Demo APK',
      kind: 'document',
      location: '/Users/ashley/Documents/a-igent/app-debug.apk.1',
      status: 'reference-only',
      summary: '已确认本地存在可安装构建产物；本轮未反编译，产品能力以技术文档和演示视频为依据。',
    },
  ],
  diary: [
    {
      id: 'diary_20260629',
      date: '2026-06-29',
      title: '把数字名片跑通，先以自己为端点验证',
      mood: 'focused',
      weather: '多云',
      location: '浙江 · 宁波',
      summary: '今天专注把个人网站从静态介绍页升级成持续更新的数字名片，并新增了日记模块。',
      body: '## 今天在做什么\n\n把数据结构文档完整落地，新增 `diary_entries` 表，让数字名片从静态介绍页变成持续在更新的人。\n\n关键改动：\n- schema 加 `diary_entries` 表与索引\n- 后端 repository/service/api 加 diary CRUD\n- 用真实数据替换 seed 中的占位（姓名、邮箱、学校、12 个项目）\n- 加 `/diary` 前端页面\n\n## 为什么\n\n妙喵被问『最近在做什么』时，目前只能回退到 FAQ。有了日记，她可以直接回答『昨天主人在准备北京实习面试』这种问题，让博主不再是一张静态名片，而是『持续在更新的人』。',
      tags: ['数字名片', '日记模块', '妙喵', '端点验证'],
      links: [
        { type: 'project', id: 'miaomiao-creator-agent', label: '妙喵 Agent' },
        { type: 'project', id: 'cline-memory-hub', label: 'Cline 记忆中枢' },
      ],
      highlights: ['schema 加 diary_entries 表', '后端 CRUD 完成', 'seed 数据真实化'],
      pinned: true,
    },
    {
      id: 'diary_20260628',
      date: '2026-06-28',
      title: '和 codex 梳理妙喵 Agent 的开发文档与数据结构',
      mood: 'excited',
      weather: '晴',
      location: '浙江 · 宁波',
      summary: '和 codex 把赛道二开发文档和数据结构文档重写成个人网站数字名片版，架构围绕我的网站展开。',
      body: '## 今天在做什么\n\n和 codex 一起重写了两份文档：\n- 《妙喵私教-赛道二开发文档》\n- 《个人网站数字名片-数据结构》\n\n核心收敛：**个人网站只是端点验证，最终产品是为每位视频博主生成一只宠物 Agent**。\n\n三模式共享一只猫：视频问答导览、视频私教、陪聊互动。不做成三个割裂页面。\n\n## 关键决策\n\n- 站里有博主桌宠「妙喵」，承接互动/问答/导流/记忆\n- 沉淀博主全部可展示数据\n- 数据分四层：公开 / 半公开 / 私域 / 受控',
      tags: ['妙喵', '开发文档', '数据结构', '赛道二', 'codex'],
      links: [
        { type: 'project', id: 'miaomiao-creator-agent', label: '妙喵 Agent' },
      ],
      highlights: ['重写两份文档', '确定端点验证路线', '确定四层数据分层'],
      pinned: false,
    },
    {
      id: 'diary_20260622',
      date: '2026-06-22',
      title: '复习量化金融与 Python，准备北京实习面试',
      mood: 'focused',
      weather: '雨',
      location: '浙江 · 宁波',
      summary: '今天主要复习量化金融和 Python/FastAPI，准备即将到来的北京实习面试。',
      body: '## 今天在做什么\n\n- 上午：复习量化金融基础，重点过 portfolio optimization 和 time series\n- 下午：刷 Python/FastAPI 题，准备实习面试的技术栈补齐\n- 晚上：整理 Cline 记忆中枢的同步脚本\n\n## 想法\n\n短期目标是大二修完全部学分 + 大三字节实习。今天复习的时候意识到，量化金融和 AI 应用开发其实是同一种思维方式——都是在不确定中找模式。\n\nCline 记忆中枢现在已经有 68 个文件，2.21MB，是我跨平台工作的真正底座。',
      tags: ['量化金融', 'Python', 'FastAPI', '北京实习', '面试准备'],
      links: [
        { type: 'project', id: 'cline-memory-hub', label: 'Cline 记忆中枢' },
      ],
      highlights: ['复习 portfolio optimization', '刷 FastAPI 题', '整理同步脚本'],
      pinned: false,
    },
    {
      id: 'diary_20260615',
      date: '2026-06-15',
      title: '《献书》互动叙事游戏 MVP 收尾',
      mood: 'proud',
      weather: '晴',
      location: '浙江 · 宁波',
      summary: '今天把《献书》的 MVP 收尾，40+ AI 视频片段和 11 种结局全部跑通。',
      body: '## 今天在做什么\n\n《献书》东晋历史 AI 互动叙事游戏的 MVP 收尾。\n\n- 40+ AI 视频片段全部生成完毕\n- 11 种结局分支验证通过\n- 30+ 交互节点测试稳定\n\n## 想法\n\n用 AI 视频生成还原历史场景，玩家选择决定人物命运走向。这其实和我做妙喵的逻辑是通的——让内容不再只是被看，而是被『复用』和『对话』。\n\n宋知秋也是这条线上的：用 AI 立绘、剧本、互动游戏构建人物，对抗遗忘。**记忆就是一切**。',
      tags: ['献书', 'AI 视频', '互动叙事', '东晋', '宋知秋'],
      links: [
        { type: 'project', id: 'xianshu-game', label: '《献书》' },
        { type: 'project', id: 'song-zhiqiu', label: '宋知秋' },
      ],
      highlights: ['40+ 视频片段完成', '11 种结局验证', '30+ 交互节点测试'],
      pinned: false,
    },
    {
      id: 'diary_20260610',
      date: '2026-06-10',
      title: '宁波黑客松筹备 + Emerge甬现社群运营',
      mood: 'tired',
      weather: '多云',
      location: '浙江 · 宁波大学',
      summary: '今天统筹宁波企业定制化 AI 黑客松的赛题设计，同时运营 Emerge甬现高校社群。',
      body: '## 今天在做什么\n\n双线工作：\n\n- 上午：宁波企业定制化 AI 黑客松的赛题设计、参赛招募方案\n- 下午：Emerge甬现高校 AI 创新社群的共学活动组织\n- 晚上：和刺猬星球对接 AIGC Workshop 课程内容\n\n## 想法\n\n作为发起人和执行方负责人统筹黑客松，覆盖赛题设计、参赛招募、技术导师、评审与落地对接——这是真正的项目执行训练。\n\n社群运营让我更理解『创作者需要什么』，这其实是妙喵 Agent 的真实需求来源。',
      tags: ['黑客松', 'Emerge甬现', '社群运营', 'AIGC Workshop', '宁波大学'],
      links: [
        { type: 'project', id: 'ningbo-hackathon', label: '宁波黑客松' },
        { type: 'project', id: 'emerge-community', label: 'Emerge甬现' },
        { type: 'project', id: 'aigc-workshop', label: 'AIGC Workshop' },
      ],
      highlights: ['赛题设计完成', '共学活动组织', '刺猬星球对接'],
      pinned: false,
    },
    {
      id: 'diary_20260601',
      date: '2026-06-01',
      title: '转专业成功，金融工程，目标 2028 提前毕业',
      mood: 'proud',
      weather: '晴',
      location: '浙江 · 宁波大学',
      summary: '今天确认转专业到金融工程成功，下一步是大二修完全部学分，目标 2028 年提前一年毕业。',
      body: '## 今天在做什么\n\n- 上午：办理转专业手续，确认进入金融工程\n- 下午：规划大二课程，目标修完全部学分\n- 晚上：更新数字记忆 about.json\n\n## 关键决策\n\n短期：北京实习面试准备 + 技术栈补齐\n中期：大二修完全部学分 + 大三字节实习\n长期：大学毕业创业 → 援助非洲\n\n## 想法\n\n转专业到金融工程，是因为它和量化、和 AI 都是『在不确定中找模式』。提前一年毕业是为了把时间留给真正重要的事——创业和创造。\n\n记忆要握在自己手里。GitHub 私有仓库 + 本地 clone，才是我自己的。',
      tags: ['转专业', '金融工程', '宁波大学', '提前毕业', '2028'],
      links: [
        { type: 'project', id: 'emerge-community', label: 'Emerge甬现' },
      ],
      highlights: ['转专业成功', '大二课程规划', '更新 about.json'],
      pinned: false,
    },
  ],
}

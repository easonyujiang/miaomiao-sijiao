PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  initials TEXT,
  role TEXT,
  location TEXT,
  status TEXT,
  tagline TEXT NOT NULL,
  summary TEXT NOT NULL,
  avatar_url TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pet_personas (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  greeting TEXT NOT NULL,
  traits_json TEXT NOT NULL DEFAULT '[]',
  style_rules_json TEXT NOT NULL DEFAULT '{}',
  safety_rules_json TEXT NOT NULL DEFAULT '{}',
  avatar_url TEXT,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  slug TEXT NOT NULL,
  name TEXT NOT NULL,
  stage TEXT,
  summary TEXT NOT NULL,
  body TEXT,
  cover_url TEXT,
  external_url TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  visibility TEXT NOT NULL DEFAULT 'public'
    CHECK (visibility IN ('public', 'unlisted', 'private', 'restricted')),
  is_featured INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (profile_id, slug),
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS faqs (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  intent TEXT NOT NULL DEFAULT 'general',
  target_section TEXT,
  keywords_json TEXT NOT NULL DEFAULT '[]',
  sources_json TEXT NOT NULL DEFAULT '[]',
  actions_json TEXT NOT NULL DEFAULT '[]',
  visibility TEXT NOT NULL DEFAULT 'public'
    CHECK (visibility IN ('public', 'unlisted', 'private', 'restricted')),
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile_links (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  url TEXT NOT NULL,
  link_type TEXT NOT NULL DEFAULT 'other',
  visibility TEXT NOT NULL DEFAULT 'public'
    CHECK (visibility IN ('public', 'unlisted', 'private', 'restricted')),
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_sources (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('document', 'video', 'audio', 'transcript', 'website', 'manual')),
  title TEXT NOT NULL,
  location TEXT NOT NULL,
  ingest_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (ingest_status IN ('pending', 'indexed', 'reference_only', 'failed')),
  checksum TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  extracted_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS videos (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  source_id TEXT,
  platform TEXT NOT NULL DEFAULT 'local',
  platform_video_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  source_url TEXT,
  local_ref TEXT,
  poster_url TEXT,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  published_at TEXT,
  transcript_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (transcript_status IN ('pending', 'processing', 'ready', 'failed', 'manual')),
  visibility TEXT NOT NULL DEFAULT 'public'
    CHECK (visibility IN ('public', 'unlisted', 'private', 'restricted')),
  tags_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (source_id) REFERENCES knowledge_sources(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS video_segments (
  id TEXT PRIMARY KEY,
  video_id TEXT NOT NULL,
  start_ms INTEGER NOT NULL,
  end_ms INTEGER NOT NULL,
  segment_type TEXT NOT NULL DEFAULT 'knowledge'
    CHECK (segment_type IN ('hook', 'knowledge', 'step', 'highlight', 'answer', 'other')),
  title TEXT NOT NULL,
  transcript TEXT,
  summary TEXT NOT NULL,
  steps_json TEXT NOT NULL DEFAULT '[]',
  tags_json TEXT NOT NULL DEFAULT '[]',
  fun_score REAL,
  embedding_ref TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (start_ms >= 0 AND end_ms >= start_ms),
  FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS video_relations (
  id TEXT PRIMARY KEY,
  from_video_id TEXT NOT NULL,
  to_video_id TEXT NOT NULL,
  relation_type TEXT NOT NULL CHECK (relation_type IN ('related', 'prerequisite', 'follow_up', 'same_series', 'creator_pick')),
  reason TEXT,
  score REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (from_video_id, to_video_id, relation_type),
  FOREIGN KEY (from_video_id) REFERENCES videos(id) ON DELETE CASCADE,
  FOREIGN KEY (to_video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS creator_style_examples (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  source_id TEXT,
  example_type TEXT NOT NULL CHECK (example_type IN ('opening', 'explanation', 'humor', 'transition', 'closing', 'boundary')),
  content TEXT NOT NULL,
  approved INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (source_id) REFERENCES knowledge_sources(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS content_chunks (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  summary TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  evidence_url TEXT,
  start_seconds REAL,
  end_seconds REAL,
  visibility TEXT NOT NULL DEFAULT 'public'
    CHECK (visibility IN ('public', 'unlisted', 'private', 'restricted')),
  embedding_ref TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS visitors (
  id TEXT PRIMARY KEY,
  anonymous_key TEXT NOT NULL UNIQUE,
  consent_memory INTEGER NOT NULL DEFAULT 0 CHECK (consent_memory IN (0, 1)),
  first_source TEXT,
  first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS visitor_sessions (
  id TEXT PRIMARY KEY,
  visitor_id TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  source TEXT,
  landing_path TEXT,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TEXT,
  FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS viewer_video_progress (
  visitor_id TEXT NOT NULL,
  video_id TEXT NOT NULL,
  last_position_ms INTEGER NOT NULL DEFAULT 0,
  completed_segments_json TEXT NOT NULL DEFAULT '[]',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (visitor_id, video_id),
  FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE,
  FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversation_messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('visitor', 'pet', 'system', 'tool')),
  content TEXT NOT NULL,
  intent TEXT,
  sources_json TEXT NOT NULL DEFAULT '[]',
  actions_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES visitor_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS visitor_events (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  section_id TEXT,
  target_id TEXT,
  payload_json TEXT NOT NULL DEFAULT '{}',
  occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES visitor_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS visitor_memories (
  id TEXT PRIMARY KEY,
  visitor_id TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  memory_key TEXT NOT NULL,
  memory_value TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
  expires_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (visitor_id, profile_id, memory_key),
  FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_actions (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL,
  action_type TEXT NOT NULL,
  target_id TEXT,
  arguments_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK (status IN ('proposed', 'executed', 'cancelled', 'failed')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  executed_at TEXT,
  FOREIGN KEY (message_id) REFERENCES conversation_messages(id) ON DELETE CASCADE
);

-- 日记模块：博主每日在做什么、想了什么、做了什么
-- 与视频、项目、FAQ 并列，构成"持续在更新的人"的数字名片
CREATE TABLE IF NOT EXISTS diary_entries (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  entry_date TEXT NOT NULL,                 -- YYYY-MM-DD，博主当天日期
  title TEXT NOT NULL,                      -- 当日主题一句话
  mood TEXT,                                -- 情绪/状态：focused / excited / tired / curious / proud ...
  weather TEXT,                             -- 天气简述，可选
  location TEXT,                            -- 当天所在地，可选
  summary TEXT NOT NULL,                    -- 当日一句话总结（首页/卡片用）
  body TEXT NOT NULL,                       -- 日记正文（Markdown）
  tags_json TEXT NOT NULL DEFAULT '[]',     -- 当日关键词
  links_json TEXT NOT NULL DEFAULT '[]',    -- 当日关联：项目/视频/外链 [{type,id?,label,url?}]
  highlights_json TEXT NOT NULL DEFAULT '[]', -- 当日完成的关键事项
  visibility TEXT NOT NULL DEFAULT 'public'
    CHECK (visibility IN ('public', 'unlisted', 'private', 'restricted')),
  is_pinned INTEGER NOT NULL DEFAULT 0 CHECK (is_pinned IN (0, 1)),
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (profile_id, entry_date),
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_projects_profile_sort
  ON projects(profile_id, is_featured DESC, sort_order ASC);
CREATE INDEX IF NOT EXISTS idx_faqs_profile_intent
  ON faqs(profile_id, intent, sort_order ASC);
CREATE INDEX IF NOT EXISTS idx_chunks_profile_source
  ON content_chunks(profile_id, source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_sources_profile_status
  ON knowledge_sources(profile_id, ingest_status, source_type);
CREATE INDEX IF NOT EXISTS idx_videos_profile_published
  ON videos(profile_id, visibility, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_segments_video_time
  ON video_segments(video_id, start_ms ASC, end_ms ASC);
CREATE INDEX IF NOT EXISTS idx_relations_from_score
  ON video_relations(from_video_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_style_profile_approved
  ON creator_style_examples(profile_id, approved, example_type);
CREATE INDEX IF NOT EXISTS idx_sessions_visitor_started
  ON visitor_sessions(visitor_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_created
  ON conversation_messages(session_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_events_session_type
  ON visitor_events(session_id, event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_visitor_profile
  ON visitor_memories(visitor_id, profile_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_diary_profile_date
  ON diary_entries(profile_id, entry_date DESC, sort_order ASC);
CREATE INDEX IF NOT EXISTS idx_diary_profile_pinned
  ON diary_entries(profile_id, is_pinned DESC, entry_date DESC);

-- ============================================================
-- Lesson / Quiz 模块 — 私教答题学习状态
-- ============================================================

CREATE TABLE IF NOT EXISTS lesson_sessions (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  lesson_id TEXT NOT NULL,
  video_id TEXT,
  current_step_index INTEGER NOT NULL DEFAULT 0,
  total_stars INTEGER NOT NULL DEFAULT 0,
  fish INTEGER NOT NULL DEFAULT 0,
  growth INTEGER NOT NULL DEFAULT 0,
  step_results_json TEXT NOT NULL DEFAULT '{}',
  review_queue_json TEXT NOT NULL DEFAULT '[]',
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lesson_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  step_id TEXT NOT NULL,
  attempt_num INTEGER NOT NULL DEFAULT 1,
  answer TEXT NOT NULL,
  score REAL NOT NULL DEFAULT 0,
  matched_count INTEGER NOT NULL DEFAULT 0,
  required_count INTEGER NOT NULL DEFAULT 0,
  passed INTEGER NOT NULL DEFAULT 0 CHECK (passed IN (0, 1)),
  stars_earned INTEGER NOT NULL DEFAULT 0,
  cat_message TEXT,
  missed_points_json TEXT NOT NULL DEFAULT '[]',
  wrong_points_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES lesson_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lesson_sessions_lesson
  ON lesson_sessions(profile_id, lesson_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_lesson_attempts_session
  ON lesson_attempts(session_id, step_id, attempt_num DESC);

-- ============================================================
-- 管理后台 — 审计日志
-- ============================================================

CREATE TABLE IF NOT EXISTS admin_audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  level TEXT NOT NULL,
  module TEXT NOT NULL,
  action TEXT NOT NULL,
  table_name TEXT,
  record_id TEXT,
  detail TEXT,
  ip TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp
  ON admin_audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_level_module
  ON admin_audit_log(level, module);

-- ============================================================
-- 共创社区模块
-- ============================================================

CREATE TABLE IF NOT EXISTS community_topics (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'discussion'
    CHECK (category IN ('question', 'discussion', 'showcase', 'feedback', 'other')),
  author_name TEXT NOT NULL DEFAULT '匿名用户',
  tags_json TEXT NOT NULL DEFAULT '[]',
  video_id TEXT,
  view_count INTEGER NOT NULL DEFAULT 0,
  reply_count INTEGER NOT NULL DEFAULT 0,
  like_count INTEGER NOT NULL DEFAULT 0,
  is_pinned INTEGER NOT NULL DEFAULT 0 CHECK (is_pinned IN (0, 1)),
  is_resolved INTEGER NOT NULL DEFAULT 0 CHECK (is_resolved IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS community_replies (
  id TEXT PRIMARY KEY,
  topic_id TEXT NOT NULL,
  parent_reply_id TEXT,
  author_name TEXT NOT NULL DEFAULT '匿名用户',
  content TEXT NOT NULL,
  is_pet_reply INTEGER NOT NULL DEFAULT 0 CHECK (is_pet_reply IN (0, 1)),
  like_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (topic_id) REFERENCES community_topics(id) ON DELETE CASCADE,
  FOREIGN KEY (parent_reply_id) REFERENCES community_replies(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_topics_profile_category
  ON community_topics(profile_id, category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_topics_pinned
  ON community_topics(profile_id, is_pinned DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_replies_topic
  ON community_replies(topic_id, created_at ASC);

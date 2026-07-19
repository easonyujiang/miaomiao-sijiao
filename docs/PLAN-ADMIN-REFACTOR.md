# 管理后端重构计划

> 2026-07-20 创建。目标：管理后端从"通用 CRUD 工具"升级为"网站 + 插件的完整管理台"。

## 现状问题

1. **三条数据通道无统一管理**：新视频上线要分别操作 videos 表（DB）、字幕 JSON（文件）、课程 JSON（文件），这次线上"罗翔视频查不到"就是漏了 DB 行
2. 通用 CRUD 只管 DB，文件资产（字幕/课程/scored_videos）完全不可见
3. `import/video` 的课程目录硬编码相对路径，不走 `config.LESSONS_DIR`
4. Bearer 校验用 `replace` 不严格；token 明文比较
5. admin 模块零测试；学习数据（lesson_sessions/attempts）只能看裸表

## 目标架构

```
/api/admin/
├─ 保留：通用 CRUD /{table}、/stats、/schema、/logs/list   ← SPA 现有功能不破坏
├─ 保留但修正：POST /import/video（路径改走 config）
├─ 新增 assets/        视频资产三通道统一管理（Part 1）
│   ├─ GET    /assets/videos             合并视图：DB 行 + 字幕 + 课程 + 片段数，缺啥一目了然
│   ├─ POST   /assets/videos             一站式上线：video + segments + subtitle + lesson（幂等 upsert）
│   ├─ GET    /assets/videos/{id}        单视频三通道详情 + 校验状态
│   ├─ PUT    /assets/videos/{id}/subtitle   上传/替换字幕 JSON（格式校验）
│   ├─ PUT    /assets/videos/{id}/lesson     上传/替换课程 JSON（格式校验）
│   └─ DELETE /assets/videos/{id}        删除视频及全部关联（行/片段/字幕文件/课程文件）
├─ 新增 extension/     插件侧管理（Part 2）
│   ├─ GET /extension/lessons            课程文件清单 + steps 校验
│   └─ GET /extension/learning           学习数据聚合视图（session × attempts × 通过率）
└─ 新增 GET /overview  管理台首页：统计 + 资产健康 + 最近审计（Part 2）
```

SPA 前端（Part 3）：新增"视频资产"页（三通道状态 + 上传表单），其余页面不变。

## 分期实施

| 期 | 内容 | 状态 |
|---|---|---|
| Part 1 | `admin/assets.py` 资产服务层 + `/assets/*` 路由 + auth 加固 + config 路径修正 + 测试 | ✅ 2026-07-20 |
| Part 2 | `/extension/lessons`、`/extension/learning`、`/overview` | 待做 |
| Part 3 | SPA 新增视频资产页 | 待做 |
| Part 4 | 文档同步（README/PROGRESS/SERVER-DEPLOYMENT） | 待做 |

## Part 1 设计要点

- **AssetService 目录可注入**：`AssetService(subtitle_dir=, lessons_dir=)` 默认取 config，测试传临时目录，避免污染环境变量
- **字幕格式校验**：必须有 `subtitles` 数组，每项含非空 `text`，`start`/`end` 为数字且 end > start
- **课程格式校验**：必须有 `id`、`video_id`、非空 `steps`；steps 含 `id/question/start_ms/end_ms`
- **upsert 语义**：video 行存在则 UPDATE 否则 INSERT；segments 全量替换（先删后插，同事务）；字幕/课程给了才写文件
- **路由注册顺序**：`/assets/*` 必须放在通用 `/{table}/{row_id}` 之前，否则被泛化路由截胡
- **auth 加固**：严格 `Bearer ` 前缀判断 + `secrets.compare_digest` 时序安全比较

## 不做

- 多用户/角色权限（单博主 Demo，一个 ADMIN_TOKEN 够用）
- 前端框架化（SPA 维持 vanilla JS 单文件）
- 文件资产的版本历史（覆盖即覆盖，git 管版本）

# 妙喵私教 · 测试指南

## 1. 环境

```bash
cd ewa
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env   # 填入 LLM API Key
```

## 2. 启动后端

```bash
python run.py
# → 妙喵私教 ready. DB: data/miaomiao.db
```

```bash
curl http://localhost:8000/health
# → {"status":"ok","site":{"seeded":true}}
```

## 3. Chrome 插件

1. Chrome → `chrome://extensions/` → 开发者模式
2. 「加载已解压的扩展程序」→ 选择 `extension/` 目录
3. 打开 `https://www.bilibili.com/video/BV1mJ4m147PG`
4. F12 Console 过滤 `[妙喵]` → 应看到「课程已加载」
5. 右下角 🐱 气泡 → 点击 → 面板弹出 → 开始学习
6. 走完 5 关答题 → 验证评分、纠错、进度持久化

## 4. 管理后台

```
http://localhost:8000/admin
输入 Token: admin-secret-change-me
```

验证：
- 仪表盘：21 表统计
- 表管理：列表 / 搜索 / 分页 / 新增 / 编辑 / 删除
- 导入视频：填写信息 + 片段 + 课程 → 提交
- 审计日志：查看操作记录

## 5. 前端网站

```bash
cd frontend && npm install && npm run dev
# → http://localhost:3000
```

验证：
- `/` 首页 → 博主信息、项目、视频
- `/diary` → 日记时间线
- `/projects` → 项目 + 视频片段
- `/community` → 社区话题（建设中提示）
- 右下角 🐱 → 聊天对话

## 6. 社区 API

```bash
# 创建话题
curl -X POST http://localhost:8000/api/community/topics \
  -H "Content-Type: application/json" \
  -d '{"title":"测试","content":"内容","author_name":"Test"}'

# 列表
curl http://localhost:8000/api/community/topics

# 回复
curl -X POST http://localhost:8000/api/community/topics/{id}/replies \
  -H "Content-Type: application/json" \
  -d '{"content":"回复","author_name":"Test"}'
```

## 7. 自动化测试

```bash
pytest tests/ -v
```

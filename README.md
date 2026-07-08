# 妙喵私教

把教学视频变成一对一私教。

在 B站/抖音视频页注入 🐱 猫咪私教：看片段 → 答案例题 → AI 判卷纠错 → 跳回讲解 → 下一关。

---

## 项目结构

```
ewa/
├── run.py                     # 启动入口
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
│
├── ewa/                       # 后端 (Python/FastAPI)
│   ├── config.py
│   ├── api/
│   │   ├── main.py            # 应用入口 + 网站 API
│   │   ├── lesson.py          # 私教 API (答题评分/持久化/LLM)
│   │   └── ext.py             # 插件 API (视频问答/离线回退)
│   └── site/
│       ├── repository.py      # SQLite 数据层 + 种子数据
│       ├── service.py         # 业务逻辑
│       └── api.py             # REST 路由
│
├── extension/                 # Chrome 插件 (MV3)
│   ├── manifest.json
│   ├── content_script.js      # 视频页注入 + 气泡 + 答题面板
│   ├── content_style.css
│   ├── background.js
│   └── assets/
│
├── frontend/                  # Next.js 博主网站
│   ├── app/                   # Home/Blog/Projects/Diary/Resume
│   └── components/            # PetAssistant 猫咪对话窗等
│
├── data/miaomiao/
│   ├── lessons/               # 课程 JSON (5 关练习)
│   └── subtitles/             # B站字幕 JSON
│
├── tests/
│   ├── test_lesson_e2e.py     # 私教全流程 (21 cases)
│   └── test_site_api.py       # 网站 API (2 cases)
│
└── docs/
    ├── TEST-GUIDE.md          # 测试与运行指南
    ├── DEMO-RUNBOOK.md        # 比赛演示脚本
    └── schema.sql             # 数据库结构 (17 表)
```

## 快速启动

```bash
cd ewa

# 安装
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e ".[dev]"

# 配置 (无 Key 也能跑，自动用离线模式)
cp .env.example .env

# 启动
python run.py
# → 妙喵私教 ready. DB: data/miaomiao.db
```

## 验证

```bash
# 健康检查
curl http://localhost:8000/health

# 一键跑通 5 关
python -c "
import json
from ewa.api.main import create_app
from fastapi.testclient import TestClient

with open('data/miaomiao/lessons/lesson_luoxiang_001.json', encoding='utf-8') as f:
    lesson = json.load(f)

answers = {
    'step_1': '不成立，这是假想防卫的情形，客观上没有现实的不法侵害，属于事实认识错误',
    'step_2': '现场追回属于正当防卫，侵害仍在进行。第二天打伤不成立，属于事后报复。',
    'step_3': '反击侵害人是防卫行为，是合法的。误伤旁边的路人不是故意的，可以按紧急情况处理。',
    'step_4': '这是挑拨防卫，故意激怒对方然后反击，不成立防卫。互殴中一方停止后可成立防卫。',
    'step_5': '属于特殊防卫，针对严重危及人身安全的暴力犯罪，适用无限防卫权。',
}

app = create_app()
with TestClient(app) as c:
    for step in lesson['steps']:
        r = c.post('/api/lesson/quiz_submit', json={
            'session_id':'demo','lesson_id':'lesson_luoxiang_001',
            'step_id':step['id'],'answer':answers[step['id']],
            'current_time_sec':step['start_ms']//1000,
        })
        d = r.json()
        print(f'{\"PASS\" if d[\"passed\"] else \"FAIL\"} {step[\"id\"]} | score={d[\"score\"]} stars={d[\"stars_earned\"]}')

    state = c.get('/api/lesson/state/demo/lesson_luoxiang_001').json()
    g = state['gamification']
    print(f'DONE | stars={g[\"total_stars\"]} fish={g[\"fish\"]} growth={g[\"growth\"]}')
"

# 全部测试
pytest tests/ -v
```

## 加载 Chrome 插件

1. Chrome → `chrome://extensions/`
2. 开启「开发者模式」
3. 「加载已解压的扩展程序」→ 选择 `extension/` 目录
4. 打开 B站视频 `BV1mJ4m147PG` → 右下角 🐱 气泡出现

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /api/site/{slug}` | 博主全量数据 |
| `POST /api/site/{slug}/chat` | 猫咪 FAQ 问答 |
| `POST /api/ext/register_video` | 注册视频 + 字幕匹配 |
| `POST /api/ext/chat` | 视频时间戳问答 (LLM+离线回退) |
| `POST /api/lesson/load` | 加载课程 |
| `POST /api/lesson/quiz_submit` | 提交作答 (关键词+LLM评分) |
| `GET /api/lesson/state/{session}/{lesson}` | 学习状态 |
| `POST /api/lesson/next_step` | 推进下一步 |

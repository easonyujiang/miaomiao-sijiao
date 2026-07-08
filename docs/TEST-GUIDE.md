# 妙喵私教 · 运行与测试指南

## 1. 安装依赖

```bash
cd ewa

# 首次创建虚拟环境
python -m venv .venv

# 激活
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 安装
pip install -e ".[dev]"
```

## 2. 配置

```bash
cp .env.example .env
```

不配置 LLM Key 也能跑，自动使用离线模式。

配置任意一个 Key 可获得更好的 LLM 判卷体验：

```bash
MOONSHOT_API_KEY=sk-...     # 首选
DEEPSEEK_API_KEY=sk-...     # 备选
```

## 3. 启动后端

```bash
python run.py
```

看到 `妙喵私教 ready. DB: data/miaomiao.db` 即启动成功。

## 4. 验证 API

```bash
# 健康检查
curl http://localhost:8000/health
# → {"status":"ok","site":{"profiles":true},...}

# 加载课程
curl -s -X POST http://localhost:8000/api/lesson/load \
  -H "Content-Type: application/json" \
  -d '{"video_id":"BV1mJ4m147PG","platform":"bilibili"}' \
  | python -c "import sys,json; d=json.load(sys.stdin); print(d['title'], d['total_steps'], 'steps')"
# → 正当防卫的构成要件 — 罗翔刑法 5 steps

# 提交第 1 关
curl -s -X POST http://localhost:8000/api/lesson/quiz_submit \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"test",
    "lesson_id":"lesson_luoxiang_001",
    "step_id":"step_1",
    "answer":"不成立，这是假想防卫的情形，客观上没有现实的不法侵害，属于事实认识错误",
    "current_time_sec":60
  }' | python -c "import sys,json; d=json.load(sys.stdin); print('PASS' if d['passed'] else 'FAIL', 'stars', d['stars_earned'])"
# → PASS stars 3

# 查看状态
curl -s http://localhost:8000/api/lesson/state/test/lesson_luoxiang_001 \
  | python -c "import sys,json; d=json.load(sys.stdin); print('stars', d['gamification']['total_stars'])"
# → stars 3
```

## 5. 一键跑通 5 关

```bash
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
            'session_id':'full_run',
            'lesson_id':'lesson_luoxiang_001',
            'step_id':step['id'],
            'answer':answers[step['id']],
            'current_time_sec':step['start_ms']//1000,
        })
        d = r.json()
        print(f'{\"PASS\" if d[\"passed\"] else \"FAIL\"} {step[\"id\"]} | score={d[\"score\"]} stars={d[\"stars_earned\"]}')

    state = c.get('/api/lesson/state/full_run/lesson_luoxiang_001').json()
    g = state['gamification']
    print(f'DONE | stars={g[\"total_stars\"]} fish={g[\"fish\"]} growth={g[\"growth\"]}')
"
```

预期输出：

```
PASS step_1 | score=0.8 stars=3
PASS step_2 | score=1.0 stars=3
PASS step_3 | score=0.75 stars=3
PASS step_4 | score=0.8 stars=3
PASS step_5 | score=0.667 stars=3
DONE | stars=15 fish=15 growth=50
```

## 6. 加载 Chrome 插件

1. Chrome → `chrome://extensions/`
2. 开启右上角「开发者模式」
3. 「加载已解压的扩展程序」→ 选择 `extension/` 目录
4. 打开 B站视频 `https://www.bilibili.com/video/BV1mJ4m147PG`
5. 右下角出现 🐱 气泡 → 点击 → 开始学习

> 如果气泡半透明：后端未连接，确认 `python run.py` 运行中。
> 如果气泡不出现：F12 → Console → 过滤 `[妙喵]` 查看日志。

## 7. 运行全部测试

```bash
# 所有测试 (23 cases)
pytest tests/ -v

# 只跑私教流程
pytest tests/test_lesson_e2e.py -v

# 只跑网站 API
pytest tests/test_site_api.py -v

# 代码检查
ruff check .
```

## 8. 手动评分测试

```bash
python -c "
from ewa.api.lesson import score_answer

answer_key = ['不构成正当防卫', '不存在不法侵害', '假想防卫', '没有现实的不法侵害', '事实认识错误']
wrong_key = ['构成正当防卫', '防卫过当', '紧急避险']

tests = [
    ('不成立，这是假想防卫，客观上没有现实的不法侵害，属于事实认识错误', '正确回答'),
    ('构成正当防卫，是防卫过当', '错误回答'),
    ('', '空回答'),
    ('假想防卫', '太短'),
]
for a, desc in tests:
    r = score_answer(a, answer_key, wrong_key)
    print(f'{desc}: score={r[\"score\"]} matched={r[\"matched\"]} wrong={r[\"wrong_hits\"]}')
"
```

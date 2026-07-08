# 妙喵私教 · 一键跑通指南

从零启动，走完完整 DEMO 流程。

---

## 第一步：安装依赖

```bash
cd ewa

# 创建虚拟环境（首次）
python -m venv .venv

# 激活（Windows Git Bash）
source .venv/Scripts/activate

# 安装后端
pip install -e ".[dev]"

# 安装前端（如需要前端网站）
cd frontend && npm install && cd ..
```

## 第二步：配置 LLM Key（可选）

```bash
# 没有 Key 也能跑——会自动使用离线 FAQ 模式
cp .env.example .env
# 编辑 .env，填入任意一个 Key：
#   MOONSHOT_API_KEY=sk-...     (推荐)
#   DEEPSEEK_API_KEY=sk-...     (备选)
```

## 第三步：启动后端

```bash
python run.py
# 看到这行就成功了 →
# 妙喵私教 ready. DB: data/miaomiao.db
```

## 第四步：加载 Chrome Extension

```
1. 打开 Chrome
2. 地址栏输入 chrome://extensions/
3. 打开右上角「开发者模式」
4. 点击「加载已解压的扩展程序」
5. 选择 extension/ 文件夹
```

## 第五步：验证跑通

打开新终端，不用停后端：

```bash
cd ewa
source .venv/Scripts/activate

# 验证后端健康
curl http://localhost:8000/health
# → {"status":"ok","site":{...},"timestamp":"..."}

# 加载课程（5关）
curl -X POST http://localhost:8000/api/lesson/load \
  -H "Content-Type: application/json" \
  -d '{"video_id":"BV1mJ4m147PG","platform":"bilibili"}'
# → {"lesson_id":"lesson_luoxiang_001","total_steps":5,...}

# 提交第1关答题
curl -X POST http://localhost:8000/api/lesson/quiz_submit \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"my_demo",
    "lesson_id":"lesson_luoxiang_001",
    "step_id":"step_1",
    "answer":"不成立，这是假想防卫的情形，客观上没有现实的不法侵害，属于事实认识错误",
    "current_time_sec":60
  }'
# → {"passed":true,"score":0.8,"stars_earned":3,...}

# 查看学习状态
curl http://localhost:8000/api/lesson/state/my_demo/lesson_luoxiang_001
# → {"completed_steps":["step_1"],"gamification":{"total_stars":3,...},...}
```

## 一键跑完 5 关

```bash
cd ewa
source .venv/Scripts/activate

python -c "
import sys, json; sys.path.insert(0,'.')
from ewa.api.main import create_app
from fastapi.testclient import TestClient

with open('data/miaomiao/lessons/lesson_luoxiang_001.json', encoding='utf-8') as f:
    lesson = json.load(f)

# 每关的正确答案（避开 wrong_key 子串）
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
        icon = 'PASS' if d['passed'] else 'FAIL'
        print(f'{icon} {step[\"id\"]}: score={d[\"score\"]} matched={d[\"matched_count\"]}/{d[\"required_count\"]} stars={d[\"stars_earned\"]}')

    state = c.get('/api/lesson/state/full_run/lesson_luoxiang_001').json()
    g = state['gamification']
    print(f'DONE stars={g[\"total_stars\"]} fish={g[\"fish\"]} growth={g[\"growth\"]}')
"
```

## 在 B站视频页测试 Extension

```
# 确保后端在 localhost:8000 运行中
# 已加载 extension/ 到 Chrome

1. 打开 B站视频：https://www.bilibili.com/video/BV1mJ4m147PG
2. 看右下角 → 🐱 气泡出现
3. 点击气泡 → 展开面板 → 开始学习
4. 按 F12 → Console → 过滤 [妙喵] 查看日志
```

## 常见问题

| 现象 | 解决 |
|------|------|
| `pip install` 报错 | 确认已激活 `.venv`，Python >= 3.11 |
| `python run.py` 报找不到模块 | 确认 `pip install -e ".[dev]"` 执行成功 |
| curl 连不上 | 确认 `python run.py` 正在运行 |
| Extension 气泡不出现 | 1) 确认后端已启动 2) 确认是 B站视频页 URL 3) F12 Console 看报错 |
| 气泡显示半透明 | 后端未连接，检查 `localhost:8000/health` |
| Extension 加载失败 | 确认选择了 `extension/` 目录（不是 `extension/assets/`） |

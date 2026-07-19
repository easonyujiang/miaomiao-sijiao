# 服务端部署指导

本文档指导如何将妙喵私教的服务端（FastAPI + Next.js）部署到云服务器。

> 当前实际部署路径：`/opt/miaomiao`

## 目录

- [环境要求](#环境要求)
- [一键部署](#一键部署)
- [手动部署](#手动部署)
- [环境变量](#环境变量)
- [反向代理配置](#反向代理配置)
- [HTTPS 配置](#https-配置)
- [数据备份](#数据备份)
- [常见问题](#常见问题)

---

## 环境要求

| 组件 | 版本 |
|---|---|
| Python | >= 3.11 |
| Node.js | >= 18（仅构建前端需要） |
| SQLite | 随 Python 自带，无需额外安装 |
| ffmpeg | 必须安装，用于音频格式转换（语音输入） |

安装 ffmpeg：

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y ffmpeg

# CentOS/RHEL
sudo yum install -y ffmpeg
```

## 一键部署

```bash
# 1. 克隆代码
git clone https://github.com/easonyujiang/miaomiao-sijiao.git /opt/miaomiao
cd /opt/miaomiao/server

# 2. 创建虚拟环境 + 安装依赖
python -m venv .venv
source .venv/bin/activate
pip install -e "."

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key 和服务器域名（见下方变量表）

# 4. 构建前端（可选，如需网页端）
cd frontend
npm install
npm run build
cd ..

# 5. 启动服务
python run.py
# 或者（生产模式）：
uvicorn ewa.api.main:app --host 0.0.0.0 --port 8000 --workers 2
```

启动后访问 `http://<服务器IP>:8000/health` 验证服务正常。

## 手动部署

### 第一步：准备 Python 环境

```bash
cd server

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux
# .venv\Scripts\Activate.ps1  # Windows

# 安装依赖（不含开发工具）
pip install -e .
```

### 第二步：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**至少配置一个 LLM API Key 和百度语音 Key**：

```env
# 首选 DeepSeek（当前默认）
DEEPSEEK_API_KEY=sk-你的key

# 或 Kimi（Moonshot）
MOONSHOT_API_KEY=sk-你的key

# 百度短语音识别（语音输入必需）
BAIDU_API_KEY=你的key
BAIDU_SECRET_KEY=你的secret

# 服务器地址
EWA_HOST=0.0.0.0
EWA_PORT=8000

# CORS（填你的域名，多个用逗号分隔；插件端不受 CORS 限制）
EWA_CORS_ORIGINS=https://your-domain.com
```

### 第三步：构建前端

```bash
cd frontend
npm install
npm run build
cd ..
```

构建产物输出到 `frontend/dist/`，FastAPI 会自动挂载为静态文件。

### 第四步：启动服务

开发模式：

```bash
python run.py
```

生产模式（推荐）：

```bash
uvicorn ewa.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --log-level info
```

### 第五步：使用 systemd 管理进程（Linux）

创建 `/etc/systemd/system/miaomiao.service`：

```ini
[Unit]
Description=MiaoMiao SiJiao API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/miaomiao/server
ExecStart=/opt/miaomiao/server/.venv/bin/uvicorn ewa.api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5
Environment=PATH=/opt/miaomiao/server/.venv/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=/opt/miaomiao/server/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable miaomiao.service
sudo systemctl start miaomiao.service
sudo systemctl status miaomiao.service
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MOONSHOT_API_KEY` | `""` | Kimi (Moonshot) API Key |
| `KIMI_API_KEY` | `""` | Moonshot 的别名（二选一） |
| `DEEPSEEK_API_KEY` | `""` | DeepSeek API Key，当前默认首选 |
| `BAIDU_API_KEY` | `""` | 百度短语音识别 API Key |
| `BAIDU_SECRET_KEY` | `""` | 百度短语音识别 Secret Key |
| `EWA_HOST` | `0.0.0.0` | 绑定地址 |
| `EWA_PORT` | `8000` | 绑定端口 |
| `EWA_CORS_ORIGINS` | `""` (默认 localhost) | CORS 允许来源，逗号分隔；`*` 允许全部 |
| `EWA_RATE_LIMIT` | `1` | 设为 `0` 禁用请求限流 |
| `EWA_DATA_DIR` | `./data` | 数据根目录 |
| `EWA_SITE_DB_PATH` | `./data/miaomiao.db` | SQLite 数据库路径 |
| `EWA_SITE_SCHEMA_PATH` | `./docs/schema.sql` | 数据库建表 SQL |
| `NEXT_PUBLIC_SITE_SLUG` | `miaomiao` | 默认博主 slug |

## 反向代理配置

### Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # SSL 配置见下一节

    # API 和前端
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 管理后台静态文件（可选，FastAPI 已挂载）
    location /admin/ {
        proxy_pass http://127.0.0.1:8000/admin/;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

### Caddy（更简洁）

```
your-domain.com {
    reverse_proxy localhost:8000
}
```

## HTTPS 配置

### Certbot + Nginx

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 自动配置
sudo certbot --nginx -d your-domain.com

# 自动续期（certbot 默认已配置 cron）
sudo certbot renew --dry-run
```

### Caddy 自动 HTTPS

Caddy 默认自动获取和续期 Let's Encrypt 证书，无需额外配置。

## 数据备份

SQLite 数据库位于 `data/miaomiao.db`，建议定期备份：

```bash
# 备份（在线备份，不影响服务）
sqlite3 data/miaomiao.db ".backup 'data/miaomiao_backup_$(date +%Y%m%d).db'"

# 或使用 cron 每天凌晨 3 点自动备份
# crontab -e
0 3 * * * sqlite3 /opt/miaomiao/server/data/miaomiao.db ".backup '/opt/backups/miaomiao_$(date +\%Y\%m\%d).db'"
```

JSON 课程/字幕数据（`data/miaomiao/`）已纳入 git 版本管理，无需额外备份。

## 常见问题

### 启动报 `sqlite3.IntegrityError`

数据库表未初始化。检查 `EWA_SITE_SCHEMA_PATH` 指向的 `schema.sql` 文件路径是否正确。正常情况下 lifespan 会自动建表。

### 前端页面 404

确认 `frontend/dist/` 目录存在且包含构建产物。如果不需要网页端，可以跳过前端构建——插件端直接通过 API 通信。

### CORS 被浏览器拦截

检查 `EWA_CORS_ORIGINS` 是否包含了前端实际访问的域名。插件端通过 `background.js` service worker 代理请求，不受 CORS 限制。

### LLM 调用超时

检查网络连通性。Kimi API 地址为 `https://api.moonshot.cn`，DeepSeek 为 `https://api.deepseek.com`。确保服务器能访问这些域名。

### 数据库文件权限

确保服务运行用户对 `data/` 目录有读写权限：

```bash
sudo chown -R root:root /opt/miaomiao/server/data
```

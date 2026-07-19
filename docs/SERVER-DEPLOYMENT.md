# 服务端部署指导

本文档描述妙喵私教服务端（FastAPI + Next.js 静态站点）当前的生产部署方式，以及日常更新、验证流程。

## 当前生产环境

| 项目 | 值 |
|---|---|
| 云服务商 | 阿里云 ECS（2C4GB，Ubuntu 22.04） |
| 公网 IP | `8.130.190.169` |
| 部署路径 | `/opt/miaomiao/server` |
| Git 仓库 | https://github.com/easonyujiang/miaomiao-sijiao |
| 进程管理 | systemd（`miaomiao.service`），unit 文件收在仓库 `infra/miaomiao.service` |
| 反向代理 | nginx（自签名 HTTPS），配置收在仓库 `infra/nginx.conf` |

### 入口策略（Demo 阶段定稿）

| 入口 | 用途 |
|---|---|
| `http://8.130.190.169:8000` | uvicorn 直连，文字访问（聊天、API、管理后台）走这里 |
| `https://8.130.190.169` | nginx 自签名证书反代，网页端语音走这里——浏览器 `getUserMedia` 要求安全上下文。首次访问接受一次证书警告即可 |

不做 ICP 备案，不使用域名（原 duckdns 域名已弃用，国内解析失败）。

### 架构

```
浏览器 ── http :8000 ────────────────────┐
浏览器 ── https :443 → nginx（自签名）───→ uvicorn ×2（127.0.0.1:8000）
                                           ├─ FastAPI（ewa.api.main:app）
                                           ├─ /         → server/frontend/dist（Next.js 15 静态导出）
                                           ├─ /admin/   → 管理后台 SPA
                                           └─ /health   → 健康检查
```

- 前端是 Next.js 15 `output: 'export'` 纯静态导出，FastAPI 直接挂载 `server/frontend/dist`，无需单独前端服务。
- nginx：80 端口 301 重定向到 443；443 自签名 SSL 反代 `127.0.0.1:8000`，`client_max_body_size 20m`（语音上传）。

## 目录

- [日常部署（一键脚本）](#日常部署一键脚本)
- [部署验证](#部署验证)
- [首次服务器初始化](#首次服务器初始化)
- [环境变量](#环境变量)
- [数据资产与新视频上线](#数据资产与新视频上线)
- [数据备份](#数据备份)
- [常见问题](#常见问题)

---

## 日常部署（一键脚本）

所有部署脚本在仓库根目录，**在本地 Windows PowerShell 中运行**，通过 SSH（密码认证）操作远端服务器。

### 前置：凭据文件

在仓库根目录创建 `.ssh-credentials.json`（已被 `.gitignore` 排除）：

```json
{
  "username": "root",
  "password": "你的服务器密码",
  "host": "8.130.190.169",
  "admin_token": "管理后台 Token"
}
```

> Windows 换行坑：ps1 里嵌的远端 bash 脚本必须是 LF，否则远端 bash 解析失败。所有脚本内部已做 `\r\n → \n` 转换，无需手动处理。

### 后端一键部署：`deploy-backend.ps1`

```powershell
.\deploy-backend.ps1
```

流程：打包本地 `server/ewa` + `server/scripts` → scp 上传 → 远端备份现有 `ewa/` 到 `/tmp/ewa_backup` → 解压覆盖 → `systemctl restart miaomiao.service` → `curl http://127.0.0.1:8000/health` 验证。

**不会触碰**服务器上的 `data/`、`.env`、`.venv`。

### 前端一键部署：`deploy-community.ps1`

```powershell
.\deploy-community.ps1
```

流程：注入 `NEXT_PUBLIC_SITE_URL=http://8.130.190.169:8000` 后 `npm run build` → 打包 `dist` → 上传 → 远端把现有 `dist` 改名 `dist_old`（可回滚）→ 替换 → 重启 miaomiao.service 并 reload nginx。

## 部署验证

| 脚本 | 用途 |
|---|---|
| `.\verify-deploy.ps1` | SSH 到服务器，打印主机名/时间/服务状态/关键代码文件特征与修改时间，确认"部署上去的代码是对的版本" |
| `.\audit-server.ps1` | 对比本地与服务器全部 `.py` 文件（`ewa/` + `scripts/`，排除 `__pycache__`）的 md5，输出"仅本地/仅服务器/不一致"清单 |
| `.\test-live-chat.ps1` | 线上聊天接口实测四个问题（视频问答、带上下文总结、日记意图、社区讨论跳转），打印 intent/answer/actions |

建议流程：`deploy-backend.ps1` → `verify-deploy.ps1` / `audit-server.ps1` → `test-live-chat.ps1`。

## 首次服务器初始化

以下步骤只需在新服务器上执行一次（当前服务器已配好）：

```bash
# 1. 依赖
sudo apt update && sudo apt install -y ffmpeg nginx python3.11-venv

# 2. 拉代码
git clone https://github.com/easonyujiang/miaomiao-sijiao.git /opt/miaomiao
cd /opt/miaomiao/server

# 3. Python 环境
python3 -m venv .venv
source .venv/bin/activate
pip install -e "."

# 4. 环境变量
cp .env.example .env
# 编辑 .env，填入 LLM Key、百度语音 Key、ADMIN_TOKEN 等（见下表）

# 5. systemd 服务（unit 文件在仓库内）
cp /opt/miaomiao/infra/miaomiao.service /etc/systemd/system/miaomiao.service
systemctl daemon-reload
systemctl enable --now miaomiao.service

# 6. nginx 自签名证书 + 配置
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/miaomiao.key \
  -out /etc/nginx/ssl/miaomiao.crt \
  -subj "/CN=8.130.190.169"
cp /opt/miaomiao/infra/nginx.conf /etc/nginx/conf.d/miaomiao.conf
nginx -t && systemctl reload nginx

# 7. 验证
curl http://127.0.0.1:8000/health
```

`miaomiao.service` 关键内容（`infra/miaomiao.service`）：

- `WorkingDirectory=/opt/miaomiao/server`
- `ExecStart=.venv/bin/uvicorn ewa.api.main:app --host 0.0.0.0 --port 8000 --workers 2`
- `EnvironmentFile=/opt/miaomiao/server/.env`
- `Restart=always`，`RestartSec=5`

## 环境变量

以 `server/.env.example` 为准：

| 变量 | 说明 |
|---|---|
| `MOONSHOT_API_KEY` | Kimi (Moonshot) API Key，**首选** |
| `DEEPSEEK_API_KEY` | DeepSeek API Key，回退用 |
| `BAIDU_API_KEY` / `BAIDU_SECRET_KEY` | 百度短语音识别，语音输入**必需** |
| `ADMIN_TOKEN` | 管理后台 Bearer Token；**不设置则启动时随机生成并打印到日志** |
| `EWA_DATA_DIR` | 数据根目录，默认 `./data` |
| `MIAOMIAO_DATA_DIR` | 妙喵数据目录，默认 `./data/miaomiao` |
| `EWA_SITE_DB_PATH` | SQLite 数据库路径，默认 `./data/miaomiao.db`。**生产建议用绝对路径**，避免多进程 cwd 不一致 |
| `NEXT_PUBLIC_SITE_SLUG` | 默认博主 slug，当前种子数据为 `ashley` |
| `EWA_CORS_ORIGINS` | CORS 允许来源，逗号分隔；`*` 允许全部。插件端经 background.js 代理，不受 CORS 限制 |
| `EWA_RATE_LIMIT` | 设为 `0` 禁用请求限流 |
| `EWA_HOST` / `EWA_PORT` | 绑定地址/端口，默认 `0.0.0.0:8000` |

LLM 至少配置一个（Kimi 优先，DeepSeek 回退）。没有 OPENAI/ANTHROPIC 相关配置项。

## 数据资产与新视频上线

| 数据 | 位置 | 管理方式 |
|---|---|---|
| 字幕 JSON | `server/data/miaomiao/subtitles/` | **随 git 入库**，服务器 `git pull` 获取 |
| 课程 JSON | `server/data/miaomiao/lessons/` | 同上 |
| SQLite 数据库 | `data/miaomiao.db` | **不入库**，服务器本地生成 |

新视频上线时，三条数据通道必须备齐：

1. `videos` 表行（SQLite）
2. 字幕 JSON
3. 课程 JSON（可选）

推荐两种方式：

### 方式一：管理后台一站式端点（推荐）

```powershell
curl.exe -X POST "http://8.130.190.169:8000/api/admin/assets/videos" `
  -H "Authorization: Bearer $env:ADMIN_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"bv_id": "BV1xxx...", "title": "视频标题", ...}'
```

一个请求同时写入 videos 表、字幕和课程数据。Token 可用 `.\get-admin-token.ps1` 获取（或取自 `.ssh-credentials.json` 的 `admin_token`）。

### 方式二：抓取脚本

```bash
cd /opt/miaomiao/server
source .venv/bin/activate
python scripts/fetch_subtitle.py <BV号>
```

抓取 B站字幕并落盘 JSON。**需要 SESSDATA cookie**（B站登录态），否则拿不到字幕。

## 数据备份

SQLite 数据库位于 `data/miaomiao.db`，建议定期备份：

```bash
# 在线备份，不影响服务
sqlite3 data/miaomiao.db ".backup 'data/miaomiao_backup_$(date +%Y%m%d).db'"

# cron 每天凌晨 3 点自动备份（crontab -e）
0 3 * * * sqlite3 /opt/miaomiao/server/data/miaomiao.db ".backup '/opt/backups/miaomiao_$(date +\%Y\%m\%d).db'"
```

字幕/课程 JSON 已随 git 入库，无需额外备份。

## 常见问题

### 服务起不来 / 重启后接口 502

```bash
systemctl status miaomiao.service
journalctl -u miaomiao.service -n 100 --no-pager
```

常见原因：`.env` 缺失或格式错误、端口 8000 被占用、依赖变更后未在 `.venv` 中重装（`pip install -e .`）。

### `deploy-backend.ps1` 报 SSH 认证失败

检查 `.ssh-credentials.json` 是否存在且 `username`/`password`/`host` 三个字段齐全。脚本通过 `SSH_ASKPASS` 传入密码，不支持交互式输入。

### 前端页面 404

确认服务器上 `/opt/miaomiao/server/frontend/dist/` 存在且包含构建产物。用 `deploy-community.ps1` 重新部署即可，旧版本保留在 `dist_old` 可回滚。

### 网页端语音录音无反应

确认走的是 `https://8.130.190.169` 且已接受自签名证书警告——`getUserMedia` 只在安全上下文可用，`http://...:8000` 下无法录音（文字聊天不受影响）。同时检查服务器 `.env` 中 `BAIDU_API_KEY` / `BAIDU_SECRET_KEY` 有效。

### CORS 被浏览器拦截

检查 `EWA_CORS_ORIGINS` 是否包含前端实际访问的来源（如 `http://8.130.190.169:8000`）。插件端通过 `background.js` service worker 代理请求，不受 CORS 限制。

### LLM 调用超时

检查服务器到 `https://api.moonshot.cn`（Kimi）和 `https://api.deepseek.com`（DeepSeek）的网络连通性。

### ADMIN_TOKEN 忘了

不设置 `ADMIN_TOKEN` 时启动日志会打印随机生成的 Token；也可以直接在 `.env` 里固定一个，然后 `systemctl restart miaomiao.service`。

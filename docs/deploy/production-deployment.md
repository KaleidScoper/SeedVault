# SeedVault 生产环境部署指南

> 版本：v0.1 · 日期：2026-05-28
> 目标读者：有 Linux 基础运维经验的开发者

---

## 目录

1. [部署前准备](#1-部署前准备)
2. [Microsoft Azure AD 应用注册](#2-microsoft-azure-ad-应用注册)
3. [方案一：Docker Compose 部署（推荐）](#3-方案一docker-compose-部署推荐)
4. [方案二：裸机部署（systemd）](#4-方案二裸机部署systemd)
5. [方案三：Caddy + 单进程（轻量）](#5-方案三caddy--单进程轻量)
6. [反向代理与 SSL](#6-反向代理与-ssl)
7. [环境变量参考](#7-环境变量参考)
8. [备份与恢复](#8-备份与恢复)
9. [运维与监控](#9-运维与监控)
10. [故障排查](#10-故障排查)

---

## 1. 部署前准备

### 1.1 服务器最低配置

| 资源 | 最低 | 推荐 |
|------|------|------|
| CPU | 1 核 | 2 核 |
| 内存 | 512 MB | 1 GB |
| 磁盘 | 10 GB | 20 GB+（取决于截图存储量） |
| 系统 | Ubuntu 22.04 / 24.04 或 Debian 12 | — |

### 1.2 前置条件

- 一个已解析到服务器的域名（`your-domain.com`）
- Microsoft Azure 账号（用于 OAuth 应用注册，免费）
- 服务器已安装 Docker Engine ≥ 24.0 和 Docker Compose ≥ v2（方案一），或 Python ≥ 3.11 + Node.js ≥ 18（方案二/三）

### 1.3 检查清单

在开始部署前确认以下事项已就绪：

- [ ] 服务器 SSH 可登录，防火墙开放 80/443 端口
- [ ] 域名 DNS 已解析到服务器 IP
- [ ] 已在 Microsoft Entra ID 注册应用并获得 Client ID
- [ ] 已选择认证方式（证书 或 客户端密码）并准备好对应的凭据

---

## 2. Microsoft Entra ID 应用注册

SeedVault 使用 Microsoft OAuth 实现免密码登录。部署前必须完成此步骤。

### 2.1 前提：你需要一个 Entra ID 目录（租户）

自 2026 年起，Microsoft 已弃用**在目录外部创建应用**的功能。直接用个人 Microsoft 账号访问"应用注册"页面会看到：

> "在目录外部创建应用程序的功能已被弃用。你可通过加入 M365 开发人员计划或注册 Azure 来获取新目录。"

这意味着：你必须先拥有一个 Entra ID 目录，再把你的账号加入该目录，然后才能在目录内注册应用。获取目录有两种免费途径：

| 途径 | 操作 | 费用 |
|------|------|------|
| **注册 Azure 免费账户**（推荐） | 前往 [azure.microsoft.com/free](https://azure.microsoft.com/free)，用你的 Microsoft 账号注册 | 免费（含 $200 试用额度，应用注册本身不收费） |
| **加入 M365 开发人员计划** | 前往 [aka.ms/joinM365DeveloperProgram](https://aka.ms/joinM365DeveloperProgram) | 免费（获得一个即时可用的 sandbox 租户） |

注册 Azure 免费账户后，系统自动创建目录，你的账号成为该目录的成员。之后访问 [entra.microsoft.com](https://entra.microsoft.com) → **应用注册** 即可正常操作。

### 2.2 注册应用

1. 登录 [Microsoft Entra 管理中心](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. 点击 **新注册** → 填写：
   - **名称**：`SeedVault`（或自定义）
   - **支持的帐户类型**：选择 `仅限个人 Microsoft 帐户`（第三项——允许任意 Microsoft 账号登录）
   - **重定向 URI**：平台选 `Web`，值填 `https://your-domain.com/api/v1/auth/callback`
3. 注册完成后进入应用详情页，记录 **应用程序（客户端）ID**（即 `MICROSOFT_CLIENT_ID`）
4. 进入 **API 权限** → **添加权限** → **Microsoft Graph** → **委托的权限** → 勾选 `XboxLive.signin` → 保存

### 2.3 创建客户端凭据

应用注册完成后，还需要创建凭据用于后端调用 Microsoft Token 端点。SeedVault 支持两种方式：

| 方式 | 说明 |
|------|------|
| **客户端密码（client secret）** | 简单，一个字符串即可。需注意租户安全策略可能阻止创建（见下方说明） |
| **证书凭据（certificate）** | 更安全，公钥上传到 Entra ID，私钥保存在服务器。SeedVault 尚未支持，计划 v0.2 |

#### 创建客户端密码

1. 在应用的 **证书和密码** → **客户端密码** 标签页 → **新建客户端密码**
2. 填写说明，选择有效期（建议 24 个月，到期前需轮换）
3. 点击添加后，**立即复制密码值**（离开页面后不再可见）

> **注意：** 如果新建客户端密码时报错 "Client secrets are blocked by a tenant-wide policy"：
> 进入 **Entra 管理中心** → **保护与安全** → **身份验证方法** → **策略** → **应用管理** → 将 **"阻止客户端密码"** 策略设为禁用，或为该应用添加例外。

#### 证书凭据（可选）

如需使用证书代替密码，生成自签名证书后将公钥上传到应用的 **证书** 标签页。`MICROSOFT_CLIENT_SECRET` 留空即可（SeedVault 目前优先使用 `client_secret_post` 方式，证书支持在后续版本中完善）。

### 2.4 OAuth 链路说明

```
用户登录 → Microsoft 授权页 → 回调 /api/v1/auth/callback
  → Xbox Live 认证 → XSTS 认证 → Minecraft 服务认证
  → 获取玩家 UUID / 皮肤 / 正版状态
  → 创建或更新用户记录 → 签发 JWT Cookie → 登录完成
```

每次登录共调用 5 个外部 API（Microsoft → Xbox Live → XSTS → Minecraft 认证 → Minecraft Profile）。若任一环节超时（通常为 XSTS 或 Minecraft 服务宕机），用户将收到登录失败提示——这是上游服务的已知限制，不属于 SeedVault 故障。

---

## 3. 方案一：Docker Compose 部署（推荐）

### 3.1 项目文件结构（部署视角）

在服务器上克隆仓库后，需额外创建以下文件：

```
SeedVault/
├── docker-compose.yml          # 容器编排
├── .env.production             # 生产环境变量
├── Dockerfile                  # 后端镜像
├── Dockerfile.frontend         # 前端构建镜像
├── .dockerignore
├── backend/
├── frontend/
└── docs/
```

### 3.2 创建 Dockerfile（后端）

在项目根目录创建 `Dockerfile`：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN mkdir -p uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.3 创建 Dockerfile.frontend

前端作为构建阶段，产物由 Nginx 托管：

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html

COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Vue Router history mode
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static assets cache
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API proxy to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Uploads proxy to backend
    location /uploads/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

EXPOSE 80
```

### 3.4 创建 docker-compose.yml

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    volumes:
      - seedvault_uploads:/app/uploads
      - seedvault_db:/app/db
    env_file:
      - .env.production
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///db/data.db
      - UPLOAD_DIR=/app/uploads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy

volumes:
  seedvault_uploads:
  seedvault_db:
```

> 生产环境建议在前端 Nginx 之前再加一层 Caddy 或 Nginx 作为 SSL 终端（见 §6），docker-compose 中的 frontend 容器仅暴露 80 端口，SSL 由外层的反向代理处理。

### 3.5 创建 .env.production

```bash
# === 必填环境变量 ===

# 应用
APP_ENV=production
ALLOW_DEV_LOGIN=false
SECRET_KEY=<生成一个 64 字符以上的随机字符串>
BASE_URL=https://your-domain.com

# 数据库（SQLite 路径为容器内路径）
DATABASE_URL=sqlite+aiosqlite:///db/data.db

# CORS（前端域名，可逗号分隔多个）
CORS_ORIGINS=https://your-domain.com

# Microsoft OAuth（必填，见 §2）
MICROSOFT_CLIENT_ID=<你的 Entra ID 应用客户端 ID>
MICROSOFT_CLIENT_SECRET=<你的 Entra ID 应用客户端密码>
MICROSOFT_REDIRECT_URI=https://your-domain.com/api/v1/auth/callback

# JWT
JWT_EXPIRE_SECONDS=604800

# === 可选环境变量 ===

# 存储（默认本地存储，如需 S3 见 §8.3）
# STORAGE_BACKEND=s3
# S3_ENDPOINT=https://your-s3-endpoint
# S3_ACCESS_KEY=<access-key>
# S3_SECRET_KEY=<secret-key>
# S3_BUCKET=seedvault-uploads
# S3_REGION=auto
# S3_PUBLIC_URL=https://cdn.your-domain.com
```

### 3.6 生成 SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

将输出值填入 `.env.production` 的 `SECRET_KEY`。

### 3.7 创建 .dockerignore

```
frontend/node_modules
frontend/dist
backend/__pycache__
backend/app/__pycache__
backend/**/__pycache__
backend/*.db
backend/*.db-*
backend/uploads/*
.venv
.git
**/.env
```

### 3.8 启动服务

```bash
# 在项目根目录
docker compose up -d --build

# 查看日志
docker compose logs -f

# 验证健康状态
curl http://localhost:8000/api/v1/health
```

### 3.9 目录权限

容器内使用非 root 用户运行更安全。在 `Dockerfile` 中添加：

```dockerfile
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
```

---

## 4. 方案二：裸机部署（systemd）

适用场景：不想引入 Docker 依赖的小型 VPS。

### 4.1 安装依赖

```bash
# Python 3.11+
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nodejs npm

# 前端构建
cd /opt/seedvault/frontend
npm ci
npm run build
```

### 4.2 安装后端

```bash
sudo mkdir -p /opt/seedvault
sudo chown $USER:$USER /opt/seedvault

# 克隆或 rsync 项目到 /opt/seedvault
cd /opt/seedvault/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4.3 创建 .env

从项目目录复制 `.env.production` 模板（见 §3.5）到 `/opt/seedvault/backend/.env`，填入实际值。

注意路径差异：

```bash
UPLOAD_DIR=/opt/seedvault/backend/uploads
DATABASE_URL=sqlite+aiosqlite:///opt/seedvault/backend/data.db
```

### 4.4 创建 systemd 服务

创建 `/etc/systemd/system/seedvault.service`：

```ini
[Unit]
Description=SeedVault Backend
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/seedvault/backend
EnvironmentFile=/opt/seedvault/backend/.env
ExecStart=/opt/seedvault/backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

# 安全加固
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/seedvault/backend/uploads /opt/seedvault/backend

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now seedvault
sudo systemctl status seedvault
```

### 4.5 前端托管

前端 `dist/` 目录需要由 Nginx 或 Caddy 托管。以下为 Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /opt/seedvault/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
    }

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 4.6 设置目录权限

```bash
sudo chown -R www-data:www-data /opt/seedvault
sudo chmod 755 /opt/seedvault/backend/uploads
```

---

## 5. 方案三：Caddy + 单进程（轻量）

Caddy 自动处理 SSL 证书，配置极简，适合个人部署。

### 5.1 安装 Caddy

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

### 5.2 Caddyfile

创建 `/etc/caddy/Caddyfile`：

```
your-domain.com {
    # API 反代到后端
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }

    # 上传文件反代到后端
    handle /uploads/* {
        reverse_proxy 127.0.0.1:8000
    }

    # 前端静态文件
    handle {
        root * /opt/seedvault/frontend/dist
        try_files {path} /index.html
        file_server
    }

    # 安全头
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }

    # 日志
    log {
        output file /var/log/caddy/seedvault.log
    }
}
```

后端启动方式与 §4 相同（systemd 服务）。Caddy 自动从 Let's Encrypt 获取 SSL 证书，无需任何额外配置。

---

## 6. 反向代理与 SSL

### 6.1 架构模式

无论选择哪种方案，推荐的请求链路为：

```
用户浏览器 → HTTPS (443) → [Caddy/Nginx 反代]
    /api/*    → http://backend:8000
    /uploads/* → http://backend:8000
    其他       → 前端静态文件
```

### 6.2 访问日志中的客户端 IP

后端的 IP 获取依赖 `X-Forwarded-For` 头部。确保反向代理正确设置此头部：

**Nginx：**
```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

**Caddy：** 默认已设置，无需额外配置。

后端 `seed_views` 表（浏览去重）和匿名举报使用 IP 参与计算 session_key / reporter_ip_hash，反向代理未正确设置此头部将导致所有请求共享同一 IP，影响浏览去重精度和匿名举报去重。

### 6.3 SSL 证书（Nginx 方案）

若使用 Nginx 而不是 Caddy，需额外安装 certbot：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo systemctl enable certbot.timer  # 自动续期
```

---

## 7. 环境变量参考

### 7.1 完整变量列表

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `APP_ENV` | 是 | `development` | `production` 或 `development` |
| `ALLOW_DEV_LOGIN` | 是 | `false` | **生产环境必须设为 `false`** |
| `SECRET_KEY` | 是 | — | JWT 签名密钥，≥ 64 字符随机字符串 |
| `BASE_URL` | 是 | — | 网站完整 URL，用于 OAuth 回调等 |
| `DATABASE_URL` | 是 | — | SQLAlchemy 数据库连接字符串 |
| `CORS_ORIGINS` | 是 | — | 允许的跨域来源，逗号分隔 |
| `MICROSOFT_CLIENT_ID` | 是 | — | Entra ID 应用客户端 ID |
| `MICROSOFT_CLIENT_SECRET` | 是 | — | Entra ID 应用客户端密码 |
| `MICROSOFT_REDIRECT_URI` | 是 | — | OAuth 回调 URL，必须与 Entra ID 中配置完全一致 |
| `JWT_EXPIRE_SECONDS` | 否 | `604800` | JWT 有效期（秒），默认 7 天 |
| `STORAGE_BACKEND` | 否 | `local` | `local` 或 `s3` |
| `UPLOAD_DIR` | 否 | `./uploads` | 本地存储目录（`local` 模式） |
| `S3_ENDPOINT` | S3 时必填 | — | S3 兼容端点 |
| `S3_ACCESS_KEY` | S3 时必填 | — | S3 Access Key |
| `S3_SECRET_KEY` | S3 时必填 | — | S3 Secret Key |
| `S3_BUCKET` | S3 时必填 | — | 存储桶名称 |
| `S3_REGION` | 否 | `auto` | 存储桶区域 |
| `S3_PUBLIC_URL` | 否 | — | 公开访问 URL 前缀（CDN 域名） |

### 7.2 必做：关闭开发登录

**生产环境必须设置**：

```bash
ALLOW_DEV_LOGIN=false
```

若此值遗漏为 `true`，任何人可从前端登录页的下拉菜单选择预设用户，绕过 Microsoft OAuth 认证。这是最高优先级的安全配置项。

---

## 8. 备份与恢复

### 8.1 需要备份的内容

| 数据 | 路径 | 备份策略 |
|------|------|----------|
| SQLite 数据库 | `backend/data.db` | 每日备份 |
| 用户上传截图 | `backend/uploads/` | 每日备份 |
| 环境变量文件 | `.env` / `.env.production` | 一次性备份到安全位置 |

### 8.2 SQLite 备份脚本

```bash
#!/bin/bash
# /opt/scripts/seedvault-backup.sh

BACKUP_DIR="/opt/backups/seedvault"
DB_PATH="/opt/seedvault/backend/data.db"
UPLOAD_PATH="/opt/seedvault/backend/uploads"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

DATE=$(date +%Y%m%d-%H%M%S)

# 安全备份 SQLite（VACUUM INTO 需要在 Python 中执行，或用 .backup）
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/data-$DATE.db'"

# 压缩截图目录
tar -czf "$BACKUP_DIR/uploads-$DATE.tar.gz" -C "$(dirname "$UPLOAD_PATH")" "$(basename "$UPLOAD_PATH")"

# 删除超过保留期的备份
find "$BACKUP_DIR" -name "*.db" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

添加到 crontab（每日凌晨 3 点）：

```bash
0 3 * * * /opt/scripts/seedvault-backup.sh >> /var/log/seedvault-backup.log 2>&1
```

### 8.3 SQLite WAL 模式注意事项

SeedVault 默认使用 SQLite + aiosqlite，WAL 模式下的 `-wal` 和 `-shm` 文件是数据库的一部分。备份时必须使用 `sqlite3 .backup` 命令（如上脚本），它会正确处理 WAL 文件。不要直接 `cp data.db` ——裸复制可能得到不完整或损坏的数据库。

### 8.4 恢复

```bash
# 停止服务
sudo systemctl stop seedvault

# 恢复数据库
cp /opt/backups/seedvault/data-20260528-030000.db /opt/seedvault/backend/data.db

# 恢复截图
tar -xzf /opt/backups/seedvault/uploads-20260528-030000.tar.gz -C /opt/seedvault/backend/

# 修复权限
sudo chown -R www-data:www-data /opt/seedvault/backend

# 启动服务
sudo systemctl start seedvault
```

---

## 9. 运维与监控

### 9.1 健康检查

```bash
# 服务是否存活
curl -s https://your-domain.com/api/v1/health
# 预期: {"status":"ok"}

# 数据库是否正常（通过请求一个公开端点）
curl -s -o /dev/null -w "%{http_code}" https://your-domain.com/api/v1/seeds?page_size=1
# 预期: 200
```

### 9.2 日志查看

**Docker Compose：**
```bash
docker compose logs -f backend
docker compose logs --tail=200 frontend
```

**systemd：**
```bash
sudo journalctl -u seedvault -f
sudo journalctl -u seedvault --since "1 hour ago"
```

### 9.3 日志级别

FastAPI + uvicorn 默认输出访问日志（每请求一行）和错误日志。生产环境可通过 uvicorn 参数控制日志级别：

```bash
uvicorn app.main:app --log-level warning
```

### 9.4 定时清理

以下任务应加入 cron：

| 任务 | 频率 | 命令/脚本 |
|------|------|-----------|
| 清理孤儿截图 | 每周 | 后端启动时自动执行。也可通过 cron 触发一个管理脚本删除 `status='pending'` 且超过 7 天的截图 |
| 清理过期 seed_views | 每日 | SQLite 会自动回收空间，但可执行 `DELETE FROM seed_views WHERE viewed_at < datetime('now', '-30 minutes')` |
| 数据库备份 | 每日 | 见 §8.2 |
| SSL 证书续期 | 自动 | certbot timer / Caddy 自动处理 |

### 9.5 版本更新流程

```bash
# 1. 备份数据库
/opt/scripts/seedvault-backup.sh

# 2. 拉取新代码
cd /opt/seedvault
git pull origin main

# 3. 重建前端
cd frontend && npm ci && npm run build

# 4. 重启后端
sudo systemctl restart seedvault

# 5. 验证
curl -s https://your-domain.com/api/v1/health
```

Docker Compose 环境下的更新：

```bash
docker compose down
git pull origin main
docker compose up -d --build
```

---

## 10. 故障排查

### 10.1 登录失败

**症状**：点击"使用 Microsoft 登录"后重定向回站点但未登录。

排查步骤：

1. 检查 `.env` 中 `MICROSOFT_CLIENT_ID` 和 `MICROSOFT_CLIENT_SECRET` 是否正确
2. 确认 Entra ID 应用的重定向 URI 与 `MICROSOFT_REDIRECT_URI` 完全一致（包括 `https://` 和路径 `/api/v1/auth/callback`）
3. 确认 Entra ID 应用已添加 `XboxLive.signin` 权限
4. 查看后端日志中的 OAuth 错误信息（`docker compose logs backend` 或 `journalctl -u seedvault`）
5. 检查 Xbox Live / Minecraft 服务状态（这两个上游偶尔宕机，此时登录将失败且 SeedVault 无法修复）

### 10.2 图片上传后无法显示

1. 确认 `uploads/` 目录存在且后端进程有写入权限
2. 确认 `X-Forwarded-For` / `X-Real-IP` 头部由反向代理正确设置（影响文件路径和访问控制）
3. 检查反代是否将 `/uploads/` 路径正确转发到后端

### 10.3 数据库锁定

SQLite 在并发写入时会返回 "database is locked" 错误。对于个人或小团队部署，正常使用不会遇到此问题。若频繁出现：

- 确认 WAL 模式已启用（aiosqlite 默认启用）
- 减少同时写入的连接数
- 考虑迁移到 PostgreSQL（见 §10.5）

### 10.4 前端页面刷新后 404

确认 Nginx/Caddy 配置中包含了 Vue Router 的 history mode 回退规则：

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

### 10.5 从 SQLite 迁移到 PostgreSQL

当单机并发写入成为瓶颈或需要高可用时：

1. 安装 `psycopg2-binary` 或 `asyncpg`
2. 使用 [pgloader](https://pgloader.io/) 迁移数据
3. 修改 `DATABASE_URL`：

```bash
# SQLite
DATABASE_URL=sqlite+aiosqlite:///data.db

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/seedvault
```

4. 所有 SQLAlchemy 模型已为 PostgreSQL 兼容设计，无需修改代码
5. 迁移前务必全量备份 SQLite 数据库

---

*文档结束 · 部署相关问题请在 GitHub Issues 反馈*

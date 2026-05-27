# Seed Vault

Minecraft 种子共享平台 —— 面向中文社群的种子投稿与检索平台，轻量自部署，GitHub 开源。

灵感来自斯瓦尔巴全球种子库（Svalbard Global Seed Vault）。

## 技术栈

| 层 | 方案 |
|---|------|
| 前端 | Vue 3 + Vite + TypeScript + Naive UI |
| 后端 | FastAPI (Python) |
| 数据库 | SQLite（开发/小规模）→ PostgreSQL（可选升级） |
| ORM | SQLAlchemy 2.x |
| 认证 | Microsoft OAuth 2.0 → JWT (HTTP-only Cookie) |
| 存储 | 本地文件系统 → S3 兼容接口（可选） |

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后自动创建 `data.db` 并填充开发用种子数据。API 文档自动生成于 `http://localhost:8000/docs`。

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 `http://localhost:5173`，自动代理 API 请求到后端。

### 开发登录

设置环境变量 `ALLOW_DEV_LOGIN=true`（`.env` 中默认开启），访问登录页面可从下拉菜单选择预设用户快速登录，无需配置 Microsoft OAuth。

生产部署前关闭此选项并配置 Microsoft Azure AD 应用凭据。

### 生产部署

```bash
cd frontend && npm run build
cd ../backend
# 编辑 .env：关闭 ALLOW_DEV_LOGIN，填入 MICROSOFT_CLIENT_ID 等
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端构建产物由 FastAPI 托管（或使用 Caddy/Nginx 反代）。

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 环境变量配置
│   │   ├── database.py          # 数据库连接
│   │   ├── models.py            # SQLAlchemy 数据模型 16 表
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── seed_data.py         # 开发种子数据
│   │   ├── routers/             # API 路由
│   │   │   ├── auth.py          # 认证（Microsoft OAuth + dev login）
│   │   │   ├── seeds.py         # 种子 CRUD / 点赞 / 举报
│   │   │   ├── upload.py        # 图片上传
│   │   │   ├── tags.py          # 标签
│   │   │   ├── versions.py      # 版本号
│   │   │   ├── users.py         # 用户主页 / 我的投稿 / 书签
│   │   │   ├── collections.py   # 收藏夹 CRUD
│   │   │   ├── admin.py         # 审核后台
│   │   │   └── notifications.py # 通知
│   │   └── services/            # 业务逻辑层
│   │       ├── auth.py          # JWT / 用户管理
│   │       ├── minecraft.py     # Xbox Live / XSTS / MC API
│   │       ├── seeds.py         # 种子筛选 / 热度分 / 点赞
│   │       └── storage.py       # 本地文件存储
│   ├── uploads/screenshots/     # 截图存储（.gitignore）
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.ts              # Vue 应用入口
│   │   ├── App.vue              # 根组件 + 全局布局
│   │   ├── router/              # Vue Router 路由
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── api/                 # Axios 请求封装
│   │   ├── types/               # TypeScript 类型定义
│   │   ├── components/          # 通用组件（Navbar, SeedCard）
│   │   └── views/               # 页面（Home, Browse, Detail, Submit, Collections, Admin, Login）
│   └── package.json
├── docs/                        # 设计文档
│   ├── mc-seed-platform-plan.md
│   ├── interaction-design.md
│   ├── visual-style-guide.md
│   ├── api-and-backend-design.md
│   └── database-design.md
└── CLAUDE.md
```

## API 端点

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/api/v1/seeds` | 种子列表（筛选+排序+分页） | - |
| `GET` | `/api/v1/seeds/{id}` | 种子详情 | - |
| `POST` | `/api/v1/seeds` | 投稿种子 | 需登录 |
| `POST` | `/api/v1/seeds/{id}/like` | 点赞/取消 | 需登录 |
| `GET` | `/api/v1/tags` | 标签列表 | - |
| `GET` | `/api/v1/versions` | 版本号列表 | - |
| `GET` | `/api/v1/auth/me` | 当前用户信息 | 需登录 |
| `GET` | `/api/v1/auth/login` | Microsoft OAuth 入口 | - |
| `POST` | `/api/v1/auth/dev-login` | 开发模式登录 | 仅开发环境 |
| `GET` | `/api/v1/collections` | 我的收藏夹 | 需登录 |
| `GET` | `/api/v1/admin/seeds/pending` | 待审种子 | 管理员 |

完整 API 文档见 `docs/api-and-backend-design.md` 及 `http://localhost:8000/docs`。

## MVP 功能

- 种子浏览/筛选（版本端、版本号、世界类型、标签、Mod 环境、排序）
- 种子详情（截图、坐标、一键复制种子值）
- 投稿三步向导（完整字段校验 + 人工审核）
- Microsoft OAuth 登录（首次自动注册）
- Minecraft 正版验证（皮肤头像 + 正版标识）
- 点赞系统（登录点赞 + 本地点赞 + 登录后合并）
- 收藏夹（创建/编辑/删除、添加/移除种子、公开/私有）
- 管理员审核后台

## 许可

MIT License

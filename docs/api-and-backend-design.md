# Seed Vault · API 与后端设计

> 版本：v0.1 · 日期：2026-05-27  
> 关联文档：`mc-seed-platform-plan.md`（架构与数据模型）、`interaction-design.md`（交互与认证流）、`visual-style-guide.md`（UI 规格）

---

## 目录

1. [API 概览](#1-api-概览)
2. [通用约定](#2-通用约定)
3. [认证相关 (Auth)](#3-认证相关-auth)
4. [种子相关 (Seeds)](#4-种子相关-seeds)
5. [评论相关 (Comments)](#5-评论相关-comments)
6. [图片上传 (Upload)](#6-图片上传-upload)
7. [标签 (Tags)](#7-标签-tags)
8. [版本号 (Versions)](#8-版本号-versions)
9. [用户相关 (Users)](#9-用户相关-users)
10. [通知 (Notifications)](#10-通知-notifications)
11. [收藏夹 (Collections)](#11-收藏夹-collections)
12. [管理后台 (Admin)](#12-管理后台-admin)
13. [请求/响应 Schemas](#13-请求响应-schemas)
14. [数据库 DDL](#14-数据库-ddl)
15. [文件存储抽象层](#15-文件存储抽象层)
16. [Auth 中间件与验证链路](#16-auth-中间件与验证链路)
17. [服务层边界](#17-服务层边界)

---

## 1. API 概览

### 1.1 端点总览

```
GET    /auth/login                        Microsoft OAuth 入口（重定向）
GET    /auth/callback                     OAuth 回调 + MC 验证 + JWT 签发
POST   /auth/logout                       清除 JWT
GET    /auth/me                           当前用户信息

GET    /seeds                             种子列表（筛选 + 排序 + 分页）
GET    /seeds/{id}                        种子详情
POST   /seeds                             投稿种子                      [需登录]
POST   /seeds/{id}/like                   点赞/取消点赞                   [需登录]
POST   /seeds/{id}/report                 举报种子
GET    /seeds/{id}/comments               评论列表
POST   /seeds/{id}/comments               发表评论                       [需登录]
DELETE /seeds/{id}/comments/{comment_id}  删除自己的评论                  [需登录]

POST   /upload/screenshot                 上传截图                       [需登录]

GET    /tags                              标签列表（预置，无分页）

GET    /versions                          版本号列表（用于筛选器/投稿表单下拉）

GET    /users/{user_id}                   用户主页
GET    /users/me/seeds                    我的投稿                       [需登录]
GET    /users/me/bookmarks                我赞过的种子                    [需登录]
POST   /users/me/bookmarks/merge          匿名书签合并                    [需登录]

GET    /notifications                     我的通知列表                    [需登录]
POST   /notifications/{id}/read           标记通知为已读                  [需登录]

GET    /collections                       我的收藏夹列表                  [需登录]
POST   /collections                       创建收藏夹                     [需登录]
GET    /collections/{id}                  收藏夹详情（含种子列表）
PUT    /collections/{id}                  编辑收藏夹                     [需登录]
DELETE /collections/{id}                  删除收藏夹                     [需登录]
POST   /collections/{id}/seeds/{seed_id}  添加种子到收藏夹                [需登录]
DELETE /collections/{id}/seeds/{seed_id}  从收藏夹移除种子                [需登录]

GET    /admin/seeds/pending               待审种子列表                    [需管理员]
POST   /admin/seeds/{id}/approve          通过审核                       [需管理员]
POST   /admin/seeds/{id}/reject           拒绝审核                       [需管理员]
GET    /admin/users                       用户列表                       [需管理员]
POST   /admin/users/{id}/ban              封禁/解封用户                   [需管理员]
POST   /admin/versions                    添加版本号                     [需管理员]
DELETE /admin/versions/{id}               删除版本号                     [需管理员]
```

### 1.2 不需要的端点

- **`POST /register`**：不存在独立注册。首次 Microsoft OAuth 登录自动创建用户。
- **`PUT /seeds/{id}`**：种子一经审核通过即锁定，不可编辑。
- **`GET /search`**：关键字搜索合并进 `GET /seeds?q=xxx`，不单独建路由。
- **`POST /bookmarks`**：点赞与收藏已分离。`POST /seeds/{id}/like` 处理点赞，`POST /collections/{id}/seeds/{seed_id}` 处理归档。
- **`/reports`**：举报通过 `POST /seeds/{id}/report` 实现，不是独立资源。

---

## 2. 通用约定

### 2.1 Base URL

```
开发:  http://localhost:8000/api/v1
生产:  https://<domain>/api/v1
```

所有端点以 `/api/v1` 为前缀（FastAPI `APIRouter(prefix="/api/v1")`）。

### 2.2 响应格式

所有成功响应遵循统一信封：

```json
{
  "data": { ... },
  "meta": { "page": 1, "page_size": 24, "total": 142, "pages": 6 }
}
```

- `data`：主体内容。单条为对象，列表为数组。
- `meta`：仅分页端点带此字段。非分页端点省略。

### 2.3 错误响应

```json
{
  "error": {
    "code": "SEED_NOT_FOUND",
    "message": "该种子不存在或已被删除"
  }
}
```

| HTTP 状态码 | 语义 |
|------------|------|
| `400` | 请求参数校验失败 |
| `401` | 未登录或 JWT 过期 |
| `403` | 已登录但权限不足 |
| `404` | 资源不存在 |
| `409` | 冲突（重复投稿、重复点赞等） |
| `413` | 上传文件超过大小限制 |
| `422` | 请求体格式正确但业务逻辑校验失败 |
| `429` | 速率限制 |
| `500` | 服务端异常 |

### 2.4 认证传递方式

登录成功后，后端设置 HTTP-only Cookie：

```
Set-Cookie: seedvault_token=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800
```

前端无需手动携带——浏览器自动随请求发送。前端通过 `GET /auth/me` 获取当前登录状态。

### 2.5 分页

| 参数 | 默认值 | 范围 |
|------|--------|------|
| `page` | 1 | ≥ 1 |
| `page_size` | 24 | 12 / 24 / 48 |

所有列表端点返回 `meta` 对象。

### 2.6 种子筛选参数（`GET /seeds`）

| 参数 | 类型 | 说明 |
|------|------|------|
| `edition` | `string` | `java` \| `bedrock` |
| `version` | `string` | 版本号。两段式（如 `1.21`）→ 模糊匹配 `1.21.%` 全部小版本；三段式（如 `1.21.4`）→ 精确匹配 |
| `world_type` | `string` | `normal` \| `large_biomes` \| `superflat` |
| `tags` | `string` | 逗号分隔的 tag key，如 `survival,village`（AND 逻辑） |
| `mod_env` | `string` | `vanilla` \| `modpack` \| `neoforge` |
| `sort` | `string` | `popular`（默认）\| `newest` \| `most_liked` \| `most_collected` |
| `q` | `string` | 关键词，匹配 title + description（ILIKE） |
| `page` | `int` | 页码，默认 1 |
| `page_size` | `int` | 每页条数，默认 24 |

> **勘误（2026-05-28）**：初版设计中 `version` 仅支持精确匹配（三段式），缺少 `world_type` 筛选参数。新增：① `version` 支持两段式模糊匹配（`1.21` → 全部 `1.21.x`）；② `world_type` 参数，因世界类型（普通/大型群系/超平坦）直接影响种子可用性，应在 MVP 阶段支持筛选。

---

## 3. 认证相关 (Auth)

### 3.1 `GET /auth/login`

重定向到 Microsoft OAuth 授权页。

```
Response: 302 Found
Location: https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize
            ?client_id={CLIENT_ID}
            &response_type=code
            &redirect_uri={REDIRECT_URI}
            &scope=XboxLive.signin%20offline_access
            &state={random_state}
```

`state` 参数由后端生成，存入 Redis / 签名的 cookie，回调时校验防 CSRF。`redirect_uri` 可携带 `?redirect={frontend_path}` 参数，回调后前端跳回该路径。

### 3.2 `GET /auth/callback`

Microsoft 重定向回此端点。后端执行完整验证链：

```
Query: ?code={authorization_code}&state={state}

后端处理:
  1. 校验 state
  2. POST /consumers/oauth2/v2.0/token → access_token, refresh_token
  3. POST /user.auth.xboxlive.com/user/authenticate → xbl_token
  4. POST /xsts.auth.xboxlive.com/xsts/authorize → xsts_token, xuid
  5. POST /api.minecraftservices.com/authentication/login → mc_access_token
  6. GET  /api.minecraftservices.com/entitlements/mcstore → 是否拥有 Java 版
  7. GET  /api.minecraftservices.com/minecraft/profile → uuid, name
  8. UPSERT users (microsoft_id 为唯一键)
  9. 签发 JWT，设置 Cookie
  10. 302 重定向到前端首页（或 redirect 参数指定的路径）

Response: 302 Found → 前端首页
Set-Cookie: seedvault_token=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800
```

### 3.3 `POST /auth/logout`

```
Response: 200 OK
Set-Cookie: seedvault_token=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0

Body:
{
  "data": { "message": "已退出登录" }
}
```

### 3.4 `GET /auth/me`

```
需登录: 是

Response 200:
{
  "data": {
    "id": 1,
    "display_name": "Kaleid_5coper",
    "minecraft_uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "minecraft_username": "Kaleid_5coper",
    "owns_java_edition": true,
    "avatar_url": "https://mc-heads.net/avatar/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/80",
    "role": "user",
    "unread_count": 3,
    "created_at": "2026-05-27T12:00:00Z"
  }
}

Response 401: 未登录或 JWT 过期
```

---

## 4. 种子相关 (Seeds)

### 4.1 `GET /seeds`

```
Query: edition, version, world_type, tags, mod_env, sort, q, page, page_size (全部可选)

**`version` 参数行为**（勘误（2026-05-28）补充）：
- 两段式（如 `1.21`）→ 大版本模糊匹配，返回所有 `tested_version LIKE '1.21.%'` 的种子
- 三段式（如 `1.21.4`）→ 精确匹配，仅返回 `tested_version = '1.21.4'` 的种子
- 前端版本筛选器默认展示大版本，展开后可选择精确小版本

Response 200:
{
  "data": [
    {
      "id": 42,
      "title": "古代城市出生点",
      "description_preview": "出生点正下方就是一座完整的古代城市...",
      "cover_url": "/uploads/screenshots/2026-05/abc123.webp",
      "seed_value": "123456789",
      "edition": "java",
      "tested_version": "1.21.4",
      "tags": [
        { "key": "survival", "label": "生存", "icon": "🏕️" },
        { "key": "ancient_city", "label": "古代城市", "icon": "🏛️" }
      ],
      "like_count": 42,
      "collection_count": 15,
      "view_count": 1234,
      "is_liked": false,
      "uploader": {
        "id": 1,
        "display_name": "Kaleid_5coper",
        "minecraft_username": "Kaleid_5coper",
        "avatar_url": "https://mc-heads.net/avatar/xxx/24",
        "owns_java_edition": true
      },
      "created_at": "2026-05-27T12:00:00Z"
    }
  ],
  "meta": { "page": 1, "page_size": 24, "total": 142, "pages": 6 }
}
```

`is_liked`：若已登录则返回当前用户是否已点赞此种子；未登录时为 `false`。浏览页种子上方心形图标据此显示实心/空心状态。

**排序算法说明**：
- `popular`（默认）：热度分 = `(like_count × 0.7 + view_count × 0.3) / (hours_since_created + 4) ^ 1.2`。新种子有冷启动保护（分母 +4），旧种子随时间自然降权。
- `newest`：纯按 `created_at DESC`。
- `most_liked`：纯按 `like_count DESC`。
- `most_collected`：纯按 `collection_count DESC`。

### 4.2 `GET /seeds/{id}`

```
Response 200:
{
  "data": {
    "id": 42,
    "title": "古代城市出生点",
    "description": "出生点正下方就是一座完整的古代城市，坐标为...\n\n附带了三个关键坐标。",
    "seed_value": "123456789",
    "edition": "java",
    "tested_version": "1.21.4",
    "compatible_range": "1.21.4 ~ 1.21.5",
    "world_type": "normal",
    "mod_env": "vanilla",
    "modpack_name": null,
    "modpack_version": null,
    "spawn_x": 0,
    "spawn_z": 64,
    "status": "approved",
    "screenshots": [
      { "id": 1, "url": "/uploads/screenshots/2026-05/abc123.webp", "is_cover": true, "sort_order": 0 },
      { "id": 2, "url": "/uploads/screenshots/2026-05/def456.webp", "is_cover": false, "sort_order": 1 }
    ],
    "key_coords": [
      { "id": 1, "label": "古代城市入口", "x": 120, "y": -30, "z": 64 },
      { "id": 2, "label": "末地传送门", "x": 800, "y": null, "z": 32 }
    ],
    "tags": [
      { "key": "survival", "label": "生存", "icon": "🏕️" },
      { "key": "ancient_city", "label": "古代城市", "icon": "🏛️" }
    ],
    "like_count": 42,
    "collection_count": 15,
    "view_count": 1235,
    "is_liked": false,
    "uploader": {
      "id": 1,
      "display_name": "Kaleid_5coper",
      "minecraft_username": "Kaleid_5coper",
      "avatar_url": "https://mc-heads.net/avatar/xxx/80",
      "owns_java_edition": true
    },
    "created_at": "2026-05-27T12:00:00Z"
  }
}

Response 404:
{
  "error": { "code": "SEED_NOT_FOUND", "message": "该种子不存在或已被删除" }
}
```

`is_liked`：若已登录则返回当前用户是否已点赞此种子；未登录则为 `false`。每次访问 `view_count + 1`（同一 session 30 分钟内不重复计数）。

### 4.3 `POST /seeds`

```
需登录: 是
Content-Type: application/json

Request Body:
{
  "seed_value": "123456789",
  "edition": "java",
  "tested_version": "1.21.4",
  "compatible_range": "1.21.4 ~ 1.21.5",
  "world_type": "normal",
  "mod_env": "vanilla",
  "modpack_name": null,
  "modpack_version": null,
  "spawn_x": 0,
  "spawn_z": 64,
  "title": "古代城市出生点",
  "description": "出生点正下方就是一座完整的古代城市...",
  "tags": ["survival", "ancient_city"],
  "key_coords": [
    { "label": "古代城市入口", "x": 120, "y": -30, "z": 64 },
    { "label": "末地传送门", "x": 800, "z": 32 }
  ],
  "screenshot_ids": [1, 2, 3]
}

Response 201:
{
  "data": { "id": 42, "status": "pending", "message": "投稿已提交，等待审核" }
}

Response 409 (重复投稿):
{
  "error": {
    "code": "DUPLICATE_SEED",
    "message": "该种子（相同版本端 + 版本号 + 种子值）已有投稿",
    "existing_id": 17
  }
}

Response 422 (校验失败示例):
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "种子值超出 32 位范围，在基岩版 < 1.18.20 中将被截断",
    "details": { ... }
  }
}
```

`screenshot_ids` 引用已通过 `POST /upload/screenshot` 上传的图片 ID（未关联种子的临时上传，投稿时将图片关联到种子）。

服务端校验清单见 §14.3。

### 4.4 `POST /seeds/{id}/like`

```
需登录: 是

Request Body: 无

Response 200 (点赞):
{
  "data": { "liked": true, "like_count": 43 }
}

Response 200 (取消):
{
  "data": { "liked": false, "like_count": 42 }
}
```

同一用户对同一种子只能点一次赞。首次请求 → 点赞，再次请求 → 取消（toggle 模式）。

### 4.5 `POST /seeds/{id}/report`

```
需登录: 否（登录后举报关联用户，便于管理员追问）

Request Body:
{
  "reason": "screenshot_mismatch",       // 'screenshot_mismatch' | 'wrong_version'
                                         // | 'duplicate' | 'inappropriate' | 'other'
  "detail": "截图中显示的地形与描述不符"   // 可选, ≤ 500 字符
}

Response 201:
{
  "data": { "message": "举报已提交，感谢您的贡献" }
}
```

同一用户对同一种子多次举报自动合并（upsert by `(reporter_id, seed_id)`，若匿名则以 IP hash 代替 reporter_id）。管理员在审核后台中查看举报列表。

---

## 5. 评论相关 (Comments)

### 5.1 `GET /seeds/{id}/comments`

```
Query: page (默认 1), page_size (默认 20)

Response 200:
{
  "data": [
    {
      "id": 1,
      "content": "这个种子太棒了！出生点就在古城旁边。",
      "author": {
        "id": 2,
        "display_name": "Player2",
        "minecraft_username": "Player2",
        "avatar_url": "https://mc-heads.net/avatar/yyy/28",
        "owns_java_edition": false
      },
      "created_at": "2026-05-28T08:00:00Z"
    }
  ],
  "meta": { "page": 1, "page_size": 20, "total": 3, "pages": 1 }
}
```

评论按 `created_at ASC` 排序（最早 → 最新），不做嵌套。

### 5.2 `POST /seeds/{id}/comments`

```
需登录: 是

Request Body:
{
  "content": "这个种子太棒了！"
}

Response 201:
{
  "data": {
    "id": 1,
    "content": "这个种子太棒了！",
    "author": { ... },
    "created_at": "2026-05-28T08:00:00Z"
  }
}
```

`content` 限制：1-1000 字符，支持 Markdown（链接、粗体、代码块），不支持图片。

### 5.3 `DELETE /seeds/{id}/comments/{comment_id}`

```
需登录: 是（仅可删除自己的评论，管理员可删除任意评论）

Response 200:
{
  "data": { "message": "评论已删除" }
}

Response 403 (删除他人评论):
{
  "error": { "code": "FORBIDDEN", "message": "只能删除自己的评论" }
}
```

软删除（`deleted_at` 字段）。已删除的评论在列表中显示为 "[该评论已被作者删除]"。

---

## 6. 图片上传 (Upload)

### 6.1 `POST /upload/screenshot`

```
需登录: 是
Content-Type: multipart/form-data

Request Body:
  file: 图片文件 (binary)

限制:
  - 格式: JPG, PNG, WebP
  - 单张 ≤ 5MB
  - 每次上传 1 张（前端并发多次调用）

Response 201:
{
  "data": {
    "id": 1,
    "url": "/uploads/screenshots/2026-05/abc123.webp"
  }
}

Response 413 (文件过大):
{
  "error": { "code": "FILE_TOO_LARGE", "message": "图片不能超过 5MB" }
}

Response 422 (格式不支持):
{
  "error": { "code": "UNSUPPORTED_FORMAT", "message": "仅支持 JPG、PNG、WebP" }
}
```

上传后图片存储在临时目录，`status = 'pending'`。投稿成功（POST /seeds）后，后端将图片关联到种子并将状态改为 `active`。未被关联的临时图片每周定时清理。

前端在投稿表单中先调用此端点上传所有截图，再将返回的 `id` 数组填入 `POST /seeds` 的 `screenshot_ids`。

---

## 7. 标签 (Tags)

### 7.1 `GET /tags`

```
无需登录

Response 200:
{
  "data": [
    { "key": "survival", "label": "生存向", "icon": "🏕️", "category": "gameplay" },
    { "key": "speedrun", "label": "速通向", "icon": "⚔️", "category": "gameplay" },
    { "key": "building", "label": "建筑向", "icon": "🏗️", "category": "gameplay" },
    { "key": "hardcore", "label": "极限模式", "icon": "💀", "category": "gameplay" },
    { "key": "challenge", "label": "挑战向", "icon": "🎯", "category": "gameplay" },
    { "key": "spawn_wonder", "label": "出生点奇观", "icon": "🌄", "category": "feature" },
    { "key": "rare_biome", "label": "稀有群系", "icon": "🍄", "category": "feature" },
    { "key": "terrain", "label": "地形奇观", "icon": "🏔️", "category": "feature" },
    { "key": "village", "label": "近出生点村庄", "icon": "🏘️", "category": "feature" },
    { "key": "stronghold", "label": "近出生点要塞", "icon": "🏰", "category": "feature" },
    { "key": "ancient_city", "label": "古代城市", "icon": "🏛️", "category": "feature" },
    { "key": "trial_chamber", "label": "试炼室集群", "icon": "⚗️", "category": "feature" },
    { "key": "diamond", "label": "资源富集", "icon": "💎", "category": "feature" },
    { "key": "island", "label": "孤岛生存", "icon": "🌊", "category": "feature" }
  ]
}
```

标签由管理员在数据库初始化时预置（seed data），前端不提供增删标签的界面。三种特殊标签（`verified` / `hot` / `new`）是系统计算字段，不出现在此列表中。

---

## 8. 版本号 (Versions)

### 8.1 `GET /versions`

```
无需登录

Query: edition (可选, 'java' | 'bedrock')

Response 200:
{
  "data": [
    { "id": 1, "edition": "java", "version": "1.21.5", "is_latest": true, "sort_order": 100 },
    { "id": 2, "edition": "java", "version": "1.21.4", "is_latest": false, "sort_order": 99 },
    { "id": 3, "edition": "bedrock", "version": "1.21.60", "is_latest": true, "sort_order": 100 }
  ]
}
```

返回前端筛选器和投稿表单下拉使用的版本列表。按 `sort_order DESC` 排列。`is_latest` 由管理员维护。

---

## 9. 用户相关 (Users)

### 9.1 `GET /users/{user_id}`

```
无需登录

Response 200:
{
  "data": {
    "id": 1,
    "display_name": "Kaleid_5coper",
    "minecraft_username": "Kaleid_5coper",
    "avatar_url": "https://mc-heads.net/avatar/xxx/80",
    "owns_java_edition": true,
    "approved_seed_count": 5,
    "created_at": "2026-05-27T12:00:00Z"
  }
}
```

### 9.2 `GET /users/me/seeds`

```
需登录: 是
Query: status (可选, 'approved' | 'pending' | 'rejected'), page, page_size

Response 200:
{
  "data": [ ...SeedListItem ],
  "meta": { ... }
}
```

返回当前登录用户提交的种子。默认按 `created_at DESC`。

### 9.3 `GET /users/me/bookmarks`

> **勘误（2026-05-28）**：端点命名 `bookmarks` 与收藏夹（`collections`）在英文语义上容易混淆——两者都暗示"保存/收藏"。此端点查询的是 `likes` 表（点赞记录），语义是"我赞过的即我想再次找到的"。若未来用户反馈命名混乱，可重命名为 `GET /users/me/likes`，与 `POST /seeds/{id}/like` 保持动词/名词一致。当前保留 `bookmarks` 命名，前端文案使用"我赞过的"以区分于"收藏夹"。

```
需登录: 是
Query: page, page_size

Response 200:
{
  "data": [ ...SeedListItem ],
  "meta": { ... }
}
```

返回当前用户点赞过的种子（"我赞过的"即"我想再次找到的"）。

### 9.4 匿名书签合并

未登录用户在本地 `localStorage` 中保存书签（`seedvault_bookmarks`，种子 ID 数组）。首次登录成功后：

1. OAuth 回调返回的 JWT payload 中附加 `merge_count` 字段——前端据此知道等待合并
2. 前端在收到 `/auth/me` 后，将本地 `seedvault_bookmarks` 数组 POST 到 `POST /users/me/bookmarks/merge`
3. 服务端逐条执行 `INSERT OR IGNORE INTO likes (user_id, seed_id)`，更新 `seeds.like_count`
4. 完成后前端清除 `localStorage` 中的 `seedvault_bookmarks`

```
POST /users/me/bookmarks/merge
需登录: 是

Request Body:
{
  "seed_ids": [42, 17, 108]
}

Response 200:
{
  "data": { "merged_count": 3, "message": "已合并 3 条收藏" }
}
```

---

## 10. 通知 (Notifications)

### 10.1 `GET /notifications`

```
需登录: 是
Query: page (默认 1), page_size (默认 20)

Response 200:
{
  "data": [
    {
      "id": 1,
      "type": "seed_approved",
      "message": "您的投稿「古代城市出生点」已通过审核",
      "seed_id": 42,
      "is_read": false,
      "created_at": "2026-05-28T14:00:00Z"
    },
    {
      "id": 2,
      "type": "seed_rejected",
      "message": "您的投稿「测试种子」未通过审核",
      "detail": "截图与描述不符",
      "seed_id": 43,
      "is_read": true,
      "created_at": "2026-05-28T10:00:00Z"
    }
  ],
  "meta": { ... }
}
```

通知类型：

| type | 触发事件 |
|------|---------|
| `seed_approved` | 投稿通过审核 |
| `seed_rejected` | 投稿被拒绝（`detail` 包含拒绝原因） |

通知为**被动拉取**模式（非推送）。前端在以下时机拉取：用户登录后（`GET /auth/me` 的响应中包含 `unread_count`）、用户主动点击通知图标时。

### 10.2 `POST /notifications/{id}/read`

```
需登录: 是

Response 200:
{
  "data": { "id": 1, "is_read": true }
}
```

标记单条通知为已读。

---

## 11. 收藏夹 (Collections)

### 10.1 `GET /collections`

```
需登录: 是

Response 200:
{
  "data": [
    {
      "id": 1,
      "name": "1.21.4 生存好种",
      "description": "适合开新档的种子",
      "cover_url": "/uploads/screenshots/2026-05/def456.webp",
      "seed_count": 12,
      "is_public": false,
      "sort_order": 0,
      "created_at": "2026-05-28T12:00:00Z",
      "updated_at": "2026-05-30T08:00:00Z"
    }
  ]
}
```

返回当前用户的所有收藏夹，按 `sort_order, created_at DESC` 排列。`cover_url` 根据 `cover_strategy` 动态计算（见 §10.3）。

### 10.2 `POST /collections`

```
需登录: 是

Request Body:
{
  "name": "1.21.4 生存好种",
  "description": "适合开新档的种子",
  "is_public": false
}

Response 201:
{
  "data": {
    "id": 1,
    "name": "1.21.4 生存好种",
    "description": "适合开新档的种子",
    "cover_url": null,
    "seed_count": 0,
    "is_public": false,
    "sort_order": 0,
    "created_at": "2026-05-28T12:00:00Z",
    "updated_at": null
  }
}
```

`name` 必填（1-50 字符）。`description` 可选（≤ 200 字符）。新收藏夹默认 `cover_strategy = 'last'`，初始 `cover_url = null`（无种子时无封面）。

### 10.3 `GET /collections/{id}`

```
Query: page (默认 1), page_size (默认 24)

Response 200:
{
  "data": {
    "id": 1,
    "name": "1.21.4 生存好种",
    "description": "适合开新档的种子",
    "cover_strategy": "last",
    "cover_seed_id": null,
    "cover_url": "/uploads/screenshots/2026-05/def456.webp",
    "is_public": true,
    "owner": {
      "id": 1,
      "display_name": "Kaleid_5coper",
      "minecraft_username": "Kaleid_5coper",
      "avatar_url": "https://mc-heads.net/avatar/xxx/28",
      "owns_java_edition": true
    },
    "seeds": [ ...SeedListItem ],
    "meta": { "page": 1, "page_size": 24, "total": 12, "pages": 1 }
  }
}
```

无需登录即可访问公开收藏夹。私有收藏夹仅所有者可查看（否则 403）。

`cover_url` 计算逻辑（后端 Service 层）：
- `cover_strategy = 'first'` → 取 `MIN(added_at)` 种子的封面
- `cover_strategy = 'last'`（默认）→ 取 `MAX(added_at)` 种子的封面
- `cover_strategy = 'manual'` → 取 `cover_seed_id` 对应种子的封面
- 如果收藏夹为空 → `cover_url = null`

### 10.4 `PUT /collections/{id}`

```
需登录: 是（仅所有者可编辑）

Request Body（所有字段可选，只发送要更新的字段）:
{
  "name": "新名称",
  "description": "新描述",
  "cover_strategy": "manual",
  "cover_seed_id": 42,
  "is_public": true,
  "sort_order": 1
}

Response 200:
{
  "data": {
    "id": 1,
    "name": "新名称",
    ...
  }
}
```

校验：
- `cover_strategy = 'manual'` 时 `cover_seed_id` 必填且必须属于此收藏夹
- `cover_strategy` 切换为 `'first'` 或 `'last'` 时 `cover_seed_id` 被忽略（设为 NULL）
- `name` 变更时如为空则拒绝

### 10.5 `DELETE /collections/{id}`

```
需登录: 是（仅所有者可删除）

Response 200:
{
  "data": { "message": "收藏夹已删除" }
}
```

级联删除所有 `collection_seeds` 关联。

### 10.6 `POST /collections/{id}/seeds/{seed_id}`

```
需登录: 是（仅所有者可添加）

Request Body: 无

Response 201:
{
  "data": {
    "collection_id": 1,
    "seed_id": 42,
    "added_at": "2026-05-30T10:00:00Z"
  }
}

Response 409 (已在收藏夹中):
{
  "error": { "code": "ALREADY_IN_COLLECTION", "message": "该种子已在此收藏夹中" }
}
```

注意：此操作与 `POST /seeds/{id}/like` 正交。用户可以点赞而不归档，也可以归档而不点赞。

服务端在插入 `collection_seeds` 记录后同步执行 `UPDATE seeds SET collection_count = collection_count + 1 WHERE id = ?`。

### 10.7 `DELETE /collections/{id}/seeds/{seed_id}`

```
需登录: 是（仅所有者可移除）

Response 200:
{
  "data": { "message": "种子已从收藏夹移除" }
}
```

移除后若 `cover_strategy = 'manual'` 且 `cover_seed_id = seed_id`，自动将 `cover_strategy` 回退为 `'last'`（`cover_seed_id` 设为 NULL），避免悬空引用。

服务端在删除 `collection_seeds` 记录后同步执行 `UPDATE seeds SET collection_count = MAX(collection_count - 1, 0) WHERE id = ?`。

---

## 12. 管理后台 (Admin)

所有 `/admin/*` 端点要求 `role = 'admin'`。

### 12.1 `GET /admin/seeds/pending`

```
需管理员: 是
Query: page, page_size

Response 200:
{
  "data": [
    {
      "id": 43,
      "title": "...",
      "seed_value": "...",
      "edition": "java",
      "tested_version": "1.21.4",
      "cover_url": "...",
      "uploader": { ... },
      "created_at": "..."
    }
  ],
  "meta": { ... }
}
```

### 12.2 `POST /admin/seeds/{id}/approve`

```
需管理员: 是

Request Body: 无

Response 200:
{
  "data": { "id": 43, "status": "approved", "message": "审核已通过" }
}
```

### 12.3 `POST /admin/seeds/{id}/reject`

```
需管理员: 是

Request Body:
{
  "reason": "截图与描述不符，出生点附近无古代城市"
}

Response 200:
{
  "data": { "id": 43, "status": "rejected", "reason": "截图与描述不符，出生点附近无古代城市" }
}
```

`reason` 字段存储进 `rejection_reason` 列，供投稿者在"我的投稿"中查看。

### 12.4 `GET /admin/users`

```
需管理员: 是
Query: q (搜索用户名/Microsoft邮箱), page, page_size

Response 200:
{
  "data": [
    {
      "id": 1,
      "display_name": "...",
      "email": "...",
      "minecraft_username": "...",
      "owns_java_edition": true,
      "role": "user",
      "is_banned": false,
      "seed_count": 5,
      "created_at": "..."
    }
  ],
  "meta": { ... }
}
```

### 12.5 `POST /admin/users/{id}/ban`

```
需管理员: 是

Request Body:
{
  "banned": true,
  "reason": "多次提交虚假种子"
}

Response 200:
{
  "data": { "id": 1, "is_banned": true, "message": "用户已被封禁" }
}
```

`banned: false` 为解封操作。被禁用户不可登录（JWT 签发时检查 `is_banned` 字段）。

### 12.6 `POST /admin/versions`

```
需管理员: 是

Request Body:
{
  "edition": "java",
  "version": "1.21.6",
  "is_latest": true
}

Response 201:
{
  "data": { "id": 4, "edition": "java", "version": "1.21.6", "message": "版本号已添加" }
}
```

若 `is_latest: true`，后端自动将同 `edition` 的其他版本设为 `is_latest: false`。

### 12.7 `DELETE /admin/versions/{id}`

```
需管理员: 是

Response 200:
{
  "data": { "message": "版本号已删除" }
}
```

---

## 13. 请求/响应 Schemas

以下为 Pydantic 模型形状。所有 datetime 字段以 ISO 8601 字符串传输。

### 13.1 UserBrief（列表/卡片中的投稿者摘要）

```
{
  id: int,
  display_name: str,
  minecraft_username: str | null,
  avatar_url: str,
  owns_java_edition: bool
}
```

`avatar_url` 推导逻辑（服务端）：
1. 若 `minecraft_uuid` 非空 → `https://mc-heads.net/avatar/{uuid}/{size}`
2. 否则调用 Microsoft Graph `GET /me/photo/$value`，若存在则返回该 URL（需缓存）
3. 否则返回 `null`，前端降级为首字母头像

### 13.2 SeedListItem（列表/卡片中的种子摘要）

```
{
  id: int,
  title: str,
  description_preview: str,        // 前 120 字符
  cover_url: str,
  seed_value: str,
  edition: str,
  tested_version: str,
  tags: list[TagBrief],
  like_count: int,
  collection_count: int,
  view_count: int,
  is_liked: bool,                   // 已登录时返回真实状态，未登录时 false
  uploader: UserBrief,
  created_at: datetime
}
```

### 13.3 SeedDetail（详情页完整种子）

```
{
  id: int,
  title: str,
  description: str,               // 全文
  seed_value: str,
  edition: str,
  tested_version: str,
  compatible_range: str | null,
  world_type: str,
  mod_env: str,
  modpack_name: str | null,
  modpack_version: str | null,
  spawn_x: int,
  spawn_z: int,
  status: str,
  screenshots: list[Screenshot],
  key_coords: list[KeyCoord],
  tags: list[TagBrief],
  like_count: int,
  collection_count: int,
  view_count: int,
  is_liked: bool,
  uploader: UserBrief,
  created_at: datetime
}
```

### 13.4 SeedCreate（投稿请求体）

```
{
  seed_value: str,                 // 必填, 1-64 字符，允许文本种子
  edition: str,                    // 'java' | 'bedrock'
  tested_version: str,             // 必填
  compatible_range: str | null,
  world_type: str,                 // 'normal' | 'large_biomes' | 'superflat'
  mod_env: str,                    // 'vanilla' | 'modpack' | 'neoforge'
  modpack_name: str | null,        // mod_env='modpack' 时必填
  modpack_version: str | null,
  spawn_x: int,                    // 必填
  spawn_z: int,                    // 必填
  title: str,                      // 1-50 字符
  description: str,                // 1-500 字符
  tags: list[str],                 // tag key 列表，至少 1 个 gameplay 类 tag
  key_coords: list[KeyCoordInput],
  screenshot_ids: list[int]        // 1-5 个，来自 POST /upload/screenshot
}
```

### 13.5 KeyCoord / KeyCoordInput

```
// 响应
{ id: int, label: str, x: int, y: int | null, z: int }

// 请求
{ label: str, x: int, y: int | null, z: int }
```

`label` 限制 1-30 字符。`y` 可选（水平坐标，"出生点高度无意义故可不填"）。

### 13.6 TagBrief

```
{ key: str, label: str, icon: str }
```

例：`{ "key": "survival", "label": "生存向", "icon": "🏕️" }`

### 13.7 Screenshot

```
{ id: int, url: str, is_cover: bool, sort_order: int }
```

### 13.8 Comment / CommentInput

```
// 响应
{ id: int, content: str, author: UserBrief, created_at: datetime }

// 请求
{ content: str }    // 1-1000 字符
```

### 13.9 UserProfile（用户主页）

```
{
  id: int,
  display_name: str,
  minecraft_username: str | null,
  avatar_url: str,
  owns_java_edition: bool,
  approved_seed_count: int,
  created_at: datetime
}
```

### 13.10 PaginationMeta

```
{ page: int, page_size: int, total: int, pages: int }
```

### 13.11 CollectionSummary（收藏夹列表项）

```
{
  id: int,
  name: str,                       // 1-50 字符
  description: str | null,         // ≤ 200 字符
  cover_url: str | null,           // 动态计算
  seed_count: int,
  is_public: bool,
  sort_order: int,
  created_at: datetime,
  updated_at: datetime | null
}
```

### 13.12 CollectionDetail（收藏夹详情）

```
{
  id: int,
  name: str,
  description: str | null,
  cover_strategy: str,             // 'first' | 'last' | 'manual'
  cover_seed_id: int | null,       // 仅 manual 时有值
  cover_url: str | null,
  is_public: bool,
  owner: UserBrief,
  seeds: list[SeedListItem],       // 分页
  meta: PaginationMeta
}
```

### 13.13 CollectionCreate（创建收藏夹请求体）

```
{
  name: str,                       // 必填, 1-50 字符
  description: str | null,         // 可选, ≤ 200 字符, 默认 null
  is_public: bool                  // 可选, 默认 false（与 DB DEFAULT 一致）
}
```

### 13.14 CollectionUpdate（编辑收藏夹请求体）

```
{
  name: str | null,                // 所有字段可选
  description: str | null,
  cover_strategy: str | null,      // 'first' | 'last' | 'manual'
  cover_seed_id: int | null,       // cover_strategy='manual' 时必填
  is_public: bool | null,
  sort_order: int | null
}
```

---

## 14. 数据库 DDL

所有字段类型为 SQLite 兼容。部署至 PostgreSQL 时仅需调整 `AUTOINCREMENT` → `SERIAL`、`BOOLEAN` → `BOOLEAN NOT NULL DEFAULT FALSE` 等细微差异。

### 14.1 users

```sql
CREATE TABLE users (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  microsoft_id       VARCHAR(64) UNIQUE NOT NULL,
  email              VARCHAR(255),
  display_name       VARCHAR(128) NOT NULL,
  minecraft_uuid     VARCHAR(36) UNIQUE,
  minecraft_username VARCHAR(64),
  owns_java_edition  BOOLEAN NOT NULL DEFAULT FALSE,
  skin_model         VARCHAR(8),                -- 'steve' | 'alex'
  role               VARCHAR(16) NOT NULL DEFAULT 'user',  -- 'user' | 'admin'
  is_banned          BOOLEAN NOT NULL DEFAULT FALSE,
  microsoft_refresh_token TEXT,                 -- 加密存储
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at      DATETIME
);

CREATE INDEX idx_users_microsoft_id ON users(microsoft_id);
CREATE INDEX idx_users_minecraft_uuid ON users(minecraft_uuid);
```

### 14.2 seeds

```sql
CREATE TABLE seeds (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  title              VARCHAR(50) NOT NULL,
  description        VARCHAR(500) NOT NULL,
  seed_value         VARCHAR(64) NOT NULL,       -- 字符串存储（保留原始输入）
  seed_numeric       BIGINT,                      -- 解析后的 64 位整数（纯数字种子，文本种子为 NULL）
  edition            VARCHAR(16) NOT NULL,        -- 'java' | 'bedrock'
  tested_version     VARCHAR(16) NOT NULL,
  compatible_range   VARCHAR(32),                 -- '1.21.4 ~ 1.21.5'
  world_type         VARCHAR(16) NOT NULL DEFAULT 'normal'
                      CHECK (world_type IN ('normal', 'large_biomes', 'superflat')),
  mod_env            VARCHAR(16) NOT NULL DEFAULT 'vanilla'
                      CHECK (mod_env IN ('vanilla', 'modpack', 'neoforge')),
  modpack_name       VARCHAR(128),
  modpack_version    VARCHAR(32),
  spawn_x            INTEGER NOT NULL,
  spawn_z            INTEGER NOT NULL,
  status             VARCHAR(16) NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
  rejection_reason   VARCHAR(500),
  uploader_id        INTEGER NOT NULL REFERENCES users(id),
  view_count         INTEGER NOT NULL DEFAULT 0,
  like_count         INTEGER NOT NULL DEFAULT 0,
  collection_count   INTEGER NOT NULL DEFAULT 0,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME,
  approved_at        DATETIME,
  approved_by        INTEGER REFERENCES users(id)
);

CREATE UNIQUE INDEX idx_seeds_unique ON seeds(seed_value, edition, tested_version)
  WHERE status != 'rejected';                    -- 部分唯一索引：拒绝的种子不阻塞重新投稿（SQLite ≥3.8.0 及 PostgreSQL 均支持）

CREATE INDEX idx_seeds_status ON seeds(status);
CREATE INDEX idx_seeds_edition_version ON seeds(edition, tested_version);
CREATE INDEX idx_seeds_uploader ON seeds(uploader_id);
CREATE INDEX idx_seeds_created ON seeds(created_at DESC);
CREATE INDEX idx_seeds_likes ON seeds(like_count DESC);
CREATE INDEX idx_seeds_collections ON seeds(collection_count DESC);
```

> **勘误（2026-05-28）**：① `seed_numeric BIGINT` 在 SQLite 中无独立 `BIGINT` 类型——SQLite 的 `INTEGER` 即 64 位有符号整数，`BIGINT` 被作为 INTEGER affinity 处理，存储无差异。迁移至 PostgreSQL 时改为原生 `BIGINT`。SQLAlchemy 的 `BigInteger` 类型在两个方言上自动适配。② `seed_numeric` 的用途是存储 `seed_value` 解析后的规范 64 位整数值（文本种子为 NULL），与字符串形式的 `seed_value` 互补。写入路径：`POST /seeds` 服务层在创建种子记录时解析并填充。读取路径：MVP 阶段无 API 端点消费此字段做筛选或排序——它预留给未来的数值范围查询和数值排序功能。

### 14.3 screenshots

```sql
CREATE TABLE screenshots (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  seed_id     INTEGER REFERENCES seeds(id) ON DELETE CASCADE,
  uploader_id INTEGER NOT NULL REFERENCES users(id),
  file_path   VARCHAR(512) NOT NULL,              -- 相对路径或 S3 key
  is_cover    BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  status      VARCHAR(16) NOT NULL DEFAULT 'pending',  -- 'pending' | 'active' | 'orphaned'
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_screenshots_seed ON screenshots(seed_id);
CREATE INDEX idx_screenshots_uploader ON screenshots(uploader_id);
```

### 14.4 key_coords

```sql
CREATE TABLE key_coords (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  seed_id INTEGER NOT NULL REFERENCES seeds(id) ON DELETE CASCADE,
  label   VARCHAR(30) NOT NULL,
  x       INTEGER NOT NULL,
  y       INTEGER,
  z       INTEGER NOT NULL
);

CREATE INDEX idx_key_coords_seed ON key_coords(seed_id);
```

### 14.5 tags

```sql
CREATE TABLE tags (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  key      VARCHAR(32) UNIQUE NOT NULL,
  label    VARCHAR(32) NOT NULL,
  icon     VARCHAR(8),          -- emoji
  category VARCHAR(16) NOT NULL  -- 'gameplay' | 'feature' | 'special'
);
```

### 14.6 seed_tags

```sql
CREATE TABLE seed_tags (
  seed_id INTEGER NOT NULL REFERENCES seeds(id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (seed_id, tag_id)
);
```

### 14.7 likes

```sql
CREATE TABLE likes (
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  seed_id    INTEGER NOT NULL REFERENCES seeds(id) ON DELETE CASCADE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, seed_id)
);
```

点赞和收藏是两个独立语义。此表仅存储点赞关系。`GET /users/me/bookmarks` 读取此表（"我赞过的"即"我想再次找到的"）。自定义收藏夹见 `collections` 和 `collection_seeds` 表。

### 14.8 comments

```sql
CREATE TABLE comments (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  seed_id    INTEGER NOT NULL REFERENCES seeds(id) ON DELETE CASCADE,
  author_id  INTEGER NOT NULL REFERENCES users(id),
  content    VARCHAR(1000) NOT NULL,
  deleted_at DATETIME,                            -- NULL = 未删除
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_comments_seed ON comments(seed_id, created_at);
```

### 14.9 versions（管理员维护的版本号表）

```sql
CREATE TABLE versions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  edition    VARCHAR(16) NOT NULL,     -- 'java' | 'bedrock'
  version    VARCHAR(16) NOT NULL,
  is_latest  BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  UNIQUE (edition, version)
);
```

### 14.10 seed_views（浏览去重）

```sql
CREATE TABLE seed_views (
  seed_id     INTEGER NOT NULL REFERENCES seeds(id) ON DELETE CASCADE,
  session_key VARCHAR(64) NOT NULL,
  viewed_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_seed_views_lookup ON seed_views(seed_id, session_key, viewed_at);
```

同一 `(seed_id, session_key)` 在 30 分钟内不重复计数。`session_key` 使用 `HMAC(seed_id + user_ip + user_agent)` 以避免存储 IP 明文。定期清理超过 30 分钟的记录。

**IP 获取**：服务端从 `X-Forwarded-For` 头部取最左侧 IP（当部署在反向代理/CDN 后），若无则取 `X-Real-IP`，再 fallback 到直连 IP。FastAPI 通过 `request.client.host` + 中间件解析代理头部实现。

### 14.11 collections

```sql
CREATE TABLE collections (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name           VARCHAR(50) NOT NULL,
  description    VARCHAR(200),
  cover_strategy VARCHAR(16) NOT NULL DEFAULT 'last'
                 CHECK (cover_strategy IN ('first', 'last', 'manual')),
  cover_seed_id  INTEGER REFERENCES seeds(id) ON DELETE SET NULL,
  is_public      BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order     INTEGER NOT NULL DEFAULT 0,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME
);

CREATE INDEX idx_collections_user ON collections(user_id, sort_order);
```

### 14.12 collection_seeds

```sql
CREATE TABLE collection_seeds (
  collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  seed_id       INTEGER NOT NULL REFERENCES seeds(id) ON DELETE CASCADE,
  added_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (collection_id, seed_id)
);

CREATE INDEX idx_collection_seeds_coll ON collection_seeds(collection_id, added_at DESC);
CREATE INDEX idx_collection_seeds_seed ON collection_seeds(seed_id);
```

### 14.13 reports

```sql
CREATE TABLE reports (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  seed_id       INTEGER NOT NULL REFERENCES seeds(id) ON DELETE CASCADE,
  reporter_id   INTEGER REFERENCES users(id),       -- NULL = 匿名举报
  reporter_ip_hash VARCHAR(64),                      -- 匿名举报者的 IP hash
  reason        VARCHAR(32) NOT NULL,                -- 'screenshot_mismatch' | 'wrong_version' | 'duplicate' | 'inappropriate' | 'other'
  detail        VARCHAR(500),
  status        VARCHAR(16) NOT NULL DEFAULT 'pending',  -- 'pending' | 'reviewed' | 'dismissed'
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_reports_unique ON reports(seed_id, reporter_id)
  WHERE reporter_id IS NOT NULL;
CREATE UNIQUE INDEX idx_reports_anon_unique ON reports(seed_id, reporter_ip_hash)
  WHERE reporter_ip_hash IS NOT NULL;
```

### 14.14 notifications

```sql
CREATE TABLE notifications (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type        VARCHAR(32) NOT NULL,     -- 'seed_approved' | 'seed_rejected'
  message     VARCHAR(255) NOT NULL,
  detail      VARCHAR(500),             -- 拒绝原因等补充信息
  seed_id     INTEGER REFERENCES seeds(id) ON DELETE SET NULL,
  is_read     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);
```

---

## 15. 文件存储抽象层

### 15.1 接口

```python
class StorageBackend(ABC):
    async def upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
        """上传文件，返回公开 URL"""
        ...

    async def delete(self, file_path: str) -> None:
        """删除文件"""
        ...
```

### 15.2 实现

| 实现 | 适用场景 | 配置 |
|------|---------|------|
| `LocalStorage` | 开发 / 单机部署 | `UPLOAD_DIR=./uploads` |
| `S3Storage` | 生产 / 对象存储 | `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` |

通过环境变量 `STORAGE_BACKEND=local|s3` 切换。两种实现在 `app/services/storage.py` 中注册，应用启动时根据配置选择。

### 15.3 路径规则

```
screenshots/{YYYY-MM}/{uuid}.{ext}

例: screenshots/2026-05/a1b2c3d4.webp
```

### 15.4 清理策略

- 投稿提交后：截图 `status` 从 `pending` 变为 `active`
- 投稿表单中上传但未提交的截图：`status` 保持 `pending`
- 定时任务（每周）清理 `status = 'pending' AND created_at < NOW() - 7 DAYS` 的截图（同时调用 `StorageBackend.delete`）

---

## 16. Auth 中间件与验证链路

### 16.1 JWT 中间件

FastAPI dependency `get_current_user` 挂载在所有 `[需登录]` 端点上：

```
请求 → 从 Cookie 提取 seedvault_token
     → 验证 JWT 签名 + 过期时间
     → 查询数据库确认用户存在且 is_banned = FALSE
     → 将 user 对象注入 request.state
     → 继续处理
     → 失败：返回 401
```

JWT payload：

```json
{
  "sub": 1,
  "role": "user",
  "exp": 1716652800,
  "iat": 1715356800
}
```

### 16.2 Admin 守卫

在上述基础上再检查 `user.role == 'admin'`，失败返回 403。

### 16.3 投稿服务端校验（补充 §4.3）

POST /seeds 在写入数据库前执行以下校验：

| 校验项 | 规则 | 错误码 |
|--------|------|--------|
| 种子值格式 | 纯数字不超 64 位范围；文本种子 ≤ 64 字符 | `INVALID_SEED_VALUE` |
| 基岩版 32 位警告 | edition=bedrock & version < 1.18.20 & 种子值 > 2^32 → 返回 422 警告 | `BEDROCK_32BIT_WARNING` |
| seed=0 版本提示 | seed_value="0" & tested_version < 1.18.2 (Java) → 提示 | `SEED_ZERO_WARNING` |
| 重复检查 | seed_value + edition + tested_version 三者组合在 approved/pending 状态中已存在 | `DUPLICATE_SEED` |
| 截图数量 | 1 ≤ len(screenshot_ids) ≤ 5 | `SCREENSHOT_COUNT` |
| 标签验证 | tags 中至少含 1 个 category='gameplay' 的 tag | `TAG_REQUIRED` |
| 截图归属 | 所有 screenshot_ids 属于当前上传者且 status='pending' | `SCREENSHOT_OWNERSHIP` |
| mod_env 联动 | mod_env='modpack' 时 modpack_name 必填 | `MODPACK_NAME_REQUIRED` |
| 坐标范围 | X/Z 在合理范围内（-30000000 ~ 30000000，Minecraft 世界边界） | `COORD_OUT_OF_RANGE` |

返回 422 时代码 `VALIDATION_ERROR`。其中 BEDROCK_32BIT_WARNING 和 SEED_ZERO_WARNING 是软警告——前端可展示警告后让用户确认是否仍要提交。API 通过 `warning` 字段区分硬错误和软警告：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "种子值超出 32 位范围...",
    "severity": "warning",
    "details": { "truncated_value": "-1798537171" }
  }
}
```

`severity: "warning"` 时前端应展示确认对话框；`severity: "error"` 时阻止提交。

### 16.4 热力分 / 冷启动保护

首页和浏览页的 `sort=popular` 排序使用以下热度公式：

```
score = (like_count * 0.7 + view_count * 0.3)
      / pow(hours_since_created + 4, 1.2)
```

- 分母 `+4`：新种子冷启动保护（提交后 4 小时内不因分母几乎为 0 而暴增）
- 幂 `1.2`：Gravity 因子，比标准 Hacker News 算法（1.8）更温和，种子内容时效性弱于新闻

> **勘误（2026-05-28）**：初版设计中热度分包含"超过 2 个大版本的种子 ×0.3 降权"，其 SQL 实现存在数学错误（REAL 类型版本号减法 `1.21 - 2 = -0.79` 导致降权永不触发），且该规则本身缺乏充分的用户需求依据。已彻底移除此规则。旧版本种子的内容可见性由版本筛选器（默认展示最新两个大版本）和排序器（`newest` / `most_liked` 等）共同控制，不需在热度分中额外引入版本惩罚。

热度分公式在数据库查询层计算（SQL expression），不在 Python 层做二次排序。

---

## 17. 服务层边界

### 17.1 分层职责

```
Router (app/routers/)
  ├── 解析请求参数 / 依赖注入
  ├── 调用 Service
  └── 构造 HTTP 响应

Service (app/services/)
  ├── 业务逻辑
  ├── 事务管理
  └── 调用外部 API（Microsoft / Xbox / Minecraft）

Repository (隐含在 SQLAlchemy 模型中)
  └── 数据库查询（通过 SQLAlchemy session 直接操作，不额外抽象）
```

### 17.2 服务清单

| 服务 | 文件 | 职责 |
|------|------|------|
| `AuthService` | `services/auth.py` | Microsoft OAuth 全链路、JWT 签发/验证、用户首次登录创建 |
| `MinecraftService` | `services/minecraft.py` | Xbox Live 认证、XSTS 认证、Minecraft 服务登录、entitlements 检查、profile 获取 |
| `SeedService` | `services/seeds.py` | 种子 CRUD、去重检查、热度分计算、点赞 toggle、浏览计数 |
| `CommentService` | `services/comments.py` | 评论 CRUD、软删除 |
| `StorageService` | `services/storage.py` | 存储后端选择、文件上传/删除、清理 |
| `AdminService` | `services/admin.py` | 审核操作、版本管理、用户管理 |

### 17.3 为什么不做 Repository 抽象

项目使用 SQLite（单文件）→ PostgreSQL（可选升级路径），两者都通过 SQLAlchemy 统一接口。`SeedService` 直接接收 `AsyncSession` 参数执行查询。不需要额外抽象层——SQLAlchemy 本身就是抽象。如果未来需要在单元测试中 mock 数据层，直接 mock `AsyncSession` 比 mock 自定义 Repository 更容易。

---

*文档结束 · API 端点变更时本文档应最先更新，作为前后端唯一契约*

# Seed Vault · 数据库设计文档

> 版本：v0.1 · 日期：2026-05-27  
> 关联文档：`api-and-backend-design.md` §12（DDL）、`mc-seed-platform-plan.md` §4.4（初始模型）

---

## 目录

1. [设计哲学](#1-设计哲学)
2. [实体关系总览](#2-实体关系总览)
3. [命名规范](#3-命名规范)
4. [表详细设计](#4-表详细设计)
5. [索引策略](#5-索引策略)
6. [约束与数据完整性](#6-约束与数据完整性)
7. [查询模式与性能](#7-查询模式与性能)
8. [迁移策略：SQLite → PostgreSQL](#8-迁移策略sqlite--postgresql)
9. [扩展性设计](#9-扩展性设计)
10. [种子数据](#10-种子数据)

---

## 1. 设计哲学

### 1.1 范式选择：3NF 为基线，按需降范

所有表达到第三范式（3NF）。仅在以下情况允许有意违反：

| 场景 | 降范手段 | 理由 |
|------|---------|------|
| 种子热度排序 | `like_count`、`collection_count`、`view_count` 冗余存储在 `seeds` 表 | COUNT 查询在大表上不可接受；写入时更新计数器，读取时零 JOIN |
| 种子封面图 | `screenshots.is_cover` 布尔标记 | 避免额外 `seed_cover` 表或 `seeds.cover_id` 自引用 |
| 投稿者摘要 | `uploader_id` 仅存外键，用户名/头像通过 JOIN 查询 | 不降范——用户名可能变更，JOIN 成本可接受 |

**原则**：先问"这个冗余是为了读取性能还是写入便利"。只有前者才允许降范。

### 1.2 主键选择：自增整数

所有业务表使用 `INTEGER PRIMARY KEY AUTOINCREMENT`。未使用 UUID 作为主键，理由：

- **B-Tree 友好**：自增整数插入时追加到索引末尾，页分裂最小化
- **外键简洁**：`uploader_id INTEGER` vs `uploader_id VARCHAR(36)`，JOIN 更快、索引更小
- **URL 安全性**：种子详情页 URL 使用 `{id}-{slug}` 格式，ID 暴露无害（无枚举风险的数据集）

UUID 仅用于 `minecraft_uuid` 和 `microsoft_id`（外部系统标识符，必须保留原值）。

### 1.3 软删除 vs 硬删除

| 实体 | 策略 | 理由 |
|------|------|------|
| 种子 | 硬删除（`status = 'rejected'` 除外） | 种子价值和显示逻辑复杂，软删会增加所有查询的 WHERE 条件 |
| 评论 | 软删除（`deleted_at`） | 保留对话线索——"该评论已被作者删除"比消失的评论更友好 |
| 用户 | 硬删除（`is_banned` 代替软删） | 被封禁 ≠ 被删除。投稿/评论通过 `ON DELETE SET NULL` 或保留外键处理 |
| 截图 | 硬删除 + 文件系统清理 | 无业务价值保留 |

### 1.4 枚举值策略：字符串 + CHECK 约束

不使用枚举表（lookup table）存储小型固定值集。`edition`、`status`、`world_type` 等字段直接存字符串，配合 CHECK 约束：

```sql
edition VARCHAR(16) NOT NULL CHECK (edition IN ('java', 'bedrock'))
```

理由：
- 10 个以内值、变化频率"一年一次"的枚举不值得建表
- 字符串自文档化——`WHERE status = 'approved'` 比 `WHERE status_id = 2` 可读
- 应用层用 Pydantic `Literal` 类型确保类型安全

标签（tags）是例外——标签有 label、icon、category 等附加属性，且可能由管理员新增，因此使用独立表。

---

## 2. 实体关系总览

```
                    ┌──────────┐
                    │  users   │
                    └────┬─────┘
                         │
     ┌───────────────────┼───────────────────┐
     │                   │                   │
uploader_id         author_id           user_id
     │                   │                   │
     ▼                   ▼                   ▼
┌──────────┐       ┌──────────┐       ┌──────────┐
│  seeds   │       │ comments │       │  likes   │
└────┬─────┘       └──────────┘       └──────────┘
     │
┌────┴─────┬──────────┬────────────┐
│          │          │            │
▼          ▼          ▼            ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐
│screen- │ │  key_  │ │seed_tags │ │seed_views │
│ shots  │ │ coords │ │          │ │           │
└────────┘ └────────┘ └────┬─────┘ └───────────┘
                           │
                           ▼
                      ┌──────────┐            ┌─────────────┐
                      │   tags   │            │ collections │
                      └──────────┘            └──────┬──────┘
                                                    │
                                               user_id
                                                    │
                                          ┌─────────┴─────────┐
                                          │                   │
                                          ▼                   ▼
                                   ┌──────────────┐   ┌──────────────┐
                                   │  collection  │   │   seeds      │
                                   │   _seeds     │───│  (via seed_id)│
                                   └──────────────┘   └──────────────┘

独立实体（无外键关联）:
  ┌──────────┐
  │ versions │  由管理员维护，不直接关联种子
  └──────────┘
```

**关系基数**：

| 父 → 子 | 基数 | 说明 |
|---------|------|------|
| users → seeds | 1:N | 一个用户可以投稿多个种子 |
| users → comments | 1:N | 一个用户可以发表多条评论 |
| users → likes | 1:N | 一个用户可以点赞多个种子 |
| users → collections | 1:N | 一个用户可以创建多个收藏夹 |
| seeds → screenshots | 1:N | 一个种子有 1-5 张截图 |
| seeds → key_coords | 1:N | 一个种子有 0-N 个关键坐标 |
| seeds → comments | 1:N | 一个种子有多条评论 |
| seeds ↔ tags | M:N | 通过 seed_tags 关联 |
| seeds ↔ collections | M:N | 通过 collection_seeds 关联 |
| seeds → seed_views | 1:N | 浏览记录 |

---

## 3. 命名规范

### 3.1 表名

- 小写 + 下划线（snake_case）
- 复数形式（`users`, `seeds`, `screenshots`）——SQL 是集合语言，表是记录的集合
- 关联表：两个实体名用下划线连接，按字母序排列（`seed_tags`，不是 `tag_seeds`）
- 不使用前缀（`tbl_`, `t_`）——表名本身即表明它是表

### 3.2 列名

- 小写 + 下划线
- 主键统一为 `id`
- 外键：`{referenced_table_singular}_id`（`uploader_id`, `seed_id`, `author_id`）
- 布尔列：`is_` 前缀（`is_cover`, `is_banned`, `is_latest`）
- 时间列：`_at` 后缀（`created_at`, `updated_at`, `deleted_at`, `approved_at`）
- 避免缩写：`description` 非 `desc`（后者是 SQL 关键字），`uploader_id` 非 `uid`
- 避免保留字：不使用 `order`、`group`、`status`（`status` 虽不是所有数据库的保留字，但安全可用）

### 3.3 索引名

遵循 `idx_{table}_{column}` 模式：

```
idx_users_microsoft_id
idx_seeds_edition_version
idx_comments_seed
```

唯一约束使用 `uq_{table}_{column}` 模式（PostgreSQL 显式命名；SQLite 在 CREATE TABLE 内联声明）。

---

## 4. 表详细设计

### 4.1 users

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ microsoft_id         │ VARCHAR(64)  │ UNIQUE NOT NULL                │
│ email                │ VARCHAR(255) │                                │
│ display_name         │ VARCHAR(128) │ NOT NULL                       │
│ minecraft_uuid       │ VARCHAR(36)  │ UNIQUE                         │
│ minecraft_username   │ VARCHAR(64)  │                                │
│ owns_java_edition    │ BOOLEAN      │ NOT NULL DEFAULT FALSE          │
│ skin_model           │ VARCHAR(8)   │ CHECK (skin_model IN           │
│                      │              │   ('steve', 'alex'))           │
│ role                 │ VARCHAR(16)  │ NOT NULL DEFAULT 'user'        │
│                      │              │ CHECK (role IN                 │
│                      │              │   ('user', 'admin'))           │
│ is_banned            │ BOOLEAN      │ NOT NULL DEFAULT FALSE          │
│ microsoft_refresh_   │ TEXT         │                                │
│   token              │              │                                │
│ created_at           │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
│ last_login_at        │ DATETIME     │                                │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `microsoft_id` 是自然主键（来自 Microsoft Graph API 的 `id` 字段），但其格式为 GUID 字符串，不适合做关联主键。因此另设 `id` 作为代理主键。
- `minecraft_uuid` 加 UNIQUE 约束——一个 Minecraft 账号不能绑定多个本站用户。反之不成立：一个 Microsoft 账号可以换绑不同 Minecraft 账号（存在 UNIQUE 但不强制关联）。
- `microsoft_refresh_token` 加密存储（AES-256-GCM，密钥来自环境变量 `TOKEN_ENCRYPTION_KEY`）。不存明文。
- 用户删除：不在 MVP 范围。被禁用户 (`is_banned = TRUE`) 不能签发新 JWT，现有 JWT 在下次请求时通过 `is_banned` 检查被拒。
- **勘误（2026-05-28）**：`skin_model` 字段（`'steve' | 'alex'`）当前未在任何 API 响应中暴露给前端。mc-heads.net 已通过 UUID 自动返回正确的皮肤头像（含模型），前端无需额外处理。此字段保留用于未来可能的服务端皮肤渲染或统计用途。

### 4.2 seeds

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ title                │ VARCHAR(50)  │ NOT NULL                       │
│ description          │ VARCHAR(500) │ NOT NULL                       │
│ seed_value           │ VARCHAR(64)  │ NOT NULL                       │
│ seed_numeric         │ BIGINT       │                                │
│ edition              │ VARCHAR(16)  │ NOT NULL                       │
│                      │              │ CHECK (edition IN              │
│                      │              │   ('java', 'bedrock'))         │
│ tested_version       │ VARCHAR(16)  │ NOT NULL                       │
│ compatible_range     │ VARCHAR(32)  │                                │
│ world_type           │ VARCHAR(16)  │ NOT NULL DEFAULT 'normal'      │
│                      │              │ CHECK (world_type IN           │
│                      │              │   ('normal',                   │
│                      │              │    'large_biomes',             │
│                      │              │    'superflat'))               │
│ mod_env              │ VARCHAR(16)  │ NOT NULL DEFAULT 'vanilla'     │
│                      │              │ CHECK (mod_env IN              │
│                      │              │   ('vanilla', 'modpack',       │
│                      │              │    'neoforge'))                │
│ modpack_name         │ VARCHAR(128) │                                │
│ modpack_version      │ VARCHAR(32)  │                                │
│ spawn_x              │ INTEGER      │ NOT NULL                       │
│ spawn_z              │ INTEGER      │ NOT NULL                       │
│ status               │ VARCHAR(16)  │ NOT NULL DEFAULT 'pending'     │
│                      │              │ CHECK (status IN               │
│                      │              │   ('pending', 'approved',      │
│                      │              │    'rejected'))                │
│ rejection_reason     │ VARCHAR(500) │                                │
│ uploader_id          │ INTEGER      │ NOT NULL REFERENCES users(id)  │
│ view_count           │ INTEGER      │ NOT NULL DEFAULT 0             │
│ like_count           │ INTEGER      │ NOT NULL DEFAULT 0             │
│ collection_count     │ INTEGER      │ NOT NULL DEFAULT 0             │
│ created_at           │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
│ updated_at           │ DATETIME     │                                │
│ approved_at          │ DATETIME     │                                │
│ approved_by          │ INTEGER      │ REFERENCES users(id)           │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `seed_value` 使用 VARCHAR(64)，不设种子空间上限（文本种子可超过 64 字符，但 64 字符已覆盖所有合法数字种子和最长的文本种子）。
- `seed_numeric` 为解析后的 64 位整数（纯数字种子），文本种子为 NULL。用于数值范围查询和数值比较排序，弥补 `seed_value` 作为字符串无法高效做数值比较的不足。应用层解析，不在数据库层触发。
- **勘误（2026-05-28）**：`BIGINT` 在 SQLite 中无独立类型——SQLite 的 `INTEGER` 即为 64 位有符号整数，`BIGINT` 被当作 INTEGER affinity 处理，实际存储无差异。迁移至 PostgreSQL 时需改为 `BIGINT` 原生类型。SQLAlchemy 的 `BigInteger` 类型在两个方言上自动适配。
- `view_count`、`like_count` 和 `collection_count` 是计数器列（降范），由应用层维护而非数据库触发器——触发器在 SQLite 中调试困难，在 PostgreSQL 中迁移时有额外步骤。
- `collection_count` 在 `POST /collections/{id}/seeds/{seed_id}` 时 +1，`DELETE` 时 -1（最小为 0）。
- `rejection_reason` 仅当 `status = 'rejected'` 时有值。投稿者在"我的投稿"中可见。
- `approved_by` 记录审核人，用于审计。
- 去重约束使用部分唯一索引（PostgreSQL）或应用层校验（SQLite），见 §6.2。

### 4.3 screenshots

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ seed_id              │ INTEGER      │ REFERENCES seeds(id)           │
│                      │              │   ON DELETE CASCADE            │
│ uploader_id          │ INTEGER      │ NOT NULL REFERENCES users(id)  │
│ file_path            │ VARCHAR(512) │ NOT NULL                       │
│ is_cover             │ BOOLEAN      │ NOT NULL DEFAULT FALSE          │
│ sort_order           │ INTEGER      │ NOT NULL DEFAULT 0             │
│ status               │ VARCHAR(16)  │ NOT NULL DEFAULT 'pending'     │
│                      │              │ CHECK (status IN               │
│                      │              │   ('pending', 'active',        │
│                      │              │    'orphaned'))                │
│ created_at           │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `seed_id` 在初始上传时为空——截图先上传，后通过 `POST /seeds` 的 `screenshot_ids` 关联。`seed_id` 的 NULL 状态对应 `status = 'pending'`。
- `file_path` 存储存储后端的路径/S3 key，不含域名前缀（前缀由 StorageBackend 动态拼接，方便切换存储位置）。
- `ON DELETE CASCADE`：种子被删除时，关联截图记录自动删除。StorageBackend 需同步删除文件（在 Service 层处理，非数据库层）。
- `sort_order` 由投稿表单中的拖拽排序决定。首张（`sort_order = 0`）自动设为 `is_cover = TRUE`。

### 4.4 key_coords

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ seed_id              │ INTEGER      │ NOT NULL REFERENCES seeds(id)  │
│                      │              │   ON DELETE CASCADE            │
│ label                │ VARCHAR(30)  │ NOT NULL                       │
│ x                    │ INTEGER      │ NOT NULL                       │
│ y                    │ INTEGER      │                                │
│ z                    │ INTEGER      │ NOT NULL                       │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `y` 可空——高度坐标在基岩版和 1.18 前的 Java 版有不同基准面，且许多投稿者不填高度。
- 不做坐标范围约束（CHECK x BETWEEN ...）。Minecraft 世界边界在不同版本间变化（30,000,000 vs 3,000,000），数据库层不应硬编码游戏规则。校验在应用层 Pydantic schema 中完成。
- 每条坐标是独立行而非 JSON 数组列——允许按坐标标签搜索、允许独立更新，且 SQLite 对 JSON 函数支持有限。
- **勘误（2026-05-28）**：此表无 `sort_order` 字段，坐标展示顺序依赖 `id` 插入顺序。若未来需要投稿者自定义坐标排列，需 ALTER TABLE 新增该字段。

### 4.5 tags

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ key                  │ VARCHAR(32)  │ UNIQUE NOT NULL               │
│ label                │ VARCHAR(32)  │ NOT NULL                       │
│ icon                 │ VARCHAR(8)   │                                │
│ category             │ VARCHAR(16)  │ NOT NULL                       │
│                      │              │ CHECK (category IN             │
│                      │              │   ('gameplay', 'feature',      │
│                      │              │    'special'))                 │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `key` 是机器标识符（API 传输用），`label` 是人类可读文本（UI 展示用）。支持未来国际化时不改 key 只替换 label。
- `category` 控制标签在筛选器中的分组（gameplay / feature / special）。
- `special` 类别标签（`verified`、`hot`、`new`）由系统计算而非用户选择，不出现在投稿表单中。
- 标签由管理员通过 seed data 管理，不提供用户自定义标签功能（避免标签爆炸和同义标签碎片化）。

### 4.6 seed_tags

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ seed_id              │ INTEGER      │ NOT NULL REFERENCES seeds(id)  │
│                      │              │   ON DELETE CASCADE            │
│ tag_id               │ INTEGER      │ NOT NULL REFERENCES tags(id)   │
│                      │              │   ON DELETE CASCADE            │
│                      │              │ PRIMARY KEY (seed_id, tag_id)  │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

- 复合主键天然防止重复关联
- 双向 CASCADE：种子或标签被删除时关联自动清除

### 4.7 likes

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ user_id              │ INTEGER      │ NOT NULL REFERENCES users(id)  │
│                      │              │   ON DELETE CASCADE            │
│ seed_id              │ INTEGER      │ NOT NULL REFERENCES seeds(id)  │
│                      │              │   ON DELETE CASCADE            │
│ created_at           │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
│                      │              │ PRIMARY KEY (user_id, seed_id) │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- 点赞和收藏是两个独立语义。此表仅存储点赞关系。
- `GET /users/me/bookmarks` 读取的是此表——"我赞过的种子"等价于"我想再次找到的种子"，语义清晰不混淆。
- 用户创建的自定义收藏夹见 §4.11（`collections`）和 §4.12（`collection_seeds`）。
- 用户删除 → 其所有点赞记录清除。
- 种子删除 → 点赞记录清除，`seeds.like_count` 随 CASCADE 失效但数据库已无此种子，不影响查询。
- `created_at` 记录点赞时间，支持按时间排序。

### 4.8 comments

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ seed_id              │ INTEGER      │ NOT NULL REFERENCES seeds(id)  │
│                      │              │   ON DELETE CASCADE            │
│ author_id            │ INTEGER      │ NOT NULL REFERENCES users(id)  │
│ content              │ VARCHAR(1000)│ NOT NULL                       │
│ deleted_at           │ DATETIME     │                                │
│ created_at           │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `deleted_at` 实现软删除。查询评论时：`WHERE deleted_at IS NULL`。已删除评论在 UI 中显示占位文字。
- 不做嵌套评论（无限层级回复）。线性时间序（最早 → 最新）降低认知负担和服务端复杂度。
- `author_id` 而非 `user_id`——语义更准确（评论的作者身份）。

### 4.9 versions

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ edition              │ VARCHAR(16)  │ NOT NULL                       │
│ version              │ VARCHAR(16)  │ NOT NULL                       │
│ is_latest            │ BOOLEAN      │ NOT NULL DEFAULT FALSE          │
│ sort_order           │ INTEGER      │ NOT NULL DEFAULT 0             │
│                      │              │ UNIQUE (edition, version)      │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- 不直接关联到 `seeds`（seeds 的 `tested_version` 存的是字符串，不是外键）。版本号列表是独立的管理实体，种子的版本号仅是数据字段。两者解耦。
- `sort_order` 控制筛选器下拉中的排列顺序，数字越大越靠前。
- 同一 edition 下，`is_latest = TRUE` 的行 ≤ 1（应用层保证）。

### 4.10 seed_views

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ seed_id              │ INTEGER      │ NOT NULL REFERENCES seeds(id)  │
│                      │              │   ON DELETE CASCADE            │
│ session_key          │ VARCHAR(64)  │ NOT NULL                       │
│ viewed_at            │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `session_key = HMAC(seed_id || user_ip || user_agent, SESSION_SECRET)`。存储的是 hash，不是 IP 明文。
- 去重逻辑：同一 `(seed_id, session_key)` 在 30 分钟内不重复计数。每次请求时先查询是否存在该时间段内的记录，若否则插入并 `UPDATE seeds SET view_count = view_count + 1`。
- 定时任务（每 30 分钟）删除 `viewed_at < NOW() - 30 MINUTES` 的记录，控制表大小。

### 4.11 collections

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ user_id              │ INTEGER      │ NOT NULL REFERENCES users(id)  │
│                      │              │   ON DELETE CASCADE            │
│ name                 │ VARCHAR(50)  │ NOT NULL                       │
│ description          │ VARCHAR(200) │                                │
│ cover_strategy       │ VARCHAR(16)  │ NOT NULL DEFAULT 'last'        │
│                      │              │ CHECK (cover_strategy IN       │
│                      │              │   ('first', 'last', 'manual')) │
│ cover_seed_id        │ INTEGER      │ REFERENCES seeds(id)           │
│                      │              │   ON DELETE SET NULL           │
│ is_public            │ BOOLEAN      │ NOT NULL DEFAULT FALSE          │
│ sort_order           │ INTEGER      │ NOT NULL DEFAULT 0             │
│ created_at           │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
│ updated_at           │ DATETIME     │                                │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `cover_strategy` 决定收藏夹封面图的来源：
  - `'first'`：使用收藏夹中第一个添加的种子封面
  - `'last'`（默认）：使用最后一个添加的种子封面
  - `'manual'`：由用户在已添加的种子中手动选择，此时 `cover_seed_id` 有值
- `cover_seed_id` 仅当 `cover_strategy = 'manual'` 时有值（CHECK 约束在应用层强制）
- `is_public`：用户可将收藏夹设为公开，生成分享链接供他人浏览
- `sort_order`：用于前端拖拽排序收藏夹

### 4.12 collection_seeds

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ collection_id        │ INTEGER      │ NOT NULL REFERENCES            │
│                      │              │   collections(id)              │
│                      │              │   ON DELETE CASCADE            │
│ seed_id              │ INTEGER      │ NOT NULL REFERENCES seeds(id)  │
│                      │              │   ON DELETE CASCADE            │
│ added_at             │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
│                      │              │ PRIMARY KEY (collection_id,    │
│                      │              │   seed_id)                     │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- 标准 M:N 关联表。复合主键天然防止重复添加。
- `added_at` 记录加入时间。`cover_strategy = 'first'` 时取 `MIN(added_at)` 的种子；`cover_strategy = 'last'` 时取 `MAX(added_at)` 的种子（默认）。
- 双向 CASCADE：收藏夹或种子被删除 → 关联自动清除。

### 4.13 likes 与 collections 的关系

两条路径服务于两种用户意图：

| 操作 | 表 | 语义 |
|------|---|------|
| "这个种子不错" | `likes` | 轻量认可，计入 `seeds.like_count` 热度分 |
| "我要分类保存" | `collection_seeds` | 归档意图，组织到自定义收藏夹 |

用户可以只点赞不归档（`likes` 有记录，`collection_seeds` 无记录），也可以只归档不点赞（反之），也可以同时做。两者正交——不互相依赖，不互相替代。

`GET /users/me/bookmarks` 保持指向 `likes` 表："我赞过的种子"即"我想再次找到的种子"。这是上一轮讨论中确立的语义——点赞按钮的含义是"这个种子值得再次找到吗？"，重命名为收藏列表名正言顺。

### 4.14 reports

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ seed_id              │ INTEGER      │ NOT NULL REFERENCES seeds(id)  │
│                      │              │   ON DELETE CASCADE            │
│ reporter_id          │ INTEGER      │ REFERENCES users(id)           │
│                      │              │   ON DELETE SET NULL           │
│ reporter_ip_hash     │ VARCHAR(64)  │                                │
│ reason               │ VARCHAR(32)  │ NOT NULL                       │
│                      │              │ CHECK (reason IN               │
│                      │              │   ('screenshot_mismatch',      │
│                      │              │    'wrong_version',            │
│                      │              │    'duplicate',                │
│                      │              │    'inappropriate',            │
│                      │              │    'other'))                   │
│ detail               │ VARCHAR(500) │                                │
│ status               │ VARCHAR(16)  │ NOT NULL DEFAULT 'pending'     │
│                      │              │ CHECK (status IN               │
│                      │              │   ('pending', 'reviewed',      │
│                      │              │    'dismissed'))               │
│ created_at           │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- `reporter_id` 可空——匿名用户也可以举报（以 `reporter_ip_hash` 标识）
- 已登录用户同种子多次举报自动合并：`UNIQUE (seed_id, reporter_id)`（部分唯一索引，reporter_id IS NOT NULL 时生效）
- 匿名举报合并：`UNIQUE (seed_id, reporter_ip_hash)`（匿名时生效）
- `status` 供管理员在审核后台处理

### 4.15 notifications

```
┌─────────────────────┬──────────────┬────────────────────────────────┐
│ 列                   │ 类型          │ 约束                            │
├─────────────────────┼──────────────┼────────────────────────────────┤
│ id                   │ INTEGER      │ PRIMARY KEY AUTOINCREMENT      │
│ user_id              │ INTEGER      │ NOT NULL REFERENCES users(id)  │
│                      │              │   ON DELETE CASCADE            │
│ type                 │ VARCHAR(32)  │ NOT NULL                       │
│                      │              │ CHECK (type IN                 │
│                      │              │   ('seed_approved',            │
│                      │              │    'seed_rejected'))           │
│ message              │ VARCHAR(255) │ NOT NULL                       │
│ detail               │ VARCHAR(500) │                                │
│ seed_id              │ INTEGER      │ REFERENCES seeds(id)           │
│                      │              │   ON DELETE SET NULL           │
│ is_read              │ BOOLEAN      │ NOT NULL DEFAULT FALSE          │
│ created_at           │ DATETIME     │ NOT NULL DEFAULT               │
│                      │              │   CURRENT_TIMESTAMP            │
└─────────────────────┴──────────────┴────────────────────────────────┘
```

**设计要点**：

- 通知为**被动拉取**模式（MVP 不做推送）。前端在登录后（`GET /auth/me` 响应含 `unread_count`）或点击通知图标时拉取
- `seed_id` 在种子被删除时 SET NULL（通知保留，"该种子已被删除"代替链接）
- `detail` 用于拒绝原因等补充信息
- 通知不编辑不软删——标记已读为唯一操作

---

## 5. 索引策略

### 5.1 索引矩阵

| 索引名 | 表 | 列 | 类型 | 驱动查询 |
|--------|---|-----|------|---------|
| `idx_users_microsoft_id` | users | `microsoft_id` | UNIQUE | OAuth 登录查找 |
| `idx_users_minecraft_uuid` | users | `minecraft_uuid` | UNIQUE | MC 验证查重 |
| `idx_seeds_unique` | seeds | `(seed_value, edition, tested_version)` | UNIQUE (partial) | 投稿去重 |
| `idx_seeds_status` | seeds | `status` | B-Tree | 管理员待审列表 |
| `idx_seeds_edition_version` | seeds | `(edition, tested_version)` | B-Tree (composite) | 首页 + 浏览筛选 |
| `idx_seeds_uploader` | seeds | `uploader_id` | B-Tree | "我的投稿" |
| `idx_seeds_created` | seeds | `created_at DESC` | B-Tree | 最新排序 |
| `idx_seeds_likes` | seeds | `like_count DESC` | B-Tree | 最多点赞排序 |
| `idx_seeds_collections` | seeds | `collection_count DESC` | B-Tree | 最多收藏排序 |
| `idx_screenshots_seed` | screenshots | `seed_id` | B-Tree | 种子详情 JOIN |
| `idx_screenshots_uploader` | screenshots | `uploader_id` | B-Tree | 临时图片清理 |
| `idx_key_coords_seed` | key_coords | `seed_id` | B-Tree | 种子详情 JOIN |
| `idx_comments_seed` | comments | `(seed_id, created_at)` | B-Tree (composite) | 评论区查询 |
| `idx_seed_views_lookup` | seed_views | `(seed_id, session_key, viewed_at)` | B-Tree (composite) | 浏览去重 |
| `idx_collections_user` | collections | `(user_id, sort_order)` | B-Tree (composite) | 用户收藏夹列表 |
| `idx_collection_seeds_coll` | collection_seeds | `(collection_id, added_at DESC)` | B-Tree (composite) | 收藏夹内容 + 封面计算 |
| `idx_collection_seeds_seed` | collection_seeds | `seed_id` | B-Tree | 查看某种子被哪些收藏夹收录 |
| `idx_reports_status` | reports | `status` | B-Tree | 管理员举报列表 |
| `idx_notifications_user` | notifications | `(user_id, is_read, created_at DESC)` | B-Tree (composite) | 用户通知列表 |

### 5.2 复合索引设计原则

唯一使用复合索引的场景是"等值 + 排序"查询：

```sql
-- 驱动: seed_id = ? ORDER BY created_at ASC
CREATE INDEX idx_comments_seed ON comments(seed_id, created_at);
```

索引列顺序：等值条件在前（`seed_id`），排序/范围条件在后（`created_at`）。

### 5.3 为什么某些列不加索引

| 列 | 理由 |
|----|------|
| `seeds.mod_env` | 基数仅 3（vanilla / modpack / neoforge），索引无意义——全表扫描比索引查找更快 |
| `seeds.world_type` | 基数仅 3，同上 |
| `seeds.compatible_range` | 不直接查询此列——用于展示而非筛选（VARCHAR(32) 存储自由格式文本如 `"1.21.4 ~ 1.21.5"`，无程序可读性）。若未来需要基于兼容范围筛选，需拆分为 `compatible_version_min` + `compatible_version_max` 两个结构化字段。 |
| `comments.author_id` | 无"查看某用户所有评论"功能——查询总是从种子侧出发 |

### 5.4 部分唯一索引

> **勘误（2026-05-28）**：初版声称"SQLite 不支持部分索引"，此陈述错误。SQLite 自 **3.8.0（2013 年）**起完整支持部分索引（Partial Indexes），语法为 `CREATE UNIQUE INDEX ... WHERE condition`，与 PostgreSQL 兼容。

投稿去重规则："同一 `(seed_value, edition, tested_version)` 在非拒绝状态下只能有一条"。

此约束可在 SQLite 和 PostgreSQL 上直接使用数据库层部分唯一索引：

```sql
CREATE UNIQUE INDEX idx_seeds_unique
  ON seeds(seed_value, edition, tested_version)
  WHERE status != 'rejected';
```

应用层校验保留作为防御性第二层（在调用数据库前先做 SELECT 检查，提供更友好的错误信息和 `existing_id`）：

```python
# app/services/seeds.py
existing = await session.execute(
    select(Seed).where(
        Seed.seed_value == value,
        Seed.edition == edition,
        Seed.tested_version == version,
        Seed.status != 'rejected'
    )
)
if existing.scalar():
    raise DuplicateSeedError(existing_id=...)
```

数据库层唯一索引提供最终保证（即使并发竞态条件下也能阻止重复插入），应用层校验提供更友好的用户反馈。

---

## 6. 约束与数据完整性

### 6.1 CHECK 约束清单

| 表 | 列 | 约束 |
|----|-----|------|
| users | `skin_model` | `IN ('steve', 'alex')` |
| users | `role` | `IN ('user', 'admin')` |
| seeds | `edition` | `IN ('java', 'bedrock')` |
| seeds | `world_type` | `IN ('normal', 'large_biomes', 'superflat')` |
| seeds | `mod_env` | `IN ('vanilla', 'modpack', 'neoforge')` |
| seeds | `status` | `IN ('pending', 'approved', 'rejected')` |
| screenshots | `status` | `IN ('pending', 'active', 'orphaned')` |
| tags | `category` | `IN ('gameplay', 'feature', 'special')` |

### 6.2 应用层约束（Pydantic + Service）

| 规则 | 实现层 | 说明 |
|------|--------|------|
| 种子投稿时 tags 至少 1 个 gameplay 类 | Service | 跨表校验 |
| 截图 1-5 张 | Pydantic `min_length=1, max_length=5` | 请求体验证 |
| mod_env='modpack' 时 modpack_name 必填 | Pydantic `model_validator` | 条件必填 |
| 种子值格式校验 | Pydantic `field_validator` | 纯数字/文本种子/范围检查 |
| 同一用户对同一种子只能点赞一次 | Service + DB PK | 双重保证 |
| 坐标范围 | Pydantic `field_validator` | 游戏规则不应进数据库 |

### 6.3 外键与 CASCADE 策略

| 外键 | CASCADE 行为 | 理由 |
|------|------------|------|
| `screenshots.seed_id` | `ON DELETE CASCADE` | 种子删除 → 截图记录清除，文件由 StorageBackend 清理 |
| `key_coords.seed_id` | `ON DELETE CASCADE` | 种子删除 → 坐标失去意义 |
| `seed_tags.seed_id` / `seed_tags.tag_id` | `ON DELETE CASCADE` | 任一端删除 → 关联无意义 |
| `likes.user_id` / `likes.seed_id` | `ON DELETE CASCADE` | 任一端删除 → 点赞无意义 |
| `comments.seed_id` | `ON DELETE CASCADE` | 种子删除 → 评论无意义 |
| `seeds.uploader_id` | 无 CASCADE（RESTRICT） | 用户被删 ≠ 种子应消失。`uploader_id` 保留但上传者名显示为"[已注销]" |
| `comments.author_id` | 无 CASCADE（SET NULL 备选） | 同上，评论保留但作者名显示为"[已注销]" |

---

## 7. 查询模式与性能

### 7.1 最频繁查询

| 查询 | 频率 | 涉及表 | 策略 |
|------|------|--------|------|
| 首页热门种子 | 极高 | seeds + screenshots + tags + users | 计数器列预计算热度分，单次 SELECT + 2 JOIN |
| 版本筛选 + 标签筛选 | 高 | seeds + seed_tags + tags | 复合索引 `(edition, tested_version)`，标签通过 EXISTS 子查询 |
| 种子详情 | 高 | seeds + screenshots + key_coords + seed_tags + users | 主键查询 + 4 个 JOIN + `view_count` 增量更新 |
| 投稿去重检查 | 中 | seeds | 复合条件查询，应用层校验 |
| 点赞 toggle | 中 | likes + seeds | UPSERT 模式：INSERT OR DELETE + 更新计数器 |
| 管理员待审列表 | 低 | seeds + users | `WHERE status = 'pending'` 索引扫描 |

### 7.2 热度分计算（SQL 表达式）

```sql
SELECT
  *,
  (like_count * 0.7 + view_count * 0.3)
    / POWER((julianday('now') - julianday(created_at)) * 24 + 4, 1.2)
    AS hot_score
FROM seeds
WHERE status = 'approved'
ORDER BY hot_score DESC;
```

- `julianday` 为 SQLite 函数。PostgreSQL 中替换为 `EXTRACT(EPOCH FROM ...)`。
- 热度分在每次 `sort=popular` 请求时实时计算——不被存储。计数器（`like_count`, `view_count`）是冗余存储，热度分是它们的衍生计算。

### 7.3 标签筛选查询模式

```sql
-- 多标签 AND 逻辑 (tags=survival,village)
SELECT s.* FROM seeds s
WHERE s.status = 'approved'
  AND EXISTS (SELECT 1 FROM seed_tags st JOIN tags t ON st.tag_id = t.id
              WHERE st.seed_id = s.id AND t.key = 'survival')
  AND EXISTS (SELECT 1 FROM seed_tags st JOIN tags t ON st.tag_id = t.id
              WHERE st.seed_id = s.id AND t.key = 'village')
ORDER BY s.like_count DESC;
```

前端的多标签筛选是 AND 语义（"同时标记为生存和村庄"），不是 OR。

#### 7.3.1 大版本模糊筛选

> **勘误（2026-05-28）**：初版设计中 `GET /seeds` 的 `version` 参数仅支持精确匹配（如 `1.21.4`），无法按大版本（如 `1.21`）模糊筛选全部小版本。这与 mod/资源包社区"筛选主版本号，展示全部补丁版本内容"的用户习惯不符。新增此查询模式。

```sql
-- 精确版本 (version=1.21.4)
SELECT s.* FROM seeds s
WHERE s.status = 'approved'
  AND s.tested_version = '1.21.4';

-- 大版本模糊 (version=1.21) — 匹配 1.21.0, 1.21.1, 1.21.4, 1.21.5 等全部小版本
SELECT s.* FROM seeds s
WHERE s.status = 'approved'
  AND s.tested_version LIKE '1.21.%';   -- SQLite
-- 或 s.tested_version ~ '^1\.21\.'     -- PostgreSQL regex
```

实现策略：
- 后端检测 `version` 参数的格式：两段式（`X.Y`）→ 模糊匹配 `X.Y.%`；三段式（`X.Y.Z`）→ 精确匹配
- `versions` 表不受影响——它存储完整三段式版本号，模糊匹配仅作用于 `seeds.tested_version` 字段
- 前端版本号筛选器默认展示大版本号（如 "1.21"），展开后显示精确小版本。选择 "1.21" 等价于 `?version=1.21`（模糊），选择 "1.21.4" 等价于 `?version=1.21.4`（精确）

### 7.4 连接池与事务

- SQLite 默认单写者模式。MVP 阶段并发量低（< 100 并发用户），WAL 模式 + 单连接已足够。
- 投稿和审核操作包裹在事务中（`BEGIN ... COMMIT`），确保种子 + 截图关联 + 标签关联 + 坐标的原子性。
- 浏览计数的 `view_count + 1` 更新不强制在事务中（允许最终一致性，丢失少量浏览计数不影响业务）。

---

## 8. 迁移策略：SQLite → PostgreSQL

### 8.1 为什么从 SQLite 起步

- **零配置**：`pip install` 之后直接运行，没有数据库服务需要管理
- **单文件**：数据 + 结构在 `data.db` 一个文件中，备份即 `cp`
- **开源友好**：GitHub clone 后可直接启动开发环境
- **足够撑到 10 万种子**：SQLite 在 WAL 模式下的读写性能支撑 100 并发无压力

### 8.2 切换信号

当以下任一条件满足时考虑迁移至 PostgreSQL：

- 并发写入请求 > 50 QPS（SQLite 的写锁开始成为瓶颈）
- 需要只读副本（read replica）做报表或搜索
- 需要全文搜索（PostgreSQL `tsvector` / `pg_trgm`）
- 部署变为多实例（多个 backend 进程共享同一数据库）

### 8.3 迁移清单

| 差异项 | SQLite | PostgreSQL | 迁移操作 |
|--------|--------|------------|---------|
| 主键自增 | `AUTOINCREMENT` | `SERIAL` / `GENERATED ALWAYS AS IDENTITY` | 替换 DDL |
| 布尔类型 | `BOOLEAN` (实际是 INTEGER) | `BOOLEAN` (原生) | 无需改动，SQLAlchemy 自动适配 |
| 日期函数 | `julianday()` | `EXTRACT(EPOCH FROM ...)` | 热度分 SQL 表达式替换 |
| 部分索引 | 支持（≥3.8.0, 2013） | `CREATE UNIQUE INDEX ... WHERE` | 无需迁移，语法兼容 |
| WAL 模式 | `PRAGMA journal_mode=WAL` | 内置 | SQLite 特化配置 |
| 连接字符串 | `sqlite:///data.db` | `postgresql://user:pass@host/db` | 环境变量切换 |

SQLAlchemy + Alembic 处理 90% 的兼容性差异。热度分 SQL（`julianday`）是唯一需要手动适配的地方——建议将其封装为一个方法 `hot_score_expr()`，根据 `dialect.name` 返回不同的 SQL 表达式。

---

## 9. 扩展性设计

### 9.1 新增版本端（Edition）

当前 `edition IN ('java', 'bedrock')`。如果未来需要收录中国版（`'china_java'`, `'china_bedrock'`）或 Legacy Console 版：

- 修改 CHECK 约束（或直接去掉 CHECK，改为应用层验证）
- `versions` 表的新值不受影响（没有外键约束）
- 筛选器 UI 需要更新，但数据库无需迁移

### 9.2 多语言标签

当前 `tags.label` 是单语言（简体中文）。如果要支持多语言：

- 不改动 `tags` 表结构
- 前端通过 i18n 文件根据 `tags.key` 做本地化显示
- `tags.label` 作为 i18n 的 fallback（当翻译缺失时使用数据库值）

```javascript
// 前端
const label = i18n.t(`tag.${tag.key}`) || tag.label;
```

### 9.3 Mod 加载器独立表

当前 `seeds.mod_env` 仅区分 vanilla/modpack。如果未来需要细化 mod 加载器信息（Forge / Fabric / NeoForge / Quilt + mod 列表）：

```sql
-- 未来可选扩展
CREATE TABLE mod_loaders (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  name    VARCHAR(32) UNIQUE NOT NULL       -- 'forge', 'fabric', 'neoforge', 'quilt'
);

CREATE TABLE seed_mods (
  seed_id       INTEGER NOT NULL REFERENCES seeds(id) ON DELETE CASCADE,
  mod_loader_id INTEGER NOT NULL REFERENCES mod_loaders(id),
  mod_name      VARCHAR(128),
  mod_version   VARCHAR(32),
  PRIMARY KEY (seed_id, mod_loader_id, mod_name)
);
```

此功能不在 MVP 范围，表结构预留但不执行。

### 9.4 种子集合/收藏夹

已于 §4.11 和 §4.12 实现。`likes` 表保持纯粹的点赞语义，收藏夹作为独立实体存在。两者的正交关系见 §4.13。

### 9.5 种子变更历史

种子一旦审核通过即锁定。如果需要支持"投稿者请求修改"或管理员更新种子信息：

```sql
-- 未来可选扩展
CREATE TABLE seed_revisions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  seed_id     INTEGER NOT NULL REFERENCES seeds(id),
  changed_by  INTEGER NOT NULL REFERENCES users(id),
  changes     TEXT NOT NULL,                   -- JSON diff
  reason      VARCHAR(500),
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 10. 种子数据

### 10.1 预置标签

```sql
-- gameplay 类（投稿必选其一）
INSERT INTO tags (key, label, icon, category) VALUES
  ('survival',      '生存向',   '🏕️', 'gameplay'),
  ('speedrun',      '速通向',   '⚔️', 'gameplay'),
  ('building',      '建筑向',   '🏗️', 'gameplay'),
  ('hardcore',      '极限模式', '💀', 'gameplay'),
  ('challenge',     '挑战向',   '🎯', 'gameplay');

-- feature 类（可多选）
INSERT INTO tags (key, label, icon, category) VALUES
  ('spawn_wonder',  '出生点奇观',   '🌄', 'feature'),
  ('rare_biome',    '稀有群系',     '🍄', 'feature'),
  ('terrain',       '地形奇观',     '🏔️', 'feature'),
  ('village',       '近出生点村庄', '🏘️', 'feature'),
  ('stronghold',    '近出生点要塞', '🏰', 'feature'),
  ('ancient_city',  '古代城市',     '🏛️', 'feature'),
  ('trial_chamber', '试炼室集群',   '⚗️', 'feature'),
  ('diamond',       '资源富集',     '💎', 'feature'),
  ('island',        '孤岛生存',     '🌊', 'feature');

-- special 类（系统计算，不在投稿表单中显示）
INSERT INTO tags (key, label, icon, category) VALUES
  ('verified',      '已验证',  '✅', 'special'),
  ('hot',           '热门',    '🔥', 'special'),
  ('new',           '新版本',  '🆕', 'special');
```

### 10.2 初始版本号

```sql
INSERT INTO versions (edition, version, is_latest, sort_order) VALUES
  ('java',    '1.21.5', TRUE,  100),
  ('java',    '1.21.4', FALSE,  99),
  ('java',    '1.21.1', FALSE,  98),
  ('java',    '1.20.6', FALSE,  97),
  ('java',    '1.20.1', FALSE,  96),
  ('bedrock', '1.21.70', TRUE, 100),
  ('bedrock', '1.21.60', FALSE, 99),
  ('bedrock', '1.21.50', FALSE, 98);
```

### 10.3 初始管理员

```sql
-- 首个管理员通过环境变量或 CLI 命令创建，非 SQL 脚本
-- python -m app.cli create-admin --microsoft-id "xxx-xxx-xxx"
```

---

*文档结束 · 数据库结构变更前应先更新本文档并生成 Alembic 迁移脚本*

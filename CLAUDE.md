# SeedVault — Minecraft 种子共享平台

面向中文社群的 Minecraft 种子投稿与检索平台，轻量自部署，GitHub 开源。

## 项目文档

- `docs/mc-seed-platform-plan.md` — 项目规划（技术机制、字段设计、架构、功能、Microsoft OAuth + Minecraft 验证）
- `docs/interaction-design.md` — 交互设计（信息架构、浏览模型、详情页、认证墙、移动端、品牌、皮肤头像）
- `docs/visual-style-guide.md` — 视觉风格指南（颜色系统、字体层级、组件标记、Microsoft 登录按钮、皮肤头像、禁止清单）
- `docs/api-and-backend-design.md` — API 与后端设计（全部端点、请求/响应 Schema、数据库 DDL、存储层、Auth 中间件、服务层边界）
- `docs/database-design.md` — 数据库设计（ERD、命名规范、表详细设计、索引策略、约束、查询模式、SQLite→PG 迁移、扩展性、种子数据）

## Agent Skills（来自 taste-skill）

项目 `.claude/skills/` 目录下导入了 [taste-skill](https://github.com/Leonxlnx/taste-skill) 的全部前端设计技能，用于在构建 UI 时指导 AI 生成高质量、非模板化的界面。

### 实现类技能（输出代码）

| 技能 | 目录 | 用途 |
|------|------|------|
| **taste-skill** | `taste-skill/` | 默认前端设计技能（v2），读取需求 → 推断设计语言 → 输出界面 |
| **taste-skill-v1** | `taste-skill-v1/` | taste-skill 原始 v1 版本，供需要固定行为的场景使用 |
| **gpt-tasteskill** | `gpt-tasteskill/` | 更强制的变体，高布局方差、GSAP 动效 |
| **image-to-code-skill** | `image-to-code-skill/` | 图片优先流程：生成参考 → 分析 → 实现 |
| **redesign-skill** | `redesign-skill/` | 现有项目 UI 审查与重构 |
| **soft-skill** | `soft-skill/` | 高端柔和 UI：低对比、留白、Spring 动效 |
| **output-skill** | `output-skill/` | 禁止截断输出，强制完整代码生成 |
| **minimalist-skill** | `minimalist-skill/` | 极简编辑风 UI（Notion/Linear 风格） |
| **brutalist-skill** | `brutalist-skill/` | 粗野主义：瑞士字体、极端对比、实验性布局 |
| **stitch-skill** | `stitch-skill/` | Google Stitch 兼容设计规则 |

### 图片生成类技能（仅输出参考图，不写代码）

| 技能 | 目录 | 用途 |
|------|------|------|
| **imagegen-frontend-web** | `imagegen-frontend-web/` | 网站设计参考图 |
| **imagegen-frontend-mobile** | `imagegen-frontend-mobile/` | 移动端设计参考图 |
| **brandkit** | `brandkit/` | 品牌套件（Logo、配色、字体）参考图 |

### 使用方式

在对话中附加对应技能文件或通过 skill 名称引用即可激活。示例：

- "用 taste-skill 帮我设计种子详情页"
- "用 minimalist-skill 构建搜索页面"
- "用 output-skill 确保生成完整代码"

详见各技能目录下的 `SKILL.md` 及 `llms.txt` 索引。

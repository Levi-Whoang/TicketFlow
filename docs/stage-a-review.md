# 阶段 A 文档与工程约定评审

> 更新时间：2026-11-17 15:00（Asia/Shanghai）  
> 对应门禁：`A-GATE`  
> 评审结论：**通过，可进入阶段 B**  
> 状态：设计已放行；后端数据库底座尚未实现

## 1. 评审输入

| 输入 | 用途 |
| --- | --- |
| [产品需求.md](../产品需求.md) | 核对业务范围、角色、状态、非功能要求 |
| [architecture.md](architecture.md) | 核对模块职责和异步/同步数据库边界 |
| [data-model.md](data-model.md) | 核对实体、关系、唯一约束和写入集合 |
| [state-machine.md](state-machine.md) | 核对状态、动作、角色和禁止路径 |
| [api-conventions.md](api-conventions.md) | 核对路径、分页、时间、认证、幂等和错误协议 |
| `backend/app/` | 核对当前已有应用工厂、配置和基础设施 |
| `任务进度.md` | 核对阶段 A 任务完成标准 |

## 2. 评审方法

本次评审采用两种方式：

1. 使用文本检索核对状态、角色、令牌版本、异步/同步 Session 和幂等等关键词是否在文档间一致。
2. 人工评审完整业务流程、事务边界、权限所有权和并发条件。

本次评审不创建数据库、ORM 或认证代码，因此不声称数据库结构已经实际运行。

## 3. 一致性与冲突检查

### 3.1 产品范围

| 检查项 | 结果 |
| --- | --- |
| 单企业内部系统 | 一致 |
| 员工、技术人员、管理员三类角色 | 一致 |
| 账号可多角色 | 一致 |
| 故障报修、软件申请、权限申请 | 一致 |
| 不包含多租户、附件、WebSocket、全文搜索、自动派单 | 一致 |
| Outbox 标记为 P2 可选 | 一致 |

结论：设计没有扩大 MVP 范围。

### 3.2 状态与数据模型

数据模型与状态机共同使用以下状态集合：

- `pending_acceptance`
- `assigned`
- `in_progress`
- `pending_confirmation`
- `closed`
- `cancelled`
- `rejected`

核对结果：

- 工单模型包含状态、处理人、提交人、时间、拒绝原因和软删除字段。
- 状态历史可以保存原状态、目标状态、操作人、原因和时间。
- 评论模型支持公开回复和内部备注。
- 审计模型支持 actor、action、前后值和原因。
- 模型具备执行全部分配、领取、处理、确认和重新打开动作所需的持久字段。

结论：没有缺少状态机所需的数据结构。

### 3.3 角色与所有权

| 规则 | 数据模型 | 状态机 | API 约定 |
| --- | --- | --- | --- |
| 多角色并集 | `USER_ROLES` | 多角色并集 | 每次请求加载当前角色 |
| 员工确认权 | `submitted_by_id` | 提交员工 | JWT 仅提供用户 ID |
| 技术员处理权 | `assignee_id` | 当前处理人 | 服务端重新加载角色 |
| 管理员分配 | `USER_ROLES` + 工单 | 管理员 | 管理员动作接口 |

员工基础角色的实现约定：

- 所有业务账号保留 `employee` 基础角色。
- 管理员或技术人员若同时有员工角色，可以提交自己的工单。
- 其管理员能力不能代替其他员工执行确认或重新打开。

结论：多角色权限并集与“只能处理本人关系”没有冲突。

### 3.4 动作与 API 映射

| 状态机动作 | API 入口 |
| --- | --- |
| `create` | `POST /api/v1/tickets` |
| `assign` | `POST /api/v1/tickets/{id}/assign` |
| `claim` | `POST /api/v1/tickets/{id}/claim` |
| `transfer` | `POST /api/v1/tickets/{id}/transfer` |
| `start` | `POST /api/v1/tickets/{id}/start` |
| `resolve` | `POST /api/v1/tickets/{id}/resolve` |
| `confirm_close` | `POST /api/v1/tickets/{id}/close` |
| `reopen` | `POST /api/v1/tickets/{id}/reopen` |
| `cancel` | `POST /api/v1/tickets/{id}/cancel` |
| `reject` | `POST /api/v1/tickets/{id}/reject` |
| `edit` | `PATCH /api/v1/tickets/{id}` |
| `adjust_priority` | `PATCH /api/v1/tickets/{id}/priority` |
| `add_public_comment` | `POST /api/v1/tickets/{id}/comments` |
| `add_internal_note` | `POST /api/v1/tickets/{id}/comments` |
| `soft_delete` | `DELETE /api/v1/tickets/{id}` |

结论：状态机所有业务动作都有唯一 HTTP 入口，没有只存在于文档却没有协议入口的动作。

### 3.5 事务和一致性

核对结果：

- 创建工单、幂等记录、初始状态历史、审计和 SLA 快照在同一事务中。
- 分配、领取和转派与状态历史、审计处于同一事务。
- 解决、重新打开和关闭与状态历史、审计处于同一事务。
- SLA 事件由数据库唯一键去重。
- Repository 不提交业务事务，Service 是默认事务所有者。
- 外部邮件发送放在数据库提交之后，不长时间占用事务。

结论：事务边界足以支持后续完整流程和并发验收。

### 3.6 异步与同步数据库边界

| 检查项 | 设计 |
| --- | --- |
| FastAPI 驱动 | `asyncmy` + `AsyncEngine` + `AsyncSession` |
| Celery 驱动 | `pymysql` + 独立同步 `Engine` + `Session` |
| Session 生命周期 | API 每请求；Celery 每任务 |
| 共享范围 | 仅共享配置、ORM Model、纯 Domain 规则 |
| 禁止共享 | Engine 连接池、Session、事务、ASGI 依赖 |
| Alembic/Seed | 独立短生命周期同步 Session |

结论：异步和同步数据库执行方式边界明确，没有 Session 复用冲突。

### 3.7 认证与令牌失效

核对结果：

- 数据模型包含 `is_active`、`must_change_password` 和 `token_version`。
- JWT 包含 `sub`、`ver`、`scope`，每次请求从数据库加载用户和角色。
- 停用、改密和管理员重置密码都提升 `token_version`。
- 旧 JWT 因版本不匹配、账号停用或自然过期统一返回 401。
- 角色变更不提升版本，但下一次请求立即使用数据库最新角色。
- 首次改密令牌只允许访问改密接口。

结论：认证数据结构足以支持旧令牌失效和首次改密要求。

### 3.8 分页、时间与排序

核对结果：

- 所有列表统一 `items + pagination`。
- 分页上限固定为 100。
- 时间统一 UTC RFC 3339。
- 排序有 `id` 第二排序字段。
- 优先级排序使用明确业务等级，不依赖字符串字典序。

结论：协议可以直接映射 Pydantic Schema 和 SQLAlchemy 排序。

### 3.9 幂等与并发

核对结果：

- 创建工单必须提供 `Idempotency-Key`。
- 同用户、同键和同请求摘要返回原工单。
- 同键不同请求返回 409。
- 幂等记录与工单同一事务。
- 幂等键具有数据库唯一约束。
- 领取使用条件更新或行锁，并依赖真实 MySQL 最终验收。

结论：API 幂等和状态机领取并发规则没有冲突。

### 3.10 SLA 与通知

核对结果：

- SLA 规则按类型和优先级配置。
- 建单时生成独立 SLA 快照。
- 首次公开回复更新响应时间，内部备注不更新。
- 首次解决写入解决达成时间，重新打开沿用原目标。
- SLA 事件使用数据库唯一键去重。
- 未分配超时只通知管理员；已分配时通知处理人和管理员。
- 邮件发送失败不回滚已提交业务。

结论：SLA 数据模型、状态动作和异步任务边界一致。

### 3.11 安全与错误

核对结果：

- 未认证、停用、改密后的旧令牌统一返回 401。
- 角色和所有权不满足返回 403。
- 不可见资源返回 404。
- 非法状态和重复动作返回 409。
- Schema 错误返回 422。
- 错误响应不泄露 SQL、密码、JWT、配置或堆栈。
- 访问日志不记录认证头、查询串、请求体和响应体。

结论：认证协议与现有统一错误、请求日志实现兼容。

## 4. 评审发现与处理

| 编号 | 发现 | 处理 | 是否阻塞 |
| --- | --- | --- | --- |
| A-R1 | 首次改密令牌原设计允许访问 `/auth/me`，比“只能访问改密接口”更宽 | 已改为只允许 `/auth/change-password` | 已解决 |
| A-R2 | `priority` 排序未说明业务等级 | 已明确 `urgent > high > medium > low` | 已解决 |
| A-R3 | `/tickets/pool` 与 `/tickets/{ticket_id}` 存在路由匹配顺序风险 | API 文档已要求静态路径先注册 | 已解决 |
| A-R4 | D16 的“未完成状态可拒绝”可能被解释得比产品流程图更宽 | 门禁采用更严格的待受理状态拒绝，与明确流程图一致 | 已冻结 |
| A-R5 | 当前 `.env.example` 只有异步测试 DSN | `B-09` 必须增加同步测试 DSN 或明确可验证的派生规则 | 非阻塞后续 |
| A-R6 | 当前没有真实 MySQL 或并发测试 | `B-09`、`B-10` 和后续 MySQL 验收任务负责 | 非阻塞后续 |
| A-R7 | Outbox 仍是 P2 | 文档未把可靠 Outbox 写成已实现能力 | 已解决 |

“非阻塞后续”表示不影响阶段 A 设计放行，但必须在对应阶段实现完成前解决，不能带病进入最终验收。

## 5. 冻结的跨文档决定

1. 状态集合和角色代码以 `data-model.md` 与 `state-machine.md` 为准。
2. 状态动作合法性以 `state-machine.md` 为唯一规则来源。
3. HTTP 入口以 `api-conventions.md` 为唯一路径来源。
4. 事务与异步/同步 Session 边界以 `architecture.md` 为准。
5. 认证失败不泄露具体原因，统一返回 401。
6. 首次改密 scope 只能访问改密接口。
7. 业务状态以 MySQL 为最终事实来源。
8. 真实 MySQL 是并发、唯一约束和幂等最终验收环境。
9. P2 Outbox 未经实现前不能声称具备可靠异步投递。
10. 任一新状态、动作、路径或表关系必须先更新设计文档和测试，再改代码。

## 6. 阶段 B 实施条件

阶段 B 可以开始，但必须遵守：

- `B-05` 建立独立 `AsyncEngine` 和请求级 `AsyncSession`。
- `B-06` 建立独立同步 `Engine` 和同步 Session 工厂。
- `B-09` 配置独立真实 MySQL 测试库，并补齐同步测试连接配置。
- `B-10` 让 API 测试和同步任务测试分别使用正确的 Session 工厂。
- 不在 Celery 任务中导入 ASGI 数据库依赖或路由。
- 不把 SQLite 结果作为并发、幂等和唯一约束的最终证据。
- 不跳过 `B-01` 直接开始账号或工单业务。

## 7. 门禁结论

| 门禁检查 | 结论 |
| --- | --- |
| 数据模型与状态机 | 通过 |
| 状态机与权限矩阵 | 通过 |
| 状态动作与 API 路径 | 通过 |
| API 与统一错误响应 | 通过 |
| JWT 与令牌版本失效 | 通过 |
| 事务与审计边界 | 通过 |
| FastAPI 异步 / Celery 同步边界 | 通过 |
| 幂等与并发规则 | 通过 |
| 当前实现与文档能力描述 | 通过，未把未来功能写成已实现 |

**最终结论：`A-GATE` 通过，可以开始阶段 B 的 `B-01`。**

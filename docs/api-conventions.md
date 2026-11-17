# TicketFlow API 与令牌失效约定

> 更新时间：2026-11-17 14:47（Asia/Shanghai）  
> 对应任务：`A-12`  
> 架构基线：[architecture.md](architecture.md)  
> 数据模型：[data-model.md](data-model.md)  
> 状态规则：[state-machine.md](state-machine.md)  
> 状态：接口协议基线；认证和业务接口尚未实现

## 1. 协议目标

本文统一 TicketFlow 第一版 API 的路径、分页、时间、排序、认证、幂等和错误行为，确保前端、Swagger、测试和后续 Service 使用同一套协议。

本文不代表接口已经存在。当前实际可访问接口只有：

- `GET /health`
- `GET /docs`
- `GET /redoc`
- `GET /openapi.json`

## 2. 基础协议

| 项目 | 约定 |
| --- | --- |
| 传输协议 | 第一版单机环境使用 HTTP；部署层可终止 TLS |
| 数据格式 | `application/json; charset=utf-8` |
| 字段命名 | 请求和响应 JSON 使用 `snake_case` |
| 路径命名 | 小写、复数资源名，组合词使用 kebab-case |
| API 版本 | 业务接口统一前缀 `/api/v1` |
| 健康检查 | `/health` 不进版本前缀，便于部署探针稳定调用 |
| 文档 | `/docs`、`/redoc`、`/openapi.json` 不进版本前缀 |
| 时间 | RFC 3339 UTC，带 `Z` 后缀 |
| ID | 对外使用数值 ID；路径示例 `/tickets/123` |
| OpenAPI | Swagger 必须能完成登录、Authorize 和主要业务请求 |

破坏兼容性的修改创建 `/api/v2`，不在 `/api/v1` 中悄悄改变字段含义。

## 3. 请求头

| 请求头 | 使用范围 | 约定 |
| --- | --- | --- |
| `Authorization` | 受保护接口 | `Bearer <JWT>` |
| `Content-Type` | 有请求体接口 | `application/json` |
| `Accept` | 可选 | 推荐 `application/json` |
| `Idempotency-Key` | 创建工单 | 必填，详见幂等约定 |

服务端不接受客户端指定请求 ID。每次请求由中间件生成新的 `X-Request-ID` 并放入响应头。

## 4. 响应头

| 响应头 | 说明 |
| --- | --- |
| `X-Request-ID` | 当前请求的唯一 UUID |
| `WWW-Authenticate: Bearer` | 401 认证失败时返回 |
| `Retry-After` | 429 限流时返回建议等待秒数 |
| `Idempotency-Replayed` | 幂等重放时返回 `true` |

## 5. API 路径目录

### 5.1 公开与认证

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/health` | 进程健康检查 |
| `POST` | `/api/v1/auth/login` | 用户名或邮箱加密码登录 |
| `GET` | `/api/v1/auth/me` | 当前用户与角色 |
| `POST` | `/api/v1/auth/change-password` | 用户修改自己的密码；首次改密令牌允许访问 |

### 5.2 管理员账号管理

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `POST` | `/api/v1/users` | 创建员工或技术人员账号 |
| `GET` | `/api/v1/users` | 分页查询账号 |
| `GET` | `/api/v1/users/{user_id}` | 查询账号详情 |
| `PATCH` | `/api/v1/users/{user_id}/status` | 启用或停用账号 |
| `PUT` | `/api/v1/users/{user_id}/roles` | 设置用户角色集合 |
| `POST` | `/api/v1/users/{user_id}/password-reset` | 管理员重置密码 |

### 5.3 工单

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `POST` | `/api/v1/tickets` | 创建工单，要求 `Idempotency-Key` |
| `GET` | `/api/v1/tickets` | 按权限查询工单列表 |
| `GET` | `/api/v1/tickets/pool` | 技术人员查询待领取池 |
| `GET` | `/api/v1/tickets/{ticket_id}` | 查询工单详情 |
| `PATCH` | `/api/v1/tickets/{ticket_id}` | 分配前编辑本人工单 |
| `PATCH` | `/api/v1/tickets/{ticket_id}/priority` | 管理员调整优先级 |
| `POST` | `/api/v1/tickets/{ticket_id}/assign` | 管理员分配 |
| `POST` | `/api/v1/tickets/{ticket_id}/claim` | 技术人员领取 |
| `POST` | `/api/v1/tickets/{ticket_id}/transfer` | 管理员转派 |
| `POST` | `/api/v1/tickets/{ticket_id}/start` | 当前处理人开始处理 |
| `POST` | `/api/v1/tickets/{ticket_id}/resolve` | 当前处理人标记已解决 |
| `POST` | `/api/v1/tickets/{ticket_id}/close` | 提交员工确认关闭 |
| `POST` | `/api/v1/tickets/{ticket_id}/reopen` | 提交员工重新打开 |
| `POST` | `/api/v1/tickets/{ticket_id}/cancel` | 提交员工取消待受理工单 |
| `POST` | `/api/v1/tickets/{ticket_id}/reject` | 管理员拒绝待受理工单 |
| `DELETE` | `/api/v1/tickets/{ticket_id}` | 管理员软删除异常工单 |

### 5.4 评论与历史

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/api/v1/tickets/{ticket_id}/comments` | 按权限查询员工回复和内部备注 |
| `POST` | `/api/v1/tickets/{ticket_id}/comments` | 添加公开回复或内部备注 |
| `GET` | `/api/v1/tickets/{ticket_id}/history` | 查询状态历史和审计动作 |

### 5.5 通知

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/api/v1/notifications` | 查询本人通知和未读数 |
| `PATCH` | `/api/v1/notifications/{notification_id}/read` | 标记本人单条通知已读 |
| `POST` | `/api/v1/notifications/read-all` | 标记本人全部通知已读 |

### 5.6 SLA、统计与审计

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/api/v1/sla-rules` | 管理员查询 SLA 规则 |
| `POST` | `/api/v1/sla-rules` | 管理员创建 SLA 规则 |
| `PATCH` | `/api/v1/sla-rules/{rule_id}` | 管理员修改 SLA 规则 |
| `GET` | `/api/v1/statistics/tickets` | 管理员查询工单与 SLA 统计 |
| `GET` | `/api/v1/statistics/technicians` | 管理员查询技术员负载 |
| `GET` | `/api/v1/audit-logs` | 管理员查询只读审计 |

命令式业务动作使用 `POST /资源/{id}/动作`，因为这些动作包含状态机和权限规则，不能用普通字段更新替代。

## 6. 分页协议

### 6.1 请求参数

| 参数 | 类型 | 默认值 | 约束 |
| --- | --- | --- | --- |
| `page` | integer | `1` | 最小 1 |
| `page_size` | integer | `20` | 1 至 100 |

参数超出范围返回 422 `VALIDATION_ERROR`。

### 6.2 列表响应

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 0,
    "pages": 0
  }
}
```

`pages` 使用向上取整。无数据时 `pages=0`。所有列表接口保持该结构，不能在某个接口中改成裸数组。

## 7. 筛选与排序

### 7.1 工单筛选

| 参数 | 含义 |
| --- | --- |
| `status` | 工单状态 |
| `ticket_type` | `fault`、`software`、`permission` |
| `priority` | 优先级枚举 |
| `assignee_id` | 处理人 ID，仅允许有相应管理范围的角色使用 |
| `created_from` | 创建时间下限，包含边界 |
| `created_to` | 创建时间上限，包含边界 |
| `updated_from` | 更新时间下限 |
| `updated_to` | 更新时间上限 |
| `keyword` | 标题和描述关键词 |

时间范围必须满足 `from <= to`。非法枚举返回 422。

### 7.2 排序参数

| 参数 | 默认值 | 可选值 |
| --- | --- | --- |
| `sort_by` | `updated_at` | 各接口白名单，如 `created_at`、`updated_at`、`priority` |
| `sort_order` | `desc` | `asc`、`desc` |

每个列表查询必须追加 `id` 作为第二排序字段，避免相同时间值导致分页结果抖动或重复。

## 8. 时间与时长

### 8.1 时间格式

响应时间统一使用 UTC RFC 3339：

```text
2026-11-17T06:47:00Z
```

- 数据库以 UTC 保存。
- API 输入时间必须带时区，服务端转换为 UTC。
- 前端负责转换为用户本地时间。
- 不允许只发送日期或省略时区。
- 日期筛选边界默认包含 `from` 和 `to`。

### 8.2 时长格式

- 耗时和 SLA 时长使用整数秒。
- 分页数量和统计数量使用整数。
- 布尔字段使用 JSON `true` / `false`。
- 空值使用 JSON `null`，不使用空字符串代替。

## 9. JWT 认证协议

### 9.1 登录请求与响应

登录成功后返回：

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "expires_in": 1800,
  "must_change_password": false
}
```

第一版只使用短期访问令牌，不实现 Refresh Token。令牌过期后重新登录。

### 9.2 JWT 声明

| 声明 | 含义 |
| --- | --- |
| `sub` | 用户 ID 的十进制字符串 |
| `ver` | 签发时用户 `token_version` |
| `scope` | `api` 或 `password_change` |
| `iss` | TicketFlow |
| `aud` | ticketflow-api |
| `iat` | 签发时间 |
| `exp` | 过期时间 |
| `jti` | 本次令牌唯一 ID |

JWT 不包含可信角色清单。角色每次从数据库用户角色关联加载，避免角色撤销后旧令牌继续携带旧权限。

### 9.3 每次认证流程

1. 从 `Authorization: Bearer` 读取令牌。
2. 校验签名、算法、签发方、受众和过期时间。
3. 根据 `sub` 从数据库加载当前用户。
4. 检查用户存在且 `is_active=true`。
5. 比较 JWT `ver` 与数据库 `token_version`。
6. 根据 `scope` 判断当前接口是否允许。
7. 从数据库加载当前角色并执行权限判断。

任何认证失败统一返回 401：

```http
WWW-Authenticate: Bearer
```

错误响应不区分“令牌过期、签名错误、账号停用、版本不匹配”，避免泄露账号或令牌状态。

### 9.4 首次改密

管理员建号或重置密码后：

- 登录成功返回 `must_change_password=true`。
- 令牌 `scope=password_change`，只能访问 `/api/v1/auth/me` 和 `/api/v1/auth/change-password`。
- 访问业务接口返回 403 `AUTHORIZATION_DENIED`。
- 改密成功后提升 `token_version`，旧令牌立即失效；用户重新登录获得 `scope=api` 令牌。

## 10. 令牌失效表

| 事件 | 数据库变化 | 事件前旧 JWT | 新登录 | 后续处理 |
| --- | --- | --- | --- | --- |
| 用户修改密码 | 更新密码哈希，`token_version += 1` | 401 | 使用新密码成功 | 获得新 JWT |
| 管理员重置密码 | 更新哈希，`must_change_password=true`，`token_version += 1` | 401 | 使用临时密码成功，只能改密 | 改密后重新登录 |
| 管理员停用账号 | `is_active=false`，`token_version += 1` | 401 | 401 | 不能访问业务 |
| 管理员启用账号 | `is_active=true`，不恢复旧版本 | 401 | 启用后使用有效密码登录 | 旧令牌仍不可恢复 |
| 管理员授予或撤销角色 | 更新用户角色关联，不修改 `token_version` | 令牌本身仍有效 | 无需重新登录 | 下一次请求按数据库最新角色鉴权 |
| JWT 自然过期 | 无数据库变化 | 401 | 重新登录 | 不能继续使用 |

停用、改密或重置密码的数据库写操作必须提交成功后再向客户端返回成功。旧 JWT 下一次请求会因版本或启用状态检查而失败。

第一版不提供“只撤销某一个设备令牌”的服务端登出。需要立即撤销所有令牌时提升 `token_version`。

## 11. 幂等协议

### 11.1 适用范围

`Idempotency-Key` 第一版只要求用于：

```text
POST /api/v1/tickets
```

### 11.2 请求头格式

- 必须为非空字符串。
- 长度 16 至 128 个字符。
- 允许 ASCII 字母、数字、`.`、`_`、`-`、`:`。
- 推荐客户端生成 UUID。
- 同一个键不能用于不同创建请求。

缺失、空值、格式非法或超长返回 400 `INVALID_REQUEST`。

### 11.3 行为

| 场景 | 行为 |
| --- | --- |
| 首次请求 | 创建工单并返回 201 |
| 同用户、同键、同请求摘要 | 返回原响应，不重复建单；增加 `Idempotency-Replayed: true` |
| 同用户、同键、不同请求摘要 | 返回 409 `BUSINESS_CONFLICT` |
| 并发相同请求 | 数据库唯一约束保证只生成一张工单；失败竞争方读取已有记录 |

幂等记录与工单创建处于同一事务。任一写入失败时，两者都不能部分存在。

请求摘要对规范化 JSON 计算；字段顺序不同但语义相同不能被视为不同请求。摘要和幂等键不得进入访问日志或响应体。

## 12. 错误响应与状态码

统一错误结构：

```json
{
  "error": {
    "code": "BUSINESS_CONFLICT",
    "message": "工单状态不允许该操作",
    "details": []
  }
}
```

| HTTP 状态 | 场景 |
| --- | --- |
| 200 | 查询、更新或状态动作成功 |
| 201 | 工单或账号创建成功 |
| 204 | 软删除或不需要响应体的成功动作 |
| 400 | 幂等键格式错误等通用请求错误 |
| 401 | 未登录、令牌无效、过期、账号停用或令牌版本不匹配 |
| 403 | 角色、所有权或令牌 scope 不允许 |
| 404 | 资源不存在或对当前用户不可见 |
| 409 | 状态冲突、重复动作、幂等键内容冲突 |
| 422 | Schema 校验失败、非法枚举、分页或字段越界 |
| 429 | 接口超过限流阈值，后续返回 `Retry-After` |

500 只返回通用信息，不泄露 SQL、堆栈、密码、令牌或内部配置。

## 13. 数据可见性与响应边界

- 响应使用 Pydantic Schema，不直接序列化 ORM。
- 用户响应从不包含 `password_hash`。
- 工单详情按角色返回，技术人员不能读取非本人负责且不在待领取池的工单。
- 员工响应不包含内部备注。
- 通知只允许接收人读取和修改已读状态。
- 审计和统计只允许管理员访问。
- 分页总数只统计当前用户可见数据。

## 14. Swagger 与测试要求

Swagger 至少支持：

1. 登录并取得 JWT。
2. 点击 Authorize 输入 Bearer Token。
3. 获取当前用户。
4. 创建带 `Idempotency-Key` 的工单。
5. 调用分配、领取、开始、解决、确认和重新打开动作。
6. 查看统一 401、403、404、409 和 422 示例。

自动化测试必须覆盖：

- 正确登录、错误密码和停用账号登录。
- JWT 过期、签名篡改、错误受众和版本不匹配。
- 停用、改密、管理员重置密码后的旧 JWT 返回 401。
- 角色撤销后下一次请求立即失去权限。
- 首次改密令牌不能访问业务接口。
- 分页边界、非法排序、时间格式和非法枚举。
- 缺失或非法 `Idempotency-Key`。
- 同键同请求重放和同键不同请求冲突。
- 错误响应不泄露敏感信息。

## 15. 冻结决策

1. 业务路径固定使用 `/api/v1`。
2. 列表统一返回 `items + pagination`。
3. 时间统一使用 UTC RFC 3339。
4. 排序必须有 `id` 第二排序字段。
5. 认证只使用 `Authorization: Bearer <JWT>`。
6. JWT 角色不可信，每次从数据库加载。
7. 停用、改密和管理员重置密码必须提升 `token_version`。
8. 旧令牌全部认证失败统一返回 401。
9. 创建工单必须提供 `Idempotency-Key`。
10. 命令式状态动作使用 `POST /资源/{id}/动作`。
11. 业务错误继续使用现有统一错误结构。
12. 不实现 Refresh Token，第一版短期令牌过期后重新登录。

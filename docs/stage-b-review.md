# 阶段 B 后端底座门禁评审

> 更新时间：2026-11-18 15:47（Asia/Shanghai）  
> 对应门禁：`B-GATE`  
> 评审结论：**通过，可进入阶段 C**  
> 状态：后端底座已放行；账号和工单业务尚未实现

## 1. 验收范围

阶段 B 交付以下能力：

- MySQL 与 Redis 本地 Compose 服务。
- MySQL 具名持久卷。
- 类型化配置加载和启动失败校验。
- FastAPI 请求级异步 Engine / Session。
- Celery 独立同步 Engine / Session。
- ORM 通用基类。
- Alembic 空库迁移。
- 真实 MySQL 测试库与 pytest Fixture。
- 真实 API、Swagger 和 OpenAPI。

本门禁不验收账号、权限、工单业务表或 Celery Worker 业务任务。

## 2. 环境与版本

| 项目 | 验证结果 |
| --- | --- |
| Python | 3.12.13 |
| Docker Engine | 29.9.3 |
| Docker Compose | v5.7.0 |
| MySQL | 8.4.13 |
| Redis | 7.4 Alpine |
| MySQL 宿主端口 | 3307（避开本机已有 3306） |
| Redis 宿主端口 | 6379 |
| API 端口 | 8765 |

## 3. 验收检查

### 3.1 Compose 与依赖服务

| 检查 | 结果 |
| --- | --- |
| `docker compose config` | 通过 |
| MySQL 容器健康 | `healthy` |
| Redis 容器健康 | `healthy` |
| Redis `PING` | `PONG` |
| MySQL 具名卷 | `ticketflow_mysql_data` |
| Compose 停止并重新启动 | MySQL、Redis 均恢复 `healthy` |
| 停止时是否删除卷 | 否，使用 `compose down` 未使用 `-v` |

注意：本门禁验证的是保留具名卷的停启。最终 `J-06` 仍需在独立空卷和独立 Compose 项目上验证一键冷启动，不能由本门禁替代。

### 3.2 配置加载与安全

| 检查 | 结果 |
| --- | --- |
| 本地 `.env` | 已创建并被 Git 忽略 |
| `.env.example` | 30 个唯一变量，不含真实凭据 |
| 缺失关键配置 | 启动被拒绝 |
| 非法数据库/Redis URL | 启动被拒绝 |
| JWT 密钥过短 | 启动被拒绝且不回显密钥 |
| 测试库与开发库相同 | 启动被拒绝 |
| 异步/同步测试库不同 | 启动被拒绝 |
| 生产环境开启 DEBUG | 启动被拒绝 |
| Uvicorn 使用有效配置 | 启动成功 |

### 3.3 异步数据库边界

| 检查 | 结果 |
| --- | --- |
| 驱动 | `mysql+asyncmy` |
| Engine | 应用 lifespan 创建并释放 |
| Session | 请求依赖创建、异常回滚、结束关闭 |
| 连接池检查 | `pool_pre_ping=true` |
| 真实依赖查询 | 测试路由执行 `SELECT 1` 成功 |

### 3.4 同步数据库边界

| 检查 | 结果 |
| --- | --- |
| 驱动 | `mysql+pymysql` |
| Engine | 与异步 Engine 对象独立 |
| Session | 同步 Session 工厂独立 |
| 真实同步查询 | `SELECT 1` 成功 |
| 共享 AsyncSession | 无 |

### 3.5 ORM 与迁移

| 检查 | 结果 |
| --- | --- |
| ORM 基类 | `BaseModel` 统一主键、创建时间和更新时间 |
| 约束命名 | 已验证 |
| Alembic 配置 | 从应用同步数据库 URL 读取 |
| 空测试库 | `ticketflow_test` 已重建 |
| 初始迁移 | `1a1c0287ed47` |
| 迁移后表 | 只有 `alembic_version` |
| 业务表提前创建 | 无 |

### 3.6 测试隔离

| 检查 | 结果 |
| --- | --- |
| 异步 MySQL Fixture | 使用 `AsyncSession` |
| 同步 MySQL Fixture | 使用同步 `Session` |
| 测试库清理 | 每个数据库测试前后清理 |
| 清理目标保护 | 数据库名必须为 `ticketflow_test` |
| 前序数据残留 | 无 |
| 测试后表 | 只保留 `alembic_version` |
| 完整测试套件 | 38 个测试通过 |

### 3.7 真实 API

| 检查 | 结果 |
| --- | --- |
| API 启动 | 成功 |
| `GET /health` | 200，`{"status":"ok"}` |
| `GET /docs` | 200，Swagger 正常 |
| `GET /openapi.json` | 200，TicketFlow 0.1.0 |
| OpenAPI 版本 | 3.1.0 |
| OpenAPI `/health` | 存在 |
| 请求 ID | 响应头存在 |
| 结构化访问日志 | JSON 正常工作 |

`/health` 是进程存活探针，不单独证明 MySQL 或 Redis 可用；本门禁通过真实 MySQL 测试、Redis `PING` 和迁移结果分别验证外部依赖。

## 4. 已验证的失败路径

- 缺失关键配置阻止 API 启动。
- 非法配置阻止 API 启动。
- 错误信息不回显密码或 JWT。
- 异步 Session 异常时回滚。
- 数据库设施未初始化时拒绝访问。
- 清理逻辑拒绝非测试数据库。
- 测试数据不会跨测试残留。

## 5. 非阻塞风险与后续任务

| 风险 | 处理 |
| --- | --- |
| Celery App 尚未接入 | 架构导入边界测试放到 Celery 实际接入阶段 |
| 健康接口不检查外部依赖 | G/B-GATE 后续可使用数据库与 Redis 集成测试或专用 readiness |
| 当前没有业务表 | C-01 添加首个 RBAC 迁移 |
| 没有独立空 Docker 卷冷启动 | J-06 验证，不能用当前门禁替代 |
| 本机 3306 已有 MySQL | 项目固定使用 3307，文档和配置已统一 |

## 6. 放行条件

阶段 C 开始后必须遵守：

- 业务模型继承 `BaseModel`。
- 每个新表通过 Alembic 迁移，不手工改数据库。
- API 使用 `AsyncSession`，Celery 使用同步 `Session`。
- 用户、角色和令牌版本字段写入真实 MySQL。
- 每次请求从数据库读取当前账号、启用状态、角色和 `token_version`。
- 测试使用 `ticketflow_test` Fixture，不连接开发库清理数据。

## 7. 门禁结论

| 门禁要求 | 结论 |
| --- | --- |
| API 可启动 | 通过 |
| MySQL 可连接 | 通过 |
| Redis 可连接 | 通过 |
| 空库迁移可执行 | 通过 |
| 真实 MySQL 测试可运行 | 通过 |
| 异步 Engine 可独立创建 | 通过 |
| 同步 Engine 可独立创建 | 通过 |
| 测试数据自动清理 | 通过 |
| 文档与实际能力一致 | 通过 |

**最终结论：`B-GATE` 通过，可以进入阶段 C 的 `C-01`。**

# Secure Payment Integration & Audit Demo —— 验收说明

## 文档目的

本文件用于对 **Secure Payment Integration & Audit Demo** 进行验收。

注意：本项目用于展示在 **PBOC-style** 或 **PCI-oriented** 支付环境中常见的工程控制点，**不是正式合规认证项目**，也**不代表通过任何审计**。

---

## 验收目标

验收时重点确认该 demo 是否已经体现以下能力：

- sensitive data masking
- RBAC
- audit logging
- signed webhook verification
- idempotent transaction handling
- secure configuration management
- risk-control checkpoints
- production-flavored engineering structure

---

## 一、基础运行验收

### 1. 本地可启动
验收标准：
- 可以通过 `docker compose up --build` 或 README 说明中的方式启动
- backend 服务可正常访问
- database 正常连接
- health endpoint 可返回成功状态

### 2. 配置清晰
验收标准：
- 存在 `.env.example`
- secrets 没有硬编码在源码中
- README 对本地运行步骤说明清楚

---

## 二、认证与权限验收

### 3. 登录能力
验收标准：
- 存在登录接口，例如 `POST /auth/login`
- 登录后可拿到 JWT 或其他 token
- 未登录用户无法访问受保护接口

### 4. RBAC
至少存在以下角色：
- `admin`
- `operator`
- `auditor`

验收标准：
- `admin` 可查看较完整的系统能力
- `operator` 可发起/查看交易，但不能执行高权限配置操作
- `auditor` 可查看 audit logs，但不能创建交易
- 未授权访问会被正确拒绝

---

## 三、支付流程验收

### 5. Payment Creation
验收标准：
- 可成功发起 payment request
- 至少包含：
  - `request_no`
  - `merchant_id`
  - `amount`
  - `currency`
  - `channel`
  - payment identifier input
- 后端会创建 transaction record

### 6. Transaction State Machine
验收标准：
- 至少存在以下 states：
  - `CREATED`
  - `PENDING_RISK`
  - `APPROVED`
  - `REJECTED`
  - `SETTLED`
  - `FAILED`
  - `REVERSED`
- state transition 受后端控制
- 不允许非法状态跳转
- `REJECTED` transaction 不能直接 `SETTLED`

### 7. Idempotency
验收标准：
- 使用相同 `request_no` 重复提交时，不会创建重复 transaction
- 系统能返回相同 transaction 或明确提示幂等结果

---

## 四、风控与安全控制验收

### 8. Risk-Control Workflow
验收标准：
- 系统存在最少 3 条 risk rules
- transaction 创建后会经过 risk step
- risk result 可被查询
- risk result 至少包含：
  - decision
  - triggered rules
  - timestamp

### 9. Sensitive Data Masking
验收标准：
- 响应中不暴露 raw sensitive payment data
- database 中不直接保存原始敏感字段，或至少主表中不明文保存
- logs 中敏感字段已 masking
- 示例：
  - 输入 `6222021234567890`
  - 展示/返回 `************7890`

### 10. Signed Webhook Verification
验收标准：
- 存在 webhook endpoint
- 支持 HMAC signature verification
- 支持 timestamp validation
- 有 replay protection（nonce 或等价机制）
- valid webhook 可推进 transaction state
- invalid webhook 会被拒绝并写入 audit log 或 system log

---

## 五、审计与可追踪性验收

### 11. Audit Logging
以下操作应至少有 audit log：
- login
- payment creation
- risk decision
- settlement request
- reversal request
- webhook handling
- 关键权限失败（如果实现）

验收标准：
- audit log 可查询
- audit record 包含：
  - timestamp
  - actor
  - actor_role
  - action
  - result
  - trace_id / request_id
- audit 内容不泄露 raw sensitive data

### 12. Traceability
验收标准：
- 能根据 transaction 或 trace_id 理解一次关键操作链路
- reviewer 能看出“谁、什么时候、做了什么、结果如何”

---

## 六、数据与持久化验收

### 13. Relational Database
验收标准：
- 使用真实 relational database
- 至少存在以下数据表：
  - `users`
  - `transactions`
  - `risk_results`
  - `audit_logs`
- 如实现 `webhook_events` 更佳

### 14. SQL / Data Workflow
验收标准：
- transaction 查询正常
- risk / audit 数据能关联查询
- schema 结构合理，字段命名清晰

---

## 七、工程化验收

### 15. Tests
最低要求应覆盖：
- idempotency
- RBAC
- masking behavior
- webhook signature verification
- risk rule decision

验收标准：
- 测试可运行
- README 中有测试说明

### 16. Documentation
验收标准：
README 至少说明：
- project purpose
- architecture overview
- setup instructions
- env vars
- API endpoints
- demo walkthrough
- compliance note

并且必须明确写出：
- 本 demo **not certified compliant**
- 它仅用于展示 **PBOC-style / PCI-oriented** 工程控制点

---

## 八、建议的手工验收步骤

### 步骤 1：启动系统
- 启动 docker compose
- 访问 health endpoint
- 确认服务已正常运行

### 步骤 2：登录不同角色
- 分别使用 `admin`、`operator`、`auditor`
- 验证权限差异

### 步骤 3：创建 payment
- 使用有效请求创建 transaction
- 记录 transaction id / trace_id

### 步骤 4：重复提交相同 `request_no`
- 确认没有重复 transaction
- 验证 idempotency 生效

### 步骤 5：触发 risk rule
- 构造高金额或 blacklist 场景
- 验证 risk decision 被记录

### 步骤 6：查看 masked data
- 确认 API response / query result 中敏感数据已 masking

### 步骤 7：发送 valid webhook
- 使用正确 signature
- 验证 transaction 状态变化

### 步骤 8：发送 invalid webhook
- 使用错误 signature
- 验证请求被拒绝并有相应记录

### 步骤 9：查看 audit logs
- 核对关键操作是否都有 audit records

---

## 九、通过标准

该 demo 可视为通过验收，如果 reviewer 能确认：

- 可以本地运行
- 具备基本 auth + RBAC
- 具备 transaction creation + state machine
- 具备 idempotency
- 具备 risk-control workflow
- 具备 masking
- 具备 audit logging
- 具备 webhook signature verification
- 具备最小可运行测试
- README 清晰说明该项目如何体现 **PBOC-style / PCI-oriented** 工程控制点

---

## 十、验收结论模板

### Pass
该 demo 已完成最小范围内的 payment-security engineering control 展示，能够体现：
- secure transaction workflow
- auditability
- traceability
- RBAC
- signed integration handling
- risk checkpoints
- sensitive data protection

### Needs Improvement
若以下任一项缺失，应判定为待补充：
- 无 idempotency
- 无 audit log
- 无 masking
- 无 webhook signature verification
- 无 RBAC
- 无清晰 README
- 将项目错误表述为正式 PCI/PBOC 合规认证

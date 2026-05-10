# Secure Payment Integration & Audit Demo — MVP Spec

## Purpose

Build a minimal but production-flavored payment integration demo that demonstrates engineering controls commonly found in **PBOC-style** and **PCI-oriented** payment environments.

This project is **not** intended to claim formal compliance or certification. Instead, it should demonstrate practical implementation of core controls such as:

- data masking
- role-based access control (RBAC)
- audit logging
- signed integration requests
- idempotent transaction handling
- secure configuration management
- risk-control checkpoints in transaction workflows

The output should be a small but runnable demo that can be started locally and easily reviewed.

---

## Primary Goal

Deliver a minimum demo that allows a reviewer to see that the system:

1. accepts a payment creation request
2. enforces idempotency
3. routes the transaction through a simple risk-control step
4. stores and returns only masked sensitive data
5. records audit logs for critical operations
6. validates signed callback/webhook requests
7. enforces RBAC for operational access

---

## Recommended Tech Stack

Codex may choose a different stack if needed, but the preferred stack is:

### Backend
- **Python + FastAPI**
- **SQLAlchemy**
- **Pydantic**
- **PostgreSQL** or **MySQL**
- **Redis** for idempotency / blacklist / rate-limiting style state where useful

### Frontend
- Minimal web UI is optional
- If implemented, prefer:
  - **React + Vite**
  - very lightweight admin-style UI

### Infra / Runtime
- **Docker Compose**
- environment-variable-driven configuration
- `.env.example`
- simple local startup instructions

### Optional
- **RabbitMQ** for asynchronous audit/event flow
- **Prometheus/Grafana** only if time allows

---

## Project Positioning

This should feel like a small internal **payment gateway sandbox** or **payment operations control demo**, not like a generic CRUD application.

The system should model realistic payment-system concerns:

- transaction state control
- secure handling of payment-related data
- traceability
- partner callback verification
- operational visibility
- controlled user access

---

## Functional Scope (MVP)

## 1. Payment Creation API

Provide an API to create a payment transaction.

### Required Fields
- `request_no`
- `merchant_id`
- `account_reference`
- `amount`
- `currency`
- `payer_name`
- `card_number` or payment identifier input
- `channel`

### Required Behavior
- create a transaction record
- immediately apply masking to sensitive fields for storage/display
- reject malformed requests
- support idempotency using `request_no`

### Notes
- full sensitive card/payment identifiers must **not** be stored in plain text in the main transaction table
- only masked representation and/or tokenized placeholder should be persisted

---

## 2. Transaction State Machine

Implement a simple but explicit transaction lifecycle.

### Required States
- `CREATED`
- `PENDING_RISK`
- `APPROVED`
- `REJECTED`
- `SETTLED`
- `FAILED`
- `REVERSED`

### Required Rules
- new payments enter `CREATED`, then go to `PENDING_RISK`
- only approved transactions may move to `SETTLED`
- rejected transactions cannot settle
- duplicate requests with the same `request_no` must not create duplicate transactions
- state transitions must be validated server-side

---

## 3. Risk-Control Workflow

Add a small rules-based risk-control step.

### Minimum Rules
At least 3 rules from the following:
- amount above threshold -> `REVIEW` or `REJECT`
- blacklisted account -> `REJECT`
- too many requests within short window -> `REJECT` or `REVIEW`
- night-time transaction -> add risk flag
- unsupported merchant/channel combination -> `REJECT`

### Required Output
The system should produce:
- risk decision
- triggered rule(s)
- timestamp
- operator/system source

### Required Behavior
- persist risk results
- link risk decision to transaction
- expose risk result in transaction detail view or API response

---

## 4. Sensitive Data Handling

This is a core requirement.

### Must Implement
- mask payment identifiers in API responses
- mask sensitive fields in logs
- avoid storing raw card/account sensitive fields directly in ordinary records
- secrets/keys must come from environment variables, not hardcoded source

### Example
- input: `6222021234567890`
- stored/displayed: `************7890`

---

## 5. RBAC (Role-Based Access Control)

Implement at least 3 roles:

- `admin`
- `operator`
- `auditor`

### Minimum Access Model
- `admin`
  - can manage configuration
  - can view transaction details
  - can view audit logs
- `operator`
  - can create/query transactions
  - can view non-sensitive transaction data
  - cannot change security configuration
- `auditor`
  - can view audit records and transaction history
  - cannot create transactions
  - cannot alter runtime configuration

### Authentication
Simple JWT-based login is acceptable for MVP.

---

## 6. Audit Logging

Every critical operation must generate an audit log record.

### Must Audit
- login
- payment creation
- risk decision
- settlement request
- reversal request
- role-protected configuration changes
- webhook callback handling
- failed authorization attempts (at least optionally)

### Required Audit Fields
- timestamp
- actor
- actor role
- action
- target resource
- result
- trace_id / request_id
- masked metadata snapshot where useful

### Requirements
- audit logs should be queryable
- audit entries should not expose raw sensitive fields
- audit trail should help reconstruct the operational flow

---

## 7. Signed Webhook / Callback Verification

Simulate third-party payment provider callback security.

### Required
Expose an endpoint that receives a callback/webhook, for example:
- payment settlement result
- transaction confirmation
- reversal confirmation

### Must Implement
- HMAC signature verification
- timestamp validation
- nonce or replay protection strategy
- rejection of invalid signatures

### Required Result
- valid webhook updates transaction state
- invalid webhook is rejected and logged

---

## 8. SQL / Data Operations

The project must have real relational persistence.

### Required
- relational database schema
- migration setup if practical
- transaction table
- risk result table
- audit log table
- user / role table
- optional webhook event table

### Nice to Have
- indexes for request lookup / transaction state / audit query
- simple seed data

---

## 9. Ops / Dev Environment

Provide a minimal local operational experience.

### Must Include
- `docker-compose.yml`
- `.env.example`
- startup instructions
- API docs (OpenAPI/Swagger if using FastAPI)
- local test steps

### Required Operational Controls
- separate app config from secrets
- clear development vs local demo config
- basic health endpoint

---

## 10. Testing

Testing does not need to be exhaustive, but should cover critical controls.

### Minimum Automated Tests
- idempotency test
- RBAC access control test
- masking behavior test
- webhook signature validation test
- risk-rule decision test

### Minimum Manual Validation Checklist
- create payment
- duplicate same `request_no`
- trigger rejection rule
- query masked transaction
- login as different roles
- send valid webhook
- send invalid webhook
- inspect audit logs

---

## API Suggestions

The exact API shape may vary, but a useful minimum is:

### Auth
- `POST /auth/login`

### Payments
- `POST /payments`
- `GET /payments/{id}`
- `GET /payments`
- `POST /payments/{id}/settle`
- `POST /payments/{id}/reverse`

### Risk
- `GET /payments/{id}/risk`

### Audit
- `GET /audit-logs`

### Webhook
- `POST /webhooks/provider/payment-status`

### Health
- `GET /health`

---

## Recommended Data Model

## Table: users
- id
- username
- password_hash
- role
- created_at

## Table: transactions
- id
- request_no
- merchant_id
- account_reference_masked
- payment_token (optional simulated token)
- amount
- currency
- channel
- state
- trace_id
- created_at
- updated_at

## Table: risk_results
- id
- transaction_id
- decision
- triggered_rules
- details_json
- created_at

## Table: audit_logs
- id
- actor
- actor_role
- action
- resource_type
- resource_id
- result
- trace_id
- metadata_json
- created_at

## Table: webhook_events (optional but recommended)
- id
- source
- event_type
- signature_valid
- payload_hash
- replay_key
- created_at

---

## Required Engineering Standards

Codex should prioritize:
- clear structure
- readability
- small but complete implementation
- security-aware defaults
- good naming
- typed request/response models
- meaningful logs
- minimal but real tests
- concise README

This demo should not over-engineer. It should be:
- small
- runnable
- reviewable
- explainable in an interview or portfolio walkthrough

---

## Deliverables

The MVP should produce:

1. runnable backend service
2. relational database integration
3. authentication + RBAC
4. payment creation + idempotency
5. risk-control workflow
6. audit logging
7. signed webhook verification
8. tests for critical paths
9. Docker Compose setup
10. README with architecture, startup, test, and demo walkthrough

---

## README Requirements

The generated README must include:

- project purpose
- architecture overview
- compliance note:
  - state clearly that this is **not certified compliant**
  - it demonstrates engineering controls commonly expected in **PBOC-style** or **PCI-oriented** payment systems
- setup instructions
- env vars
- default seeded users/roles
- API endpoints
- manual demo walkthrough
- test instructions

---

## Compliance Positioning Language

Use wording similar to:

> This demo is designed to reflect engineering controls commonly required in payment environments operating under PBOC-style or PCI-oriented security and compliance expectations. It is not intended to represent formal certification or audited compliance.

Do **not** claim:
- PCI compliant
- PBOC certified
- audit passed
- production certified

---

## Suggested Milestones

### Milestone 1
- project skeleton
- auth
- RBAC
- DB schema
- payment create/query

### Milestone 2
- risk workflow
- audit logging
- idempotency

### Milestone 3
- webhook signature verification
- tests
- Docker Compose
- README polish

---

## Acceptance Definition

The MVP is acceptable if a reviewer can:

- run it locally
- log in as different roles
- create a payment
- verify masked data handling
- observe idempotency behavior
- see risk-control decisions
- inspect audit logs
- send a signed callback
- observe valid vs invalid webhook handling
- understand from the README how this reflects payment-security engineering controls

---

## Final Instruction to Codex

Build the smallest complete demo that satisfies the above. Favor clarity and correctness over feature count. Do not spend time on visual polish unless a minimal admin page is very easy to provide. Backend correctness, security-minded behavior, auditability, and explainability are the priority.

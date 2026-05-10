# Payment Compliance MVP Acceptance Flow

## Purpose

This document defines the local acceptance flow for the Secure Payment Integration and Audit Demo.

The goal is to verify the smallest useful MVP through Swagger/OpenAPI first, without requiring a custom frontend page.

This demo is not certified compliant. It only demonstrates engineering controls commonly expected in PBOC-style or PCI-oriented payment systems.

## Acceptance Surface

Primary acceptance UI:

```text
http://localhost:8000/docs
```

Supporting endpoints:

```text
http://localhost:8000/health
http://localhost:8000/openapi.json
```

Expected local runtime:

```text
FastAPI app container
PostgreSQL container
Swagger/OpenAPI documentation
```

## Seeded Users

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | `admin` |
| `operator` | `operator123` | `operator` |
| `auditor` | `auditor123` | `auditor` |

## Batch Acceptance Plan

### Batch 1: Skeleton, Auth, RBAC, Database

Scope:

- FastAPI project skeleton
- Docker Compose local runtime
- PostgreSQL connection
- `users` table
- seeded users
- JWT login
- current user endpoint
- reusable RBAC dependency
- health endpoint
- Swagger page

Acceptance criteria:

- `docker compose up --build` starts the app and database.
- `GET /health` returns `{"status":"ok"}`.
- `POST /auth/login` works for `admin`, `operator`, and `auditor`.
- Login returns a bearer token.
- `GET /auth/me` returns the authenticated username and role.
- `/docs` is accessible.
- The repository includes `.env.example`.
- The repository includes local startup instructions.

Swagger flow:

1. Open `/docs`.
2. Call `GET /health`.
3. Call `POST /auth/login` with `admin`.
4. Click `Authorize` and paste the bearer token.
5. Call `GET /auth/me`.
6. Repeat login checks for `operator` and `auditor`.

### Batch 2: Payment Creation, Idempotency, Masking

Scope:

- `transactions` table
- `POST /payments`
- `GET /payments`
- `GET /payments/{id}`
- `request_no` uniqueness
- idempotent duplicate handling
- sensitive payment identifier masking
- basic transaction states
- RBAC on payment creation and query

Acceptance criteria:

- `operator` can create a payment transaction.
- `admin` can query transaction details.
- `auditor` cannot create a payment transaction.
- The payment create request includes `request_no`, `merchant_id`, `account_reference`, `amount`, `currency`, `payer_name`, payment identifier input, and `channel`.
- API responses show only masked sensitive payment identifiers.
- The main transaction record does not store raw card number or raw payment identifier values.
- Submitting the same `request_no` twice does not create a second transaction.
- Duplicate submission returns the existing transaction or clearly marks the response as idempotent.
- Malformed requests return a 4xx response.

Swagger flow:

1. Login as `operator`.
2. Authorize with the operator token.
3. Call `POST /payments` with a valid payment payload.
4. Save the returned transaction id and `request_no`.
5. Call `POST /payments` again with the same `request_no`.
6. Verify that only one transaction exists for that `request_no`.
7. Call `GET /payments/{id}`.
8. Verify that sensitive values are masked.
9. Login as `auditor`.
10. Try `POST /payments` and verify access is denied.

### Batch 3: Risk Control and Audit Logs

Scope:

- `risk_results` table
- `audit_logs` table
- automatic risk evaluation during payment creation
- at least three risk rules
- risk result linked to transaction
- `GET /payments/{id}/risk`
- `GET /audit-logs`
- masked audit metadata
- RBAC on audit log access

Recommended minimum risk rules:

- amount over threshold returns `REVIEW` or `REJECT`
- blacklisted account returns `REJECT`
- unsupported merchant and channel combination returns `REJECT`

Acceptance criteria:

- Creating a payment automatically produces a risk decision.
- Risk results include decision, triggered rules, timestamp, and source.
- Risk results are persisted and linked to the transaction.
- `GET /payments/{id}/risk` returns the risk result.
- Login, payment creation, and risk decision generate audit log records.
- Audit logs do not expose raw sensitive payment data.
- `admin` and `auditor` can query audit logs.
- `operator` cannot query audit logs unless intentionally allowed by the access model.

Swagger flow:

1. Login as `operator`.
2. Create a normal payment.
3. Create a payment that triggers a risk rule.
4. Call `GET /payments/{id}/risk` for both transactions.
5. Login as `admin` or `auditor`.
6. Call `GET /audit-logs`.
7. Verify that login, payment creation, and risk decision entries exist.
8. Verify that audit metadata is masked.

### Batch 4: Webhook HMAC, State Flow, Tests, README

Scope:

- signed webhook endpoint
- HMAC signature verification
- timestamp validation
- nonce or replay protection
- webhook event persistence or equivalent replay tracking
- valid webhook updates transaction state
- invalid webhook is rejected and logged
- settlement and reversal endpoints
- final core tests
- README demo walkthrough

Expected endpoints:

- `POST /webhooks/provider/payment-status`
- `POST /payments/{id}/settle`
- `POST /payments/{id}/reverse`
- optional local-only `POST /dev/webhook-signature`

Acceptance criteria:

- Valid webhook signature is accepted.
- Invalid signature is rejected.
- Expired timestamp is rejected.
- Reused nonce or replay key is rejected.
- Valid webhook can update transaction state to `SETTLED`, `FAILED`, or `REVERSED`, according to payload and state rules.
- Invalid webhook attempts are logged.
- Only authorized roles can trigger settlement or reversal.
- Tests cover login/RBAC, idempotency, masking, risk rules, webhook signature validation, and audit logging.
- README explains setup, seeded users, API flow, and the compliance positioning note.

Swagger flow:

1. Login as `operator` or `admin`.
2. Create a payment transaction.
3. Generate webhook headers and signature.
4. Call `POST /webhooks/provider/payment-status` with a valid signature.
5. Query the transaction and verify state change.
6. Repeat the webhook request with a modified signature and verify rejection.
7. Repeat the webhook request with the same nonce and verify replay rejection.
8. Query audit logs and verify webhook handling entries.

## Final MVP Acceptance Checklist

The MVP is accepted when a reviewer can verify all of the following:

- The system runs locally.
- Swagger is available at `/docs`.
- Different roles can log in.
- RBAC restricts protected operations.
- A payment transaction can be created.
- Duplicate `request_no` requests are idempotent.
- Sensitive payment information is masked in API responses.
- Raw sensitive payment identifiers are not stored in the main transaction record.
- Risk control rules run during the payment flow.
- Risk results are queryable.
- Audit logs are generated for critical operations.
- Audit logs do not expose raw sensitive payment data.
- HMAC-signed webhook requests are validated.
- Invalid webhook requests are rejected and logged.
- Core tests can run locally.
- README explains the local demo flow.
- The project does not claim formal PCI or PBOC certification.

## Local Commands

Start the stack:

```bash
docker compose up --build
```

Run tests:

```bash
python3 -m pytest -q
```

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

## Pass or Fail Decision

Pass:

- All seven MVP controls are visible through Swagger or documented local commands.
- Core automated tests pass.
- The README provides enough context for a reviewer to repeat the demo.

Fail:

- Any of the seven MVP controls is missing.
- Raw sensitive payment data is exposed in responses, audit logs, or main transaction records.
- RBAC can be bypassed.
- Duplicate `request_no` values create duplicate transactions.
- Invalid webhook signatures are accepted.
- The project claims formal compliance or certification.


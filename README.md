# Secure Payment Integration & Audit Demo

This repository contains a local MVP for a payment-security engineering demo. The current build provides the runnable backend skeleton, PostgreSQL integration, JWT login, seeded roles, RBAC dependencies, Swagger, payment creation, request-number idempotency, and sensitive payment identifier masking.

This demo is not certified compliant. It demonstrates engineering controls commonly expected in PBOC-style or PCI-oriented payment systems.

## Local Startup

1. Create the local environment file:

```bash
cp .env.example .env
```

2. Start the stack:

```bash
docker compose up --build
```

3. Open:

```text
http://localhost:8000/docs
http://localhost:8000/health
```

## Seeded Users

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | `admin` |
| `operator` | `operator123` | `operator` |
| `auditor` | `auditor123` | `auditor` |

## Batch 1 Acceptance

- `docker compose up --build` starts the app and PostgreSQL.
- `GET /health` returns `ok`.
- `POST /auth/login` returns a bearer token for each seeded user.
- `GET /auth/me` returns the authenticated user's username and role.
- Swagger is available at `/docs`.

## Batch 2 Acceptance

- `operator` and `admin` can create payment transactions with `POST /payments`.
- `auditor` can query transactions but cannot create them.
- Reusing the same `request_no` returns the existing transaction with `idempotent_replay=true`.
- API responses expose masked payment identifiers only.
- The main transaction record stores masked identifiers, not raw card numbers or account references.

Brief reviewer flow:

1. Open `http://localhost:8000/docs`.
2. Call `POST /auth/login` with `operator` / `operator123`.
3. Click `Authorize` and paste the returned bearer token.
4. Call `POST /payments` with a payment payload that includes `request_no`, `merchant_id`, `account_reference`, `amount`, `currency`, `payer_name`, `card_number`, and `channel`.
5. Confirm the response returns a risk-derived `state` such as `APPROVED` and masked fields such as `payment_identifier_masked=************7890`.
6. Call `POST /payments` again with the same `request_no`.
7. Confirm the second response returns the same payment `id` and `idempotent_replay=true`.
8. Call `GET /payments/{id}` and confirm no raw card number or raw account reference is exposed.
9. Log in as `auditor` / `auditor123`.
10. Confirm `GET /payments/{id}` succeeds, but `POST /payments` returns `403`.

## Batch 3 Acceptance

- Creating a payment automatically generates a risk decision.
- At least three rules are available: high amount review, blacklisted account rejection, and unsupported merchant/channel rejection.
- `GET /payments/{id}/risk` returns the persisted risk result.
- Login, payment creation, and risk decision create audit records.
- `GET /audit-logs` is available to `admin` and `auditor`, but not `operator`.
- Audit metadata uses masked sensitive values only.

Brief reviewer flow:

1. Open `http://localhost:8000/docs`.
2. Log in as `operator` / `operator123` and authorize.
3. Call `POST /payments` with a normal amount and confirm the response state is `APPROVED`.
4. Call `GET /payments/{id}/risk` and confirm `decision=APPROVE`.
5. Create another payment with `amount=15000.00`.
6. Call `GET /payments/{id}/risk` and confirm `decision=REVIEW` with `AMOUNT_ABOVE_THRESHOLD`.
7. Create another payment with `account_reference=ACC-BLACKLISTED-001`.
8. Call `GET /payments/{id}/risk` and confirm `decision=REJECT` with `BLACKLISTED_ACCOUNT`.
9. Log in as `admin` / `admin123`.
10. Call `GET /audit-logs` and confirm `LOGIN`, `PAYMENT_CREATE`, and `RISK_DECISION` records exist without raw card numbers or raw account references.

## Tests

```bash
python3 -m pytest -q
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

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

## Tests

```bash
python3 -m pytest -q
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

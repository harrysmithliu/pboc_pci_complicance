# Secure Payment Integration & Audit Demo

This repository contains a local MVP for a payment-security engineering demo. Batch 1 provides the runnable backend skeleton, PostgreSQL integration, JWT login, seeded roles, RBAC dependencies, and Swagger.

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

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

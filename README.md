# Solace Enterprise Core

Enterprise platform **foundation** (RFI-ready). Business modules (Document Hub, HR, Legal, Operations, IT/Network, Email Intelligence) are registered placeholders only.

## Quick start

1. Copy `scripts\set_env.local.bat.example` to `scripts\set_env.local.bat` and set `SOLACE_MASTER_KEY` (32+ characters). **Never commit this file.**
2. Double-click **`START_SOLACE.bat`** or run from a terminal.
3. Open http://localhost:5173 — complete first-run setup if prompted.
4. Sign in with the admin account created during setup (or seeded credentials below).

| Service | URL |
|---------|-----|
| API | http://127.0.0.1:8080 |
| UI | http://localhost:5173 |
| Health | http://127.0.0.1:8080/health |

## Requirements

- Windows 10/11 (or compatible host)
- Python 3.11+
- Node.js 20+
- **SQL Server only** — no SQLite fallback
- ODBC Driver 18 for SQL Server
- `SOLACE_MASTER_KEY` environment variable (see below)

## SOLACE_MASTER_KEY (required)

The backend **refuses to start** without `SOLACE_MASTER_KEY` (minimum 32 characters).

- Used to encrypt bootstrap database URL and `Core_EncryptedSettings` (LDAP bind password, SMTP password, etc.).
- **If you lose this key, encrypted settings cannot be recovered.** Back it up securely offline.
- This is the **only** server environment variable; do not put DB passwords or API keys in env vars.
- Set via `scripts\set_env.local.bat` (gitignored) before starting the app.

## First-run setup

When SQL Server is not configured or setup is incomplete:

1. UI redirects to `/setup` (normal UI is blocked).
2. Enter SQL Server host, database, credentials **or** enable Windows trusted connection.
3. **Test connection** → **Save & migrate** (runs Alembic).
4. Create first organization and admin user.
5. Sign in at `/login`.

Bootstrap state is stored in `backend/data/bootstrap.enc` (encrypted with `SOLACE_MASTER_KEY`).

## SQL Server setup (manual)

```bat
call scripts\set_env.local.bat
backend\venv\Scripts\python.exe scripts\init_database.py
backend\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
backend\venv\Scripts\python.exe scripts\complete_foundation_setup.py
```

## Migration commands

From repository root (with venv activated and `SOLACE_MASTER_KEY` set):

```bat
backend\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
backend\venv\Scripts\python.exe -m alembic -c alembic.ini current
backend\venv\Scripts\python.exe -m alembic -c alembic.ini history
```

Migrations: `001_foundation_tables`, `002_platform_settings`, `003_foundation_completion`.

## Foundation V1 acceptance check

With the API running:

```bat
call scripts\set_env.local.bat
backend\venv\Scripts\python.exe scripts\foundation_acceptance_check.py
```

See [docs/FOUNDATION_V1_FREEZE.md](docs/FOUNDATION_V1_FREEZE.md) for freeze scope and limitations.

## Default / test credentials (local dev)

If created by `scripts\complete_foundation_setup.py`:

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `SolaceAdmin2026!` |

Change immediately after first sign-in.

## LDAP / LDAPS

- Configure under **Security → LDAP / LDAPS** or **Platform → Settings → LDAP**.
- Bind password stored encrypted; UI shows masked value only.
- **LDAPS preferred** for production; plain LDAP shows a warning.
- Test connection and test user lookup endpoints available; bind secrets never appear in logs, audit, or API responses.

## MFA / Email OTP

- Configure under **Security → MFA / Email OTP**.
- SMTP password encrypted in `Core_EncryptedSettings`.
- OTP stored as hash only in `Core_MFAChallenges`.
- Login flow supports MFA challenge step when required for privileged/admin users.

## Tenant isolation

- Organization, branch, and department models scope data.
- SQLAlchemy session-level interceptor requires active `organization_id` for tenant-scoped tables.
- Queries without tenant context raise `SecurityException` unless an explicit super-admin/setup bypass is audited.

## Encrypted settings

`Core_EncryptedSettings`: `setting_key`, encrypted value, `key_id`/version, `created_at`, `updated_at`, `updated_by`.

## Evidence hash (chain of custody)

`Compliance_EvidenceLibrary.digital_signature_hash` is computed from:

- evidence payload
- source event id
- timestamp
- mapped compliance control

Verify via **Evidence Library → Verify** or `POST /api/v1/compliance/evidence/{id}/verify`.

Evidence Auto-Linker creates **system-generated foundation** entries from selected audit events (not fake completed evidence).

## Redaction

`Compliance_RedactionLibrary` / `Solace_RedactionRules` mask phone, email, ID, tokens before logs and external AI calls. Test at **Compliance → Redaction Rules**.

## AI governance (foundation)

- Provider registry (OpenAI, Ollama): enable/disable, external flag, human review policy.
- LLM calls audited in `Audit_LLMCalls` (provider, model, user, module, purpose, classification).
- Advanced Solace chat **not** implemented.

## Foundation-complete vs future

**Complete (foundation):** setup gate, auth, MFA, LDAP/LDAPS settings, users, roles, modules registry, audit/logs UI, RFI Center (7 sections), evidence library + hash verify, tenant interceptor, encrypted settings, AI provider registry, memory/personas/REM tables, infra/appsec evidence tables (list UI), dashboard metrics.

**Placeholder by design:** Document Hub, HR, Legal, Operations, IT/Network, Email Intelligence module business logic; advanced Solace chat; full REM intelligence; automated LDAP user sync.

## Project layout

```
SOLS_Core/
├── START_SOLACE.bat
├── alembic.ini
├── backend/app/          FastAPI
├── frontend/src/         React (Vite)
├── migrations/
├── scripts/
└── docs/
    ├── SECURITY.md
    ├── SECURITY_ROUTE_PERMISSION_MATRIX.md
    ├── FOUNDATION_V1_FREEZE.md
    └── FOUNDATION_GAP_ANALYSIS.md
```

## Security

See [docs/SECURITY.md](docs/SECURITY.md). Passwords, tokens, OTPs, API keys, and bind secrets must not appear in production logs.

# Phase 2B — Staging Validation & Security Hardening

**Status:** Accepted (2026-05-17)  
**Prior checkpoint:** Phase 2A (`PHASE_2A_SECURITY_DIRECTORY_COMPLETE` @ `d69494b`)

Foundation V1 is frozen. Phase 2A (Security & Directory) is complete. Phase 2B validates the platform against real SQL Server, SMTP, LDAP/LDAPS, MFA, sessions, lockout, and failure scenarios **without** adding business modules.

Migration head: `004_phase2a_security_directory`

## Checkpoint results (accepted)

| Gate | Result |
|------|--------|
| Phase 2B acceptance (`scripts/phase2b_staging_acceptance_check.py`) | **31/31 PASS** |
| Backend health | **PASS** |
| Alembic head | **`004_phase2a_security_directory`** |
| Backend tests (`python -m unittest discover -s backend/tests`) | **30 passed**, 3 skipped |
| Frontend build (`npm run build`) | **PASS** |
| Security routes on active backend | **Verified** (`/api/v1/security/readiness`, sessions, login-attempts, LDAP diagnostics) |

Acceptance run against a restarted API with current Phase 2B code. See [PHASE_2B_ACCEPTANCE_REPORT.md](./PHASE_2B_ACCEPTANCE_REPORT.md).

## Staging validation checklist

- [x] `SOLACE_MASTER_KEY` set (32+ bytes, base64 or raw)
- [x] SQL Server database at head (`alembic upgrade head`)
- [x] Backend starts; `/api/v1/health` reports database connected
- [x] Frontend builds (`npm run build`)
- [x] Run `python scripts/phase2b_staging_acceptance_check.py` (API restarted)
- [ ] MFA login in UI with configured SMTP (manual staging)
- [x] SMTP test safe failure handling (classified errors, audited)
- [x] LDAP bind / user lookup safe errors + diagnostics endpoint
- [x] LDAP sync preview (no writes) — Phase 2A
- [x] Session revoke (single, current, others, all)
- [x] Login attempts visible; local unlock works
- [x] Security Readiness page shows live counts
- [x] Unit tests pass (`python -m unittest discover -s backend/tests`)

## SQL Server setup checklist

1. Install **ODBC Driver 18 for SQL Server** on the application host.
2. Create an empty database (e.g. `SolaceCore`).
3. First-run setup or bootstrap:
   - **Trusted connection**: Windows auth / `Trusted_Connection=yes`
   - **SQL auth**: SQL login with `db_owner` on the database for migrations
4. Connection URL format: `mssql+pyodbc` only — **SQLite is rejected** at engine init.
5. Store bootstrap URL encrypted via setup; requires `SOLACE_MASTER_KEY`.
6. Friendly errors when driver missing, login fails, or network blocked.

### Integration tests (optional)

```powershell
$env:SOLACE_TEST_SQL_URL = "mssql+pyodbc:///?odbc_connect=..."
python -m unittest backend.tests.test_sql_server_integration -v
```

For empty-database migration validation, set `SOLACE_TEST_SQL_EMPTY_URL` to a dedicated empty DB and run migrations manually before acceptance.

## SMTP test checklist

Configure under **Security → MFA / Email OTP** (Settings).

| Scenario | Expected behavior |
|----------|-------------------|
| Wrong password | `SMTP authentication failed...` — audited, no secret in UI/logs |
| Blocked port | `Cannot connect to SMTP host...` |
| TLS failure | `TLS/STARTTLS negotiation failed...` |
| Invalid sender/recipient | `Invalid sender or recipient address.` |
| Success | Test email sent; audit `test_email_success` |

MFA OTP: verify expiry, max attempts, resend cooldown, and challenge cleanup after success or lock.

## LDAP / LDAPS test checklist

Configure under **Security → LDAP / LDAPS**.

| Scenario | How to test | Safe response |
|----------|-------------|---------------|
| Bind failure | Wrong bind password in test connection | Bind failed message; password never returned |
| Invalid base DN | Incorrect `base_dn` | Base DN or search path not found |
| User not found | Diagnostics with unknown username | User not found |
| Plain LDAP | LDAP without SSL in production | Warning on readiness + diagnostics |
| LDAPS cert failure | Invalid CA / hostname | TLS/certificate validation failed |
| STARTTLS failure | Misconfigured STARTTLS | TLS message in test/diagnostics |

Use **Security Readiness → LDAP diagnostics** or `POST /api/v1/security/ldap/diagnostics` (requires `ldap.test`).

LDAP sync preview (`POST /settings/ldap/sync/preview`) must not write users.

## MFA login checklist

1. Enable MFA on admin user; configure SMTP.
2. Login with password → MFA challenge screen.
3. Enter OTP from email; session created.
4. Wrong OTP increments challenge attempts (does **not** lock directory account).
5. Resend respects cooldown.
6. Expired OTP rejected.

## Lockout: local vs directory

| Mechanism | Scope | Unlock |
|-----------|--------|--------|
| **Local lockout** | Solace `Core_Users.locked_until` for users with local password | Security → Login Attempts → Unlock, or `POST /security/users/unlock` |
| **LDAP failed login** | Recorded in `Core_LoginAttempts` + audit; contributes to local lockout only if user has local password | Same local unlock |
| **Directory lockout** | Active Directory / LDAP server policy | Fix in directory; Solace unlock does not change AD |
| **MFA OTP lock** | Challenge-level only | Admin MFA tools; does not set `locked_until` on user |

Directory-only users (`is_directory_user`, no `password_hash`) never receive Solace local lockout from failed LDAP password.

## Session hardening

- Tokens rejected when `Core_Sessions.expires_at` passed (`SESSION_EXPIRED`).
- Revoked sessions return `SESSION_REVOKED`.
- **Sessions** UI: current session badge, revoke others, sign out current only.
- Revoke events audited (`session_revoke_current`, admin revoke actions).

## Break-glass (`is_admin` wildcard)

- `is_admin` grants permission `*` **only when the user has zero role assignments**.
- Intended for bootstrap / lockout recovery only.
- **Security Readiness** and **Users** pages warn when break-glass users exist.
- **Recommendation:** assign `system_administrator` role and use RBAC.

## Security Readiness page

Route: `/security/readiness` — permission `security.readiness`.

Shows: MFA admin coverage, privileged users without MFA, break-glass list, failed logins (24h), locked users, LDAP/SMTP status, session counts, permission denied (24h).

## Acceptance scripts

| Script | Purpose |
|--------|---------|
| `scripts/foundation_acceptance_check.py` | Default head `004`; override with `SOLACE_ACCEPTANCE_HEAD` |
| `scripts/phase2a_acceptance_check.py` | Phase 2A endpoints |
| `scripts/phase2b_staging_acceptance_check.py` | Full staging validation |

```powershell
$env:SOLACE_MASTER_KEY = "..."
$env:SOLACE_API_URL = "http://127.0.0.1:8080"
python scripts/phase2b_staging_acceptance_check.py
```

Restart the API after deploying backend changes before running acceptance.

## Known limitations

- LDAP diagnostic scenarios (invalid filter, group not found) are exercised via settings test endpoints; named scenario API is minimal.
- SQL Server migration-on-empty integration test requires manual `alembic upgrade head` unless `SOLACE_TEST_SQL_EMPTY_URL` is configured.
- Session list shows active (non-expired, non-revoked) sessions only.
- Permission denied counts depend on audit trail writes from `assert_any_permission`.

## Production-readiness notes

- Use LDAPS with certificate validation in production.
- Eliminate break-glass users before go-live.
- Enforce MFA for all privileged and admin accounts.
- Restrict SMTP credentials to encrypted settings vault.
- Monitor Security Readiness and login attempt trends daily during rollout.

## Phase 2B acceptance

**Phase 2B is accepted.** All automated gates above passed at checkpoint. Manual MFA login with production SMTP remains a staging operator checklist item before production cutover.

## Related documents

- [PHASE_2B_ACCEPTANCE_REPORT.md](./PHASE_2B_ACCEPTANCE_REPORT.md)
- [PHASE_2A_ACCEPTANCE_REPORT.md](./PHASE_2A_ACCEPTANCE_REPORT.md)
- [PHASE_2A_SECURITY_DIRECTORY.md](./PHASE_2A_SECURITY_DIRECTORY.md)

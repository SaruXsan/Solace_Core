# Foundation Gap Analysis (vs Word Plan)

Date: 2026-05-17

## Implemented
- SOLACE_MASTER_KEY startup enforcement
- SQL Server + Alembic migrations (001, 002)
- Bootstrap encrypted DB connection
- Local auth, bcrypt, lockout, sessions, JWT
- Core platform tables (org, branch, dept, users, roles, permissions, modules)
- Settings UI tabs (system, DB, security, LDAP, MFA, AI, redaction)
- LDAP settings save/test (encrypted bind password, masked)
- MFA settings, challenges create/verify/resend, OTP hashed
- Users CRUD (partial)
- Roles list/create, permissions list, base roles seed
- Modules registry (placeholders blocked from enable)
- RFI Center (7 sections), Evidence library + hash + auto-linker skeleton
- Audit tables + basic audit writers
- Tenant context + session interceptor skeleton
- Infra/AppSec tables (schema only)

## Partially implemented
- First-run setup (UI exists; no global gate blocking main app)
- Core_EncryptedSettings (missing `updated_by`)
- Logout (client-only clear; no server revoke endpoint)
- LDAP login at sign-in (settings only)
- Role edit UI
- Permission enforcement on endpoints (admin-only, not permission codes)
- Tenant interceptor (exists; needs hardening)
- Dashboard (static cards)
- Sidebar (subset of plan routes)
- Compliance shells (RFI + evidence only; no control map/incidents UI)
- Memory/personas (tables only)
- AI governance (provider toggle only)
- Trusted SQL connection option

## Missing (this increment targets)
- Setup gate + setup-complete middleware
- Logout + session revoke API
- LDAP authentication on login
- Permission-based route protection
- Logs UI pages
- Dashboard real metrics API
- Organizations/branches/departments UI
- Evidence hash verify endpoint
- Redaction test endpoint
- Role edit API/UI
- Expanded sidebar routes + foundation list pages
- README completion

## Placeholder by design (not built)
- Business modules: Document Hub, Operations, HR, Legal, IT/Network, Email Intelligence
- Advanced Solace chat / REM intelligence
- Full LDAP user sync
- Production ISO content

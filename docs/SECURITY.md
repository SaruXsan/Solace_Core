# Security Design — Solace Enterprise Core Foundation

## Master key

`SOLACE_MASTER_KEY` is the only server environment variable. It derives the Fernet key used to encrypt:

- Bootstrap database connection (`backend/data/bootstrap.enc`)
- `Core_EncryptedSettings` values (LDAP bind password, future API keys)

The application exits at startup if the key is missing or shorter than 32 characters.

## Authentication

- **Local:** bcrypt password hashes in `Core_Users`
- **Lockout:** 5 failed attempts → 5-minute lock (`locked_until`)
- **Sessions:** JWT + `Core_Sessions` with JTI revocation support
- **LDAP/LDAPS:** `Auth_DirectorySettings` with encrypted bind password; test connection / user lookup endpoints; plain LDAP warns for production
- **MFA:** `Core_MFAChallenges` — OTP stored as hash only; never logged

## Tenant isolation

`TenantScopedMixin` models require `organization_id` in context.

`Session.do_orm_execute` and `before_flush` listeners raise `SecurityException` when tenant-scoped operations run without an active organization (unless audited system bypass).

## Audit

Events written to `Audit_Trail`, `Audit_LoginEvents`, `Audit_MFAEvents`, `Audit_AdminActions`, `Audit_ConfigChanges`, etc. Detail JSON strips secret field names before persistence.

## Evidence chain of custody

`Compliance_EvidenceLibrary.digital_signature_hash` = SHA-256 of canonical JSON (payload + source event + control + timestamp).

Evidence Auto-Linker skeleton job creates signed placeholder records for pipeline verification.

## AI governance (foundation tables)

- `Solace_AIProviderRegistry`, `Solace_AIDataHandlingPolicy`
- Classifications: PUBLIC → SECRET with `external_provider_allowed` flags
- `Solace_LLMCallLog` / `Audit_LLMCalls` for future call auditing

Restricted/Secret data must not reach external providers unless policy explicitly allows.

## Redaction

`Compliance_RedactionLibrary` + built-in patterns mask phone, SSN-like, email, API tokens before logs.

## Rule

**Security filtering happens before AI reasoning.** The model never decides access scope.

# Enterprise Scope — Master Architecture

**Status:** Architecture authority (pre-implementation alignment)  
**Applies to:** Solace Enterprise Core foundation and all future modules  
**Related:** [PHASE_2C_ENTERPRISE_SCOPE_ISOLATION.md](./PHASE_2C_ENTERPRISE_SCOPE_ISOLATION.md)

---

## Design principle

The enterprise model is **not** separation-only.

The correct model is:

> **Separation by default. Consolidation by explicit authority.**

| Mode | Question answered | Default |
|------|-------------------|---------|
| **Operational isolation** | What can I **operate on**? | Yes — all users |
| **Executive consolidation** | What can I **report across**? | No — granted explicitly |

These are **not** the same capability. A user may operate in one company while being authorized to consolidate KPIs across several companies. A user may manage users locally without any consolidation rights. Consolidation never replaces operational scope; it adds a second, audited lane.

---

## Enterprise hierarchy

```
Holding / Enterprise Group
  └── Country / Jurisdiction          (Core_Countries)
        └── Company / Legal Entity    (Core_Organizations — table name retained)
              └── Branch / Site         (Core_Branches)
                    └── Department / Business Unit (Core_Departments)
```

| Level | Role in architecture |
|-------|----------------------|
| **Country / jurisdiction** | Legal, regulatory, language, currency, timezone context |
| **Company / legal entity** | **Primary tenant boundary** for operational data |
| **Branch / site** | Operational / location boundary |
| **Department / business unit** | Functional boundary |

**Compatibility rule:** `Core_Organizations` means **Companies / Legal Entities** in product language. Do not rename the table unless a migration strategy explicitly requires it.

Country alone does **not** satisfy tenant isolation. Company (legal entity) remains the primary filter for operational data.

---

## Operational Isolation vs Executive Consolidation

### Why two lanes exist

Operational work (users, roles, settings, documents, cases, sales, HR records, audits, AI assistance in daily work) must stay inside assigned boundaries so Company A never bleeds into Company B by accident.

Executive and group functions (regional KPIs, holding-wide risk, cross-company compliance, group legal summaries) require **read/report intelligence** across boundaries — but only when policy, classification, and audit allow it.

Mixing these into a single “scope” without a mode causes either over-exposure (executives see too much by default) or under-service (executives cannot get legitimate group reports).

### Lane 1 — Operational Isolation Lane

**Who:** Normal users, local admins, department users, branch managers, company staff, module operators.

**Purpose:** Day-to-day work inside assigned enterprise boundaries.

**Rules:**

1. **Active scope** controls what the user can see and operate on (country → company → branch → department).
2. **Company / legal entity** is the primary tenant boundary for queries and writes.
3. **Branch** and **department** narrow access further when assigned.
4. The following are separated by **active operational scope** and RBAC:
   - Users and role assignments
   - Platform settings (where scoped)
   - Documents and file metadata (future Document Hub)
   - Audit and compliance records
   - Module business data (sales, legal, HR, operations, etc.)
   - AI provider calls and prompt context
   - Solace memories used in operational chat
5. **AI / Solace (operational):** May only receive data already filtered by the user’s **operational scope** and **permissions**. No cross-company inference from operational context.

**Operational access answers:** *“What can I operate on right now?”*

---

### Lane 2 — Executive Consolidation Lane

**Who:** Authorized higher management, group executives, regional managers, group auditors, and roles explicitly granted cross-company reporting (not implied by `is_admin` or local admin).

**Purpose:** Aggregated intelligence, executive Q&A, and cross-entity reports — never silent bypass of isolation.

**Rules:**

1. **Consolidation is never automatic.** Holding membership or admin flag does not grant consolidation.
2. User must have **explicit consolidation permission(s)** and **assigned consolidation scope**.
3. Consolidated access may span (when scope and permissions allow):
   - Multiple departments
   - Multiple branches
   - Multiple companies / legal entities
   - Multiple countries / jurisdictions
   - Full holding group
4. **Consolidated answers** must record **which scope was included** (companies, countries, date range, modules).
5. **Consolidated reports** must respect **data classification** and **redaction policy**.
6. **Raw restricted / secret** data must not appear in consolidation output unless `consolidation.view_restricted` (or equivalent) is granted and scope allows it.
7. **All consolidated queries and AI summaries** must be **audited** (who, what scope, what classification ceiling, what modules).

**Consolidation access answers:** *“What am I allowed to report across?”*

---

## Operational vs consolidation — examples

| Persona | Operational | Consolidation |
|---------|-------------|---------------|
| Company A admin | Manage Company A users, settings, data | Cannot see Company B operational data |
| Regional executive (UAE) | May operate in one “home” company if assigned | May see consolidated KPIs across UAE companies if `consolidation.report` + UAE consolidation scope |
| Group CEO | Not necessarily a local user admin | May ask Solace executive questions across all companies if **global consolidation scope** + `consolidation.ai_summary` |
| Group compliance auditor | Operates in audit tooling for assigned company if any | May view evidence summaries across companies with consolidation scope; not HR private files without module + classification permission |
| Branch manager | Branch-scoped operations only | No consolidation unless explicitly granted |

---

## Scope data model

### Operational scopes — `Core_UserScopes` (operational lane)

Existing / planned operational assignment. Each row is one grant of **where the user may work**.

| Field | Purpose |
|-------|---------|
| `id` | PK |
| `user_id` | Subject |
| `scope_mode` | **`operational`** (default) — distinguishes lane |
| `scope_type` | `global` \| `country` \| `organization` \| `branch` \| `department` |
| `country_id` | Nullable anchor |
| `organization_id` | Nullable; required for company-scoped types |
| `branch_id` | Nullable |
| `department_id` | Nullable |
| `is_default` | Auto-select at login when single operational default |
| `is_active` | Revocable without delete |
| `created_at`, `created_by` | Audit |

**Note:** `scope_type = global` on **operational** scope means holding-wide *operational eligibility* (e.g. platform ops), not consolidation. Consolidation global is a separate grant on the consolidation model.

### Consolidation scopes — `Core_ConsolidationScopes` (recommended)

Separate table keeps operational and consolidation grants auditable and queryable without conflating “I work here” with “I may report there.”

**Alternative:** Extend `Core_UserScopes` with `scope_mode = consolidation` and consolidation-only columns. Architecture prefers **`Core_ConsolidationScopes`** for clarity.

| Field | Purpose |
|-------|---------|
| `id` | PK |
| `user_id` | Subject |
| `scope_mode` | Fixed: **`consolidation`** (if unified table) |
| `country_id` | Nullable — limit to jurisdiction |
| `organization_id` | Nullable — single company consolidation |
| `branch_id` | Nullable — branch subtree if `include_child_scopes` |
| `department_id` | Nullable |
| `include_child_scopes` | When true, grant includes descendants in hierarchy (e.g. country → all companies in country) |
| `allowed_modules` | Nullable JSON/list — e.g. `sales`, `legal`, `compliance`; null = all modules permitted by permission |
| `max_classification_allowed` | Ceiling (e.g. `internal`, `confidential`); blocks higher labels |
| `can_view_raw_restricted` | Rare; explicit raw secret access in consolidation |
| `can_use_ai_summary` | Allows Solace consolidated Q&A for this scope |
| `is_active` | Revocable |
| `created_at`, `created_by` | Audit |

Session / request context should carry:

- **Active operational scope** (required for tenant isolation)
- **Active consolidation scope** (optional; required only when invoking consolidation APIs or AI consolidation mode)

---

## Permissions

### Operational (existing + Phase 2C foundation)

Examples: `users.read`, `companies.manage`, `scopes.read`, `user_scopes.manage`, module operational permissions.

### Consolidation (new — not optional for executive features)

| Code | Purpose |
|------|---------|
| `consolidation.view` | See consolidation dashboards / scope picker for reporting |
| `consolidation.report` | Run cross-entity reports |
| `consolidation.ai_summary` | Solace executive Q&A across allowed consolidation scope |
| `consolidation.export` | Export consolidated datasets |
| `consolidation.view_restricted` | Include restricted-tier sources in consolidation (highly controlled) |
| `consolidation.manage` | Assign consolidation scopes to users (security admin) |

**Seed:** `system_administrator` and `security_admin` receive consolidation manage; executives receive grants via role, not by default.

---

## AI / Solace consolidation rule

Solace may answer across companies **only when all** of the following are true:

1. User holds `consolidation.ai_summary` (or equivalent module-specific consolidation AI permission).
2. User has **consolidation scope** covering every company/country included in the answer.
3. Source queries are filtered by **classification ceiling** and **redaction rules**.
4. The answer **records and audits** included scope (companies, countries, modules, classification max, correlation id).

Operational Solace sessions must **not** use consolidation scope implicitly. Switching to consolidation AI mode is an explicit user or UI action with audit.

---

## Memory architecture

**Default:** Memories are **separated** by operational scope (company, and finer levels where configured).

### Memory visibility scopes

| Scope | Meaning |
|-------|---------|
| `private_user` | User-only |
| `department` | Department operational context |
| `branch` | Branch operational context |
| `company` | Company operational context |
| `country` | Country-level operational context |
| `global_holding` | Holding-wide operational (rare; tightly permissioned) |
| `consolidation_summary` | Derived executive summary — not raw operational store |

### Rules

1. A memory from **Company A** must **not** appear in **Company B** operational context.
2. **`consolidation_summary`** memories may be created **only** from authorized consolidated reports.
3. Required metadata on `consolidation_summary` memories:
   - Source consolidation scope
   - Included countries / companies (ids and codes)
   - Classification ceiling used
   - `generated_by` (user id)
   - `audit_event_id` (link to audit trail)
   - `expiry` / `review_date`
4. An authorized **global executive** consolidation context may retrieve Company A + Company B **summary** memories if consolidation scope and permissions allow — still not raw Company A operational memories unless operational scope also permits.

---

## Reporting rule (all future modules)

Every major module must implement **two view modes**:

| View mode | API / UI pattern | Data path |
|-----------|------------------|-----------|
| **Operational scoped** | Default lists, CRUD, workflows | Filter by active operational scope + RBAC |
| **Consolidation / reporting** | Separate endpoints or `?view=consolidation` | Aggregate/read-only; consolidation scope + permissions + classification |

Modules must not expose consolidation aggregates on operational routes.

---

## Future module patterns

### Document Hub

- Company users see and manage **their** documents under operational scope.
- Executives ask *“How many documents in UAE companies?”* only with consolidation scope + permission.
- Raw restricted documents stay protected; consolidation returns counts or redacted summaries unless `consolidation.view_restricted`.

### Sales

- Company sales teams: operational scoped pipeline and orders.
- Group management: consolidated group sales via consolidation APIs; no automatic cross-company drill-down in operational UI.

### Legal

- Local legal teams: cases and matters in their company.
- Group legal head: cross-country **summaries** when consolidation scope includes those countries and `legal` module allowed in `allowed_modules`.

### HR

- HR data is highly sensitive.
- Consolidated HR: **aggregated / redacted** by default (headcount bands, policy compliance rates). Raw employee files excluded unless exceptional permission + audit.

### Audit

- Local admins: audit for active company operational scope.
- Group auditors: cross-company audit **only** with `consolidation.view` + consolidation scope; event types and classification filters enforced.

---

## Active scope and sessions

| Context | Stored on session / JWT | Used for |
|---------|-------------------------|----------|
| Active operational scope | `active_scope_type`, `organization_id`, branch, department, country | Tenant isolation, CRUD, operational AI |
| Active consolidation scope | Optional consolidation scope id or denormalized bounds | Reports, consolidation AI, export |

`POST /auth/switch-scope` switches **operational** context.  
`POST /auth/switch-consolidation-scope` (planned) switches **consolidation** context for reporting lane — does not widen operational write access.

---

## Audit requirements

| Event | Minimum detail |
|-------|----------------|
| Operational scope switch | User, from/to scope, IP |
| Consolidation scope switch | User, consolidation scope id, bounds |
| Consolidation report run | Scope, modules, classification ceiling, row counts |
| Consolidation AI query | Prompt hash, scope included, models, classification ceiling |
| Consolidation export | Scope, format, record counts |
| `consolidation_summary` memory create | Source report id, scope, expiry |

---

## LDAP and provisioning

- Directory sync assigns **operational** scope only (default company/branch/department).
- **Consolidation scopes** are never implied by LDAP group membership without explicit mapping policy (future: optional group → consolidation scope template).
- No user is “global consolidator” by default.

---

## Tenant isolation (unchanged core rule)

1. Operational queries use **active company** (`organization_id`) unless audited system bypass.
2. Consolidation queries use **consolidation scope** to build an explicit allow-list of companies/countries — never `SELECT *` across the holding without scope proof.
3. Country is context; company is operational tenant boundary.

---

## Summary — final model

```
┌─────────────────────────────────────────────────────────────────┐
│  ISOLATION FOR OPERATION                                         │
│  Active operational scope + RBAC + classification on each row   │
│  AI/memory/document/module data filtered to "what I operate on"   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │  explicit grant only
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CONSOLIDATION FOR EXECUTIVE INTELLIGENCE                        │
│  Core_ConsolidationScopes + consolidation.* permissions          │
│  Aggregates, reports, AI summaries — audited, classified, bounded  │
└─────────────────────────────────────────────────────────────────┘
```

**Controlled by:** scope (operational vs consolidation), permissions, data classification, redaction policy, and audit — together, not any single flag.

---

## Phase 2C implementation alignment

Phase 2C foundation delivery (migration `005_phase2c_enterprise_scope`) implements **operational hierarchy and operational scopes** only. Consolidation lane, consolidation permissions, consolidation AI, and `consolidation_summary` memories are **specified here** and scheduled for a follow-on foundation increment before business modules.

See [Schema changes required](#schema-changes-required-for-phase-2c-and-follow-on) below.

---

## Schema changes required for Phase 2C and follow-on

### Already implemented in Phase 2C (`005_phase2c_enterprise_scope`)

| Artifact | Status |
|----------|--------|
| `Core_Countries` | Done |
| `Core_Organizations` extended (company fields, `country_id`) | Done |
| `Core_Branches` / `Core_Departments` extended | Done |
| `Core_Users` default scope FKs | Done |
| `Core_UserScopes` (operational grants; `scope_type` hierarchy) | Done — **missing `scope_mode`** |
| `Core_UserRoles` scoped columns | Done |
| `Core_Sessions` active operational scope columns | Done |
| `Auth_DirectorySettings` LDAP sync defaults | Done |
| Operational permissions (`countries.*`, `companies.*`, `scopes.*`, …) | Done |

### Required to align Phase 2C with this architecture (follow-on migration `006` or amend before business modules)

#### 1. Operational scope lane clarity

| Change | Detail |
|--------|--------|
| `Core_UserScopes.scope_mode` | `NVARCHAR(32) NOT NULL DEFAULT 'operational'` — values: `operational` only on this table |
| Constraint | Operational scopes must not set consolidation-only columns |

#### 2. Consolidation scope storage (recommended new table)

**Table: `Core_ConsolidationScopes`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | UUID FK → `Core_Users` | |
| `country_id` | UUID FK nullable | |
| `organization_id` | UUID FK nullable | |
| `branch_id` | UUID FK nullable | |
| `department_id` | UUID FK nullable | |
| `consolidation_level` | string | `department` \| `branch` \| `organization` \| `country` \| `holding` |
| `include_child_scopes` | bit | Expand to descendants |
| `allowed_modules` | NVARCHAR(MAX) JSON | Nullable |
| `max_classification_allowed` | NVARCHAR(32) | e.g. internal, confidential, restricted |
| `can_view_raw_restricted` | bit default 0 | |
| `can_use_ai_summary` | bit default 0 | |
| `is_active` | bit default 1 | |
| `created_at` | datetimeoffset | |
| `created_by` | UUID nullable | |

Indexes: `(user_id, is_active)`, optional `(organization_id)`.

#### 3. Session / context

| Change | Detail |
|--------|--------|
| `Core_Sessions.active_consolidation_scope_id` | UUID FK nullable → `Core_ConsolidationScopes` |
| JWT claim | `consolidation_scope_id` optional |

#### 4. Permissions seed

Add to `Core_Permissions` and role bundles:

- `consolidation.view`
- `consolidation.report`
- `consolidation.ai_summary`
- `consolidation.export`
- `consolidation.view_restricted`
- `consolidation.manage`

#### 5. Audit

| Change | Detail |
|--------|--------|
| `AuditTrail` event types | `consolidation_report`, `consolidation_ai_query`, `consolidation_export`, `consolidation_scope_switch` |
| Optional `Core_ConsolidationQueryLog` | Stores scope snapshot, modules, classification ceiling, correlation id for AI/report |

#### 6. Memory (Solace — when memory tables gain scope)

| Change | Detail |
|--------|--------|
| `visibility_scope` enum column | `private_user`, `department`, `branch`, `company`, `country`, `global_holding`, `consolidation_summary` |
| `Core_MemoryConsolidationMeta` or JSON on memory | `source_scope_json`, `included_organization_ids`, `classification_ceiling`, `audit_event_id`, `review_date` |

#### 7. Classification integration (if not already on rows)

Ensure operational and consolidation queries join **classification** and **redaction** rules (existing compliance foundation).

### Not required for operational-only Phase 2C MVP

- Consolidation UI pages (can follow permissions + API)
- Module-specific consolidation aggregates (Document Hub, Sales, etc.) — future modules
- `POST /auth/switch-consolidation-scope` — follow-on API

### Decision record

| Option | Recommendation |
|--------|----------------|
| Extend `Core_UserScopes` with `scope_mode` + consolidation columns | Possible but mixes two security domains in one table |
| **`Core_ConsolidationScopes` separate table** | **Preferred** — clearer audit, assignment UI, and permission checks |

---

## Document history

| Date | Change |
|------|--------|
| 2026-05-17 | Initial master architecture: separation by default, consolidation by authority; two-lane model |

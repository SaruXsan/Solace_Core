# Phase 2D — Executive Consolidation Foundation

**Status:** Implementation  
**Prior checkpoint:** Phase 2C (`PHASE_2C_OPERATIONAL_SCOPE_ISOLATION_COMPLETE`)

## Governing rule

> **Separation by default. Consolidation by explicit authority.**

| Lane | Controls | Default |
|------|----------|---------|
| **Operational** (`Core_UserScopes`, active session scope) | What you **operate on** | Everyone has operational boundaries |
| **Consolidation** (`Core_ConsolidationScopes`, active consolidation scope) | What you may **report across** | Nobody unless explicitly granted |

Operational isolation from Phase 2C remains intact. Consolidation does not replace or bypass operational scope.

---

## Operational scope vs consolidation scope

| | Operational | Consolidation |
|---|-------------|---------------|
| **Session field** | `organization_id`, `active_scope_type`, country/branch/dept | `active_consolidation_scope_id` |
| **Top bar** | Scope selector (company work) | Consolidation selector (optional, reporting authority) |
| **Typical user** | All staff | Executives, group auditors, compliance (when assigned) |
| **Data writes** | Yes, within company | **No** in Phase 2D — foundation only |
| **Cross-company reads** | No | Only via consolidation guard (future reports) |

A user may work in Company A (operational) while holding a UAE regional consolidation scope for KPI reporting.

---

## Core_ConsolidationScopes

Explicit grants per user:

- `scope_level`: global / country / organization / branch / department
- Hierarchy FKs + `include_child_scopes`
- `max_classification_allowed`: Public → Secret ceiling
- `can_view_raw_restricted`, `can_use_ai_summary`, `can_export`
- `allowed_modules` (JSON list, optional)

---

## Permissions

| Code | Purpose |
|------|---------|
| `consolidation.view` | See assigned scopes, activate consolidation context |
| `consolidation.report` | Future consolidated reports |
| `consolidation.ai_summary` | Future executive AI summaries |
| `consolidation.export` | Future export of consolidated data |
| `consolidation.view_restricted` | Raw restricted/secret in consolidation output |
| `consolidation.manage` | Create/update/disable consolidation scopes |

**Role seeds:**

- `system_administrator`: all consolidation permissions
- `security_admin`: `consolidation.view`, `consolidation.manage`
- `compliance_reviewer`: `consolidation.view`, `consolidation.report`
- `standard_user` / `read_only`: none unless explicitly assigned scopes

---

## Classification and restricted data

- Consolidation output must not exceed `max_classification_allowed` on the active scope.
- Raw **Restricted** / **Secret** requires `consolidation.view_restricted` **and** `can_view_raw_restricted` on the scope.
- Denials audit as `consolidation_restricted_data_denied`.

---

## Audit requirements

Events: `consolidation_scope_created`, `consolidation_scope_updated`, `consolidation_scope_disabled`, `consolidation_scope_switched`, `consolidation_access_denied`, `consolidation_restricted_data_denied`, `consolidation_access_granted`.

Each guard evaluation records actor, consolidation scope id, requested entities, module, classification, allowed/denied, reason.

---

## AI / Solace (future)

`app/core/ai_consolidation_policy.py` pre-flight only:

- AI never decides access
- Data filtered before any model call
- Requires active consolidation scope + `consolidation.ai_summary`
- Redaction required by default

No executive AI or summaries are built in Phase 2D.

---

## Memory (preparation)

`Solace_MemoryAtoms` extended (migration 006):

- `visibility_scope`, `source_scope`, `included_countries`, `included_organizations`
- `classification_ceiling`, `audit_event_id`, `review_date`

**Rules:**

- Company memory must never enter another company's operational context.
- `consolidation_summary` visibility is for future authorized consolidated reports only.

---

## API (foundation)

| Method | Path |
|--------|------|
| GET | `/api/v1/consolidation/scopes` |
| POST | `/api/v1/consolidation/scopes` |
| PATCH | `/api/v1/consolidation/scopes/{id}` |
| POST | `/api/v1/auth/switch-consolidation-scope` |
| GET | `/api/v1/auth/active-consolidation-scope` |

Services: `consolidation_scope_service.py`, `consolidation_guard.py`

---

## UI

- **Platform → Consolidation Scopes** — list/create/edit (manage permission)
- **Top bar → Consolidation** selector — separate from operational Scope selector

No executive dashboards, reports, or AI summary UI in this phase.

---

## What Phase 2D does NOT build

- Business modules (Document Hub, HR, Legal, Operations, IT, Email Intelligence)
- Executive reporting dashboards
- AI executive summaries
- Cross-company operational data access
- Implicit consolidation from `is_admin` alone

---

## Migration

Head: `006_phase2d_executive_consolidation`

```bat
backend\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

# Provenance: Story 3.12 — Geocoding Infrastructure

## Bucket Classification

**Bucket B — Greenfield core implementation**

No premium, enterprise, or clean-room-restricted source files were read or referenced during implementation.

## New Files Created

All files are original implementations in `backend/src/baserow/geocoding/` and `backend/tests/baserow/geocoding/`. No code was copied or derived from any enterprise/premium module.

## Pattern Sources (free core only)

| Pattern | Source (free core) |
|---|---|
| Celery task structure | `backend/src/baserow/contrib/database/export/tasks.py` |
| CELERY_TASK_ROUTES entry | `backend/src/baserow/config/settings/base.py` |
| Env var format | `backend/src/baserow/config/settings/base.py` (INTEGRATION_LOCAL_BASEROW_PAGE_SIZE_LIMIT template) |
| Field permission check | `baserow.core.handler.CoreHandler.check_permissions` + `ReadFieldOperationType` from free `baserow.contrib.database.fields.operations` |
| Django AppConfig | `backend/src/baserow/contrib/dashboard/apps.py` |

## Date

2026-06-11

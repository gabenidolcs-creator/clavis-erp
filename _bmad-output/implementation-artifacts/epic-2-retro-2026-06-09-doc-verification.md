# Epic 2 Retrospective — Doc-Update Verification Pass

**Date:** 2026-06-09
**Method:** For each candidate doc surfaced by Epic 2 implementation learnings, read the current doc, compare against the as-built code/config, and either (a) update on a verified discrepancy or (b) discard where doc matches code.

---

## Candidate List & Verdicts

| # | Doc | Learning that flagged it | Verified against | Verdict |
|---|-----|--------------------------|------------------|---------|
| 1 | `docs/development/running-tests.md` | Epic 2 backend tests ran against `baserow-test-db` on port **5431** (Story 2.5 dev notes / debug log) | `justfile:1057` `test_db_port := env("TEST_DB_PORT", "5431")`; running container `baserow-test-db 0.0.0.0:5431->5432` | **UPDATED** — doc stated default `5433` in 4 places; code default is `5431`. Fixed all 4. |
| 2 | `docs/plugins/field-type.md` | Epic 2 added 5 field types; i18n key-location and read-only/signal recompute gotchas | Doc describes the **plugin** extension path (`field_type_registry.register` from a plugin app). Epic 2 registered **in-tree** in `baserow/contrib/database/apps.py` — a different, still-valid mechanism. Doc has no i18n/signal guidance to contradict. | **DISCARDED** — no divergence; doc documents a separate path Epic 2 did not use. |
| 3 | `_bmad-output/planning-artifacts/architecture.md` | Did the MTI / Bucket-B field-type strategy change during build? | Implementation matched the plan exactly: MTI subclasses of `NumberFieldType`/`TextField`/`ReadOnlyFieldType`, Bucket B, no clean-room gate, zero new user-table columns. | **DISCARDED** — code matches architecture; no decision changed. |
| 4 | `docs/apis/rest-api.md` | New field config params (`currency_symbol`, `barcode_type`, etc.) | Baserow REST API reference is OpenAPI-generated from serializers, not hand-maintained per field. New params are exposed via `serializer_field_names`; no hand-written API doc claims otherwise. | **DISCARDED** — no hand-maintained API statement diverged. |
| 5 | `README.md` | Outdated setup/instructions | Upstream Baserow project README; untouched by and unrelated to Epic 2's field-type work. | **DISCARDED** — out of scope, no Epic 2 discrepancy. |
| 6 | i18n authoring guidance (story-template / docs) | Story 2.5 spec named `fieldType.runningCountDescription` but repo convention is `fieldType.<type>` + `fieldDocs.<type>` in `web-frontend/locales/en.json` | No committed *doc* asserts the wrong location — the error was in the **story text**, not a doc. Captured as retro Action Item D1 (story-authoring guidance), not a doc fix. | **DISCARDED as doc fix** — tracked as action item instead. |

---

## Changes Applied

### `docs/development/running-tests.md` (4 edits)
- "Start ramdisk database on port **5433**" → **5431**
- `TEST_DB_PORT` "(default: **5433**)" → **5431**
- 2× `DATABASE_URL=postgres://baserow:baserow@localhost:**5433**/baserow` → **5431**

Source of truth: `justfile:1057` and the live `baserow-test-db` container port mapping.

---

## Summary

- **Docs updated:** 1 (`running-tests.md` — verified port discrepancy)
- **Candidates discarded (code matches / out of scope):** 5
- **Discrepancies left for action items rather than doc edits:** 1 (i18n story-authoring guidance → Action Item D1)

The low edit count is expected: Epic 2 deliberately followed existing Baserow patterns (MTI extension, Bucket B), so most docs already matched the as-built code. The one genuine drift was a stale test-DB default port.

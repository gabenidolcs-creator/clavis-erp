# Provenance record — Story 1.4 Central field-permission layer with edit restriction

- **PR / branch:** feat(story-1.4) central field-permission layer with edit restriction (branch: develop)
- **Story:** 1.4 Central field-permission layer with edit restriction
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06

## Sources Consulted

<!--
All sources below are on the allowed-source list (see ../allowed-sources.md):
public docs, public SaaS UI, public issues, and MIT free-core symbols in this repo.
No excluded paid (PE/EE) source was read, copied, adapted, or recalled.
-->

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow field-permission UX — admin marks a single field read-only to lower roles while it stays readable | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | `WriteFieldValuesOperationType` (`database.table.field.write_values`) — per-field write op already emitted on row update | MIT free-core | `backend/src/baserow/contrib/database/fields/operations.py` |
| 3 | `UpdateFieldOperationType` (`database.table.field.update`) — field-config update op | MIT free-core | `backend/src/baserow/contrib/database/fields/operations.py` |
| 4 | `PermissionManagerType` contract (True=grant / exception=deny / absent=defer) + `get_permissions_object` + `supported_actor_types` | MIT free-core | `backend/src/baserow/core/registries.py` |
| 5 | `CoreHandler.check_multiple_permissions` batch collapse-to-False vs `return_permissions_exceptions`; single-check re-raise; `get_permissions` aggregation | MIT free-core | `backend/src/baserow/core/handler.py` |
| 6 | `RowHandler._check_write_fields_values_permissions` — existing per-field `write_values` hook (the 401→403 fix point) | MIT free-core | `backend/src/baserow/contrib/database/rows/handler.py` |
| 7 | `FieldHandler.update_field` — config path that re-raises → 403 | MIT free-core | `backend/src/baserow/contrib/database/fields/handler.py` |
| 8 | `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` — operation-`type`-string admin-gating convention | MIT free-core | `backend/src/baserow/core/permission_manager.py` |
| 9 | `RbacHandler.get_effective_role`, `roles.role_at_least`, `ROLE_ORDER` (Story 1.2) — effective-role reuse | MIT free-core (this repo) | `backend/src/baserow/core/rbac/handler.py`, `roles.py` |
| 10 | `PermissionException`/`PermissionDenied` hierarchy + `api_exception_registry` global 403 mapping (Story 1.3 `RoleProhibitedError` pattern) + `Field.read_only` precedent | MIT free-core | `backend/src/baserow/core/exceptions.py`, `backend/src/baserow/core/apps.py`, `backend/src/baserow/api/errors.py`, `backend/src/baserow/contrib/database/fields/models.py` |
| 11 | Frontend `canWriteFieldValues → $hasPermission('…write_values')` cell gate + `PermissionManagerType` frontend base | MIT free-core | `web-frontend/modules/database/fieldTypes.js`, `web-frontend/modules/core/permissionManagerTypes.js` |
| 12 | Application-Builder LocalBaserow data-source `write_values` check (the second governed surface) | MIT free-core | `backend/src/baserow/contrib/integrations/local_baserow/service_types.py` |
| 13 | Django / DRF framework documentation | general public knowledge | https://docs.djangoproject.com , https://www.django-rest-framework.org |

## Implementer Attestation

- [x] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any `premium/` or `enterprise/`
      (PE/EE) source for this feature, and I was not *influenced by* it. Every source I
      used is listed above and is on the allowed-source list.

**Implementer signature / handle:** AI dev-agent (isolation model (a))   **Date:** 2026-06-06

## Reviewer confirmation (filled at review)

- [ ] Reviewer verified implementer eligibility per implementer-isolation.md.
- [ ] Reviewer verified all sources above are on the allowed-source list.

## Notes

- **One schema change:** a new `FieldPermission` model + migration in the `database`
  app (rule row lives next to `Field`; enforcement lives in `core/field_permissions/`).
  Reverting drops the table and restores pre-1.4 behavior (no rule = unrestricted).
- The enterprise field-permissions feature (`enterprise/backend/.../field_permissions/`)
  was **not** consulted. Its DB-driven `FieldPermissions` model, `FieldPermissionsRoleEnum`
  (incl. CUSTOM/NOBODY), and custom-subject allow/deny system are **not** our design;
  only the public MIT registry shape (a manager returning an exception to deny + the
  existing `write_values` op) is shared.

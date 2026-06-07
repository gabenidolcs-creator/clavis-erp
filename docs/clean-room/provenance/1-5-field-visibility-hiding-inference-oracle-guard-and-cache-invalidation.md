# Provenance record — Story 1.5 Field visibility hiding, inference-oracle guard, and cache invalidation

- **PR / branch:** feat(story-1.5) field visibility hiding, inference-oracle guard, and cache invalidation (branch: develop)
- **Story:** 1.5 Field visibility hiding, inference-oracle guard, and cache invalidation
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
| 1 | Public Airtable/Baserow field-permission UX — admin hides a single field from lower roles so they never see its value; higher roles still see it | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | `ReadFieldOperationType` (`database.table.field.read`) — per-field read op | MIT free-core | `backend/src/baserow/contrib/database/fields/operations.py` |
| 3 | `PermissionManagerType.filter_queryset` / `get_permissions_object` contract | MIT free-core | `backend/src/baserow/core/registries.py` |
| 4 | `CoreHandler.filter_queryset` dispatch (None = defer, queryset = apply) | MIT free-core | `backend/src/baserow/core/handler.py` |
| 5 | `get_row_serializer_class(..., exclude_field_ids=...)` include/exclude filter (exclude overrides include) | MIT free-core | `backend/src/baserow/contrib/database/api/rows/serializers.py` |
| 6 | `get_hidden_field_ids_for_view_user` view-ownership hidden set + `get_view_filtered_queryset` search narrowing | MIT free-core | `backend/src/baserow/contrib/database/api/views/utils.py` |
| 7 | `search_all_fields(only_search_by_field_ids=...)` | MIT free-core | `backend/src/baserow/contrib/database/table/models.py` |
| 8 | `ViewHandler.create_sort`/`create_filter`/`update_filter`/`update_sort` — the `ReadFieldOperationType` guard asymmetry closed here | MIT free-core | `backend/src/baserow/contrib/database/views/handler.py` |
| 9 | `TablePageType.can_add` / `RowPageType.can_add` subscribe-time auth | MIT free-core | `backend/src/baserow/contrib/database/ws/pages.py` |
| 10 | `invalidate_table_in_model_cache(table_id)` model-cache hook | MIT free-core | `backend/src/baserow/contrib/database/table/cache.py` |
| 11 | `permissions_updated` signal + per-table permission-channel-group broadcast (`users_removed_from_permission_group`, `send_message_to_channel_group`, `get_permission_channel_group_name`) | MIT free-core | `backend/src/baserow/core/signals.py`, `backend/src/baserow/contrib/database/table/tasks.py`, `backend/src/baserow/ws/consumers.py` |
| 12 | Story 1.4 `FieldPermission` model, `FieldPermissionManagerType`, `FieldPermissionHandler`, `FieldEditProhibitedError → ERROR_FIELD_EDIT_PROHIBITED → core/apps.py` 403 registration (this repo) — extended | MIT free-core (this repo) | `backend/src/baserow/contrib/database/fields/models.py`, `backend/src/baserow/core/field_permissions/`, `backend/src/baserow/core/exceptions.py`, `backend/src/baserow/core/apps.py`, `backend/src/baserow/api/errors.py` |
| 13 | `RbacHandler.get_effective_role`, `roles.role_at_least`, `ROLE_ORDER` (Story 1.2) | MIT free-core (this repo) | `backend/src/baserow/core/rbac/handler.py`, `roles.py` |
| 14 | Frontend `PermissionManagerType` base + 1.4 `FieldPermissionManagerType` + `$hasPermission` chain | MIT free-core | `web-frontend/modules/core/permissionManagerTypes.js` |
| 15 | Django / DRF framework documentation | general public knowledge | https://docs.djangoproject.com , https://www.django-rest-framework.org |

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

- **One schema change:** a `readable_by_role` column added to the existing 1.4
  `FieldPermission` model (one migration in the `database` app, after `0212`).
  Reverting drops the column and restores 1.4 behavior (no read threshold = visible).
- **No enterprise read-redaction logic consulted.** The enterprise field-permissions
  feature's read path (its `filter_queryset` / anonymous-value submission / custom-subject
  `get_permissions_object` payload) was **not** read or recalled. The redaction here is a
  single `FieldPermissionManagerType.filter_queryset` + one `FieldPermissionHandler.get_hidden_field_ids`
  helper fed into the pre-existing free-core `exclude_field_ids` / `only_search_by_field_ids`
  levers — no parallel surface-specific hiding.
- **Redaction omits; the guard raises.** A normal read silently drops a hidden field
  (no 403). Only a filter/sort *on* a hidden field raises `FieldVisibilityProhibitedError`
  → 403 `ERROR_FIELD_VISIBILITY_PROHIBITED`, registered globally exactly as 1.4's
  `FieldEditProhibitedError`.

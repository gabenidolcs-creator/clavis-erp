---
baseline_commit: 7a1669e9202c58ae0c02fb485f0f90b648943fae
---

# Story 1.9: Exports Honor Field Permissions

Status: review

## Story

As an admin,
I want every export path to respect Field Permissions and row restrictions,
so that hidden data cannot leak through a download.

## Acceptance Criteria

1. **[AC1 — Export field redaction]**: Given a principal exports via CSV/JSON/XLSX, Map, or any download, when the export is produced, then Fields hidden by Field Permissions (FR-30) are absent from every format, and the export path consumes the central field-permission layer established in Story 1.5.

2. **[AC2 — Anonymous/public export surface]**: Given a public/anonymous principal (ExportJob where user is None, or an interface-only principal), when they trigger an export of a public view with `allow_public_export=True`, then they cannot export beyond their granted surface — Fields restricted to roles above anonymous are absent from the output.

## Tasks / Subtasks

- [x] Task 1: Add `hidden_field_ids` parameter to `QuerysetSerializer.for_table()` and `for_view()` (AC: #1, #2)
  - [x] 1.1: In `backend/src/baserow/contrib/database/export/file_writer.py` L183, change `for_table(cls, table)` → `for_table(cls, table, hidden_field_ids=None)`. After computing `ordered_field_objects = model._field_objects.values()`, add: `if hidden_field_ids: ordered_field_objects = [fo for fo in ordered_field_objects if fo["field"].id not in hidden_field_ids]`
  - [x] 1.2: In the same file L196, change `for_view(cls, view, visible_field_ids_in_order=None)` → `for_view(cls, view, visible_field_ids_in_order=None, hidden_field_ids=None)`. After `fields` is resolved (at the end of the `if/else` for `visible_field_ids_in_order`), add: `if hidden_field_ids: fields = [fo for fo in fields if fo["field"].id not in hidden_field_ids]`. Return value and `visible_field_objects_in_view` remain unchanged.

- [x] Task 2: Compute and inject `hidden_ids` in `_open_file_and_run_export` (AC: #1, #2)
  - [x] 2.1: In `backend/src/baserow/contrib/database/export/handler.py` L333, at the top of `_open_file_and_run_export`, after `exporter = table_exporter_registry.get(job.exporter_type)`, add the imports and actor/hidden_ids computation:
    ```python
    from django.contrib.auth.models import AnonymousUser
    from baserow.contrib.database.fields.field_permission_handler import FieldPermissionHandler
    actor = job.user if job.user is not None else AnonymousUser()
    hidden_ids = FieldPermissionHandler.get_hidden_field_ids(actor, job.table)
    ```
  - [x] 2.2: Change `queryset_serializer_class.for_table(job.table)` (L364) → `queryset_serializer_class.for_table(job.table, hidden_field_ids=hidden_ids)`
  - [x] 2.3: Change `queryset_serializer_class.for_view(job.view, visible_fields_in_order)` (L366) → `queryset_serializer_class.for_view(job.view, visible_fields_in_order, hidden_field_ids=hidden_ids)`
  - [x] 2.4: After computing `only_by_field_ids = [f["field"].id for f in visible_fields_in_view]` (L368), add: `if hidden_ids: only_by_field_ids = [fid for fid in only_by_field_ids if fid not in hidden_ids]` — prevents ad-hoc filter/sort options from referencing hidden fields.

- [x] Task 3: Write backend tests (AC: #1, #2)
  - [x] 3.1: `test_export_table_hides_permission_restricted_field` in `backend/tests/baserow/contrib/database/api/export/test_export_views.py` — MEMBER user, one ADMIN-restricted text field and one open text field; table export (no view); run export via API + `django_capture_on_commit_callbacks`; read CSV from tmpdir storage; assert restricted field column header absent, open field present.
  - [x] 3.2: `test_export_view_hides_permission_restricted_field` — same setup but with a `grid_view`; view export; assert restricted field absent from CSV.
  - [x] 3.3: `test_export_no_field_permissions_exports_all_fields` — two fields, no `FieldPermission` rows; table export; assert both field columns present (regression guard).
  - [x] 3.4: `test_export_anonymous_public_view_hides_restricted_field` — call `_open_file_and_run_export` directly with an `ExportJob` where `user=None`, view is public with `allow_public_export=True`, and one ADMIN-restricted field; assert restricted field absent from CSV output.

## Dev Notes

### Architecture Context

This story wires Epic 1's central field-permission enforcement layer (Architecture D7, Story 1.5) into the export pipeline. It is Bucket `[X]` — extending existing free core code. No clean-room mandate.

**Central redactor (do not re-implement):**
- `backend/src/baserow/contrib/database/fields/field_permission_handler.py` — `FieldPermissionHandler.get_hidden_field_ids(user, table) → Set[int]`
  - Routes through `CoreHandler().filter_queryset(user, ReadFieldOperationType.type, ...)` → `FieldPermissionManagerType._hidden_field_ids(actor, workspace)`
  - For `AnonymousUser`, returns all field IDs with a `readable_by_role` restriction (Story 1.8 verified this path in handler tests at `test_view_handler.py:5565`)
  - For a MEMBER user, returns IDs of fields where MEMBER is excluded from `readable_by_role`

### Key Files to Modify (UPDATE)

| File | Lines | What to change |
|------|-------|----------------|
| `backend/src/baserow/contrib/database/export/file_writer.py` | L183–193 | `for_table()` — add `hidden_field_ids` param, filter `ordered_field_objects` |
| `backend/src/baserow/contrib/database/export/file_writer.py` | L196–228 | `for_view()` — add `hidden_field_ids` param, filter resolved `fields` |
| `backend/src/baserow/contrib/database/export/handler.py` | L333–388 | `_open_file_and_run_export` — compute actor+hidden_ids, pass to serializer, filter only_by_field_ids |

### Current State of Key Functions

**`_open_file_and_run_export` (handler.py L333):**
```python
def _open_file_and_run_export(job: ExportJob) -> ExportJob:
    exporter: TableExporter = table_exporter_registry.get(job.exporter_type)
    # ... file setup ...
    filters = job.export_options.pop("filters", None)
    order_by = job.export_options.pop("order_by", None)
    visible_fields_in_order = job.export_options.pop("fields", None)
    only_by_field_ids = None

    with _create_storage_dir_if_missing_and_open(storage_location) as file:
        queryset_serializer_class = exporter.queryset_serializer_class
        if job.view is None:
            serializer = queryset_serializer_class.for_table(job.table)          # ← ADD hidden_field_ids
        else:
            serializer, visible_fields_in_view = queryset_serializer_class.for_view(
                job.view, visible_fields_in_order                                # ← ADD hidden_field_ids
            )
            only_by_field_ids = [f["field"].id for f in visible_fields_in_view]  # ← FILTER out hidden_ids
        # ...
```

**`QuerysetSerializer.for_table` (file_writer.py L183):**
```python
@classmethod
def for_table(cls, table) -> "QuerysetSerializer":                   # ← ADD hidden_field_ids=None
    model = table.get_model()
    qs = model.objects.all().enhance_by_fields()
    ordered_field_objects = model._field_objects.values()            # ← FILTER before return
    return cls(qs, ordered_field_objects)
```

**`QuerysetSerializer.for_view` (file_writer.py L196):**
```python
@classmethod
def for_view(cls, view, visible_field_ids_in_order=None) -> ...:     # ← ADD hidden_field_ids=None
    view_type = view_type_registry.get_by_model(view.specific_class)
    visible_field_objects_in_view, model = view_type.get_visible_fields_and_model(view)
    if visible_field_ids_in_order is None:
        fields = visible_field_objects_in_view
    else:
        field_map = {fo["field"].id: fo for fo in visible_field_objects_in_view}
        fields = [field_map[fid] for fid in visible_field_ids_in_order if fid in field_map]
    # ← INSERT: if hidden_field_ids: fields = [fo for fo in fields if fo["field"].id not in hidden_field_ids]
    qs = ViewHandler().get_queryset(None, view, model=model)
    return cls(qs, fields), visible_field_objects_in_view            # visible_field_objects_in_view unchanged — caller uses for only_by_field_ids
```

### Imports to Add to handler.py

Move the two imports inside the function body (local imports, like other circular-avoiding patterns in this codebase) to avoid any circular import risk:
```python
from django.contrib.auth.models import AnonymousUser
from baserow.contrib.database.fields.field_permission_handler import FieldPermissionHandler
```

Check whether `FieldPermissionHandler` is already imported at the top of `handler.py` before deciding whether to import at module scope or locally. If already imported at module scope, use it directly; only use a local import if it's not there.

### Anonymous / Public Export Path

- `ExportJob.user` is a nullable FK (`ForeignKey(User, null=True)`) — public-view exports set `user=None`
- `view_is_publicly_exportable(user, view)` in `export/utils.py`: `return user is None and view and view.allow_public_export and view.public`
- When `job.user is None`, actor = `AnonymousUser()` → `FieldPermissionHandler.get_hidden_field_ids(AnonymousUser(), table)` → returns all fields with any `readable_by_role` restriction

### Restricted Rows Note

The AC mentions "restricted Rows absent." Row-level restrictions are already enforced by `ViewHandler().get_queryset()` which applies view filters. There is no separate row-level RBAC in the current architecture. For table exports (no view), no row restriction exists by design. This AC clause is satisfied by existing view filter behavior — no additional row-level work needed.

### Test Pattern from Existing Tests

Use the full integration pattern from `test_exporting_csv_writes_file_to_storage` (test_export_views.py L183):
- `FileSystemStorage(location=str(tmpdir), base_url="http://localhost")`
- `patch("baserow.core.storage.get_default_storage")` → mock returns `storage`
- Create job via API POST `reverse("api:database:export:export_table", kwargs={"table_id": table.id})`
- `django_capture_on_commit_callbacks(execute=True)` to run the celery task in-process
- Read file from `tmpdir.join(settings.EXPORT_FILES_DIRECTORY, filename)` 
- Assert CSV column headers (first line after BOM `﻿`) contain/don't contain field names

For Task 3.4 (anonymous job), create `ExportJob` model instance directly with `user=None` and call the module-level `_open_file_and_run_export` function. Import it:
```python
from baserow.contrib.database.export.handler import _open_file_and_run_export
```
Create a minimal `ExportJob` with `state="pending"`, `table=table`, `view=public_view`, `user=None`, `exporter_type="csv"`, `export_options={"csv_include_header": True, "csv_column_separator": ",", "export_charset": "utf-8"}`.

### FieldPermission Creation Pattern

From existing Story 1.8 tests:
```python
from baserow.contrib.database.fields.models import FieldPermission
FieldPermission.objects.create(field=restricted_field, readable_by_role="ADMIN")
```
No data_fixture helper — create directly via ORM.

### Previous Story Learnings (1.8)

- Inline imports inside functions are the pattern used in `permission_manager.py` to avoid circular imports — apply same judgment here
- `FieldPermissionHandler.get_hidden_field_ids` is safe to call for AnonymousUser (verified in handler test at line 5565)
- Always run `just b test backend/tests/baserow/contrib/database/api/export/` after changes
- `PASSWORD_HASHERS` not overridden in tests — Argon2 is active; for export tests this is irrelevant
- Test environment requires `BASEROW_OSS_ONLY=true` behavior but local `pytest` needs full install to resolve `baserow_premium`; CI is the authoritative test runner

### Project Structure Notes

- Export handler: `backend/src/baserow/contrib/database/export/handler.py`
- Export file_writer: `backend/src/baserow/contrib/database/export/file_writer.py`
- Export tests (API): `backend/tests/baserow/contrib/database/api/export/test_export_views.py`
- Field permission handler: `backend/src/baserow/contrib/database/fields/field_permission_handler.py`
- ExportJob model: `backend/src/baserow/contrib/database/export/models.py`

### References

- Architecture D7: `_bmad-output/planning-artifacts/architecture.md` — "export must wire into core/field_permissions/ central enforcement layer"
- Story 1.5 implementation: `backend/src/baserow/contrib/database/fields/field_permission_handler.py` (established central redactor)
- Story 1.8 anonymous path: `backend/tests/baserow/contrib/database/view/test_view_handler.py:5565` (verifies AnonymousUser hidden_field_ids)
- Existing export tests: `backend/tests/baserow/contrib/database/api/export/test_export_views.py:183` (CSV write pattern)
- `view_is_publicly_exportable`: `backend/src/baserow/contrib/database/export/utils.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Wired `FieldPermissionHandler.get_hidden_field_ids(actor, table)` into `_open_file_and_run_export`: actor = `job.user` or `AnonymousUser()` when user is None.
- Added `hidden_field_ids=None` param to `QuerysetSerializer.for_table()` and `for_view()` — filters field objects before serialization. `visible_field_objects_in_view` return value unchanged (caller uses it for `only_by_field_ids`).
- Added `only_by_field_ids` post-filter to exclude hidden fields from ad-hoc filter/sort scope.
- Imports added as local (inside function body) to avoid circular import risk per codebase pattern.
- 4 tests added: table export redaction, view export redaction, regression guard (no permissions = all fields), anonymous public view redaction.
- Ruff lint: all checks passed.

### File List

- `backend/src/baserow/contrib/database/export/file_writer.py` (UPDATE)
- `backend/src/baserow/contrib/database/export/handler.py` (UPDATE)
- `backend/tests/baserow/contrib/database/api/export/test_export_views.py` (UPDATE — add 4 new tests)

## Change Log

- 2026-06-06: Story 1.9 implemented — export field permission enforcement wired into `_open_file_and_run_export`, `for_table`, `for_view`; 4 tests added.

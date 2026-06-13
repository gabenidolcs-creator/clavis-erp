"""Story 6.4 — FR-31 interface-only scope verification (Task 5).

DEFERRED: All tests in this file require Story 6.3 (interface-only collaborator role)
to be implemented and its status set to "done". Until then, these tests are scaffolded
but skipped.

Expected behavior once Story 6.3 is done:
- An interface-only principal can access only the App Builder Page they were granted.
- Denied surfaces: DB/Table/View REST list/create/update/delete, App Builder Data Source
  dispatch for out-of-scope pages, formula evaluation, WebSocket channels beyond the
  granted page.
- The deny must be at the data layer (backend permission check), not only in frontend
  navigation guards.
- Positive path: interface-only principal accessing their granted page's Data
  Source → 200.
"""

import pytest

SKIP_REASON = (
    "Requires Story 6.3 (interface-only collaborator role) to be implemented. "
    "When 6.3 status = done, remove the @pytest.mark.skip decorators and verify."
)


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_denied_db_table_list():
    """interface-only principal receives 403 on GET /api/database/tables/."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_denied_table_list():
    """interface-only principal receives 403 on GET /api/database/tables/{id}/."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_denied_view_list():
    """interface-only principal receives 403 on GET /api/database/views/{table_id}/."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_denied_row_create():
    """interface-only principal receives 403 on POST /api/database/rows/{table_id}/."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_denied_row_update():
    """interface-only principal receives 403 on PATCH
    /api/database/rows/{table_id}/{row_id}/."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_denied_row_delete():
    """interface-only principal receives 403 on DELETE
    /api/database/rows/{table_id}/{row_id}/."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_denied_out_of_scope_data_source_dispatch():
    """interface-only principal dispatching a Data Source outside their granted
    Page → 403."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_allowed_granted_page_data_source():
    """Positive path: interface-only principal dispatching their granted Page's
    Data Source → 200."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_denied_websocket_ungranted_table():
    """interface-only principal cannot subscribe to WebSocket for a table not on their page."""
    raise NotImplementedError("Requires Story 6.3")


@pytest.mark.django_db
@pytest.mark.skip(reason=SKIP_REASON)
def test_interface_only_deny_is_backend_not_frontend_only():
    """Confirm the deny is enforced in the permission manager, not only a frontend
    navigation guard. If Story 6.3 uses a frontend-only guard as the sole protection,
    this test must fail and the finding must be escalated as CRITICAL."""
    raise NotImplementedError("Requires Story 6.3")

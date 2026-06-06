"""Story 1.4 — unit tests for ``FieldPermissionManagerType``.

Assert: a restricted field denies a below-threshold role's write_values/field.update with
``FieldEditProhibitedError``; defers for an unrestricted field, for an at/above-threshold
role, and for read ops; and the admin-only update_permission op denies a non-admin while
granting the Admin tier. Also asserts no N+1 (one rule query for N field checks).
"""

from django.conf import settings

import pytest

from baserow.contrib.database.fields.models import FieldPermission
from baserow.contrib.database.fields.operations import (
    ReadFieldOperationType,
    UpdateFieldOperationType,
    UpdateFieldPermissionOperationType,
    WriteFieldValuesOperationType,
)
from baserow.core.exceptions import FieldEditProhibitedError
from baserow.core.field_permissions.enforcement import FIELD_EDIT_OPERATIONS
from baserow.core.field_permissions.permission_manager import (
    FieldPermissionManagerType,
)
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import ADMIN, EDITOR, VIEWER
from baserow.core.types import PermissionCheck


def _setup(data_fixture, member_role):
    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    member = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=member, permissions="MEMBER"
    )
    RbacHandler().assign_role(member, workspace, member_role)
    database = data_fixture.create_database_application(user=owner, workspace=workspace)
    table = data_fixture.create_database_table(user=owner, database=database)
    field = data_fixture.create_text_field(table=table)
    return owner, member, workspace, field


@pytest.mark.django_db
def test_denies_below_threshold_write_and_config(data_fixture):
    owner, member, workspace, field = _setup(data_fixture, EDITOR)
    FieldPermission.objects.create(field=field, editable_by_role=ADMIN)

    manager = FieldPermissionManagerType()
    checks = [
        PermissionCheck(member, WriteFieldValuesOperationType.type, field),
        PermissionCheck(member, UpdateFieldOperationType.type, field),
    ]
    result = manager.check_multiple_permissions(checks, workspace)

    assert isinstance(result[checks[0]], FieldEditProhibitedError)
    assert isinstance(result[checks[1]], FieldEditProhibitedError)


@pytest.mark.django_db
def test_defers_for_at_or_above_threshold(data_fixture):
    owner, member, workspace, field = _setup(data_fixture, EDITOR)
    FieldPermission.objects.create(field=field, editable_by_role=EDITOR)

    manager = FieldPermissionManagerType()
    check = PermissionCheck(member, WriteFieldValuesOperationType.type, field)
    result = manager.check_multiple_permissions([check], workspace)

    # Editor == threshold → defer (omit from result).
    assert check not in result


@pytest.mark.django_db
def test_defers_for_unrestricted_field(data_fixture):
    owner, member, workspace, field = _setup(data_fixture, EDITOR)
    # No FieldPermission row → unrestricted.

    manager = FieldPermissionManagerType()
    check = PermissionCheck(member, WriteFieldValuesOperationType.type, field)
    result = manager.check_multiple_permissions([check], workspace)

    assert check not in result


@pytest.mark.django_db
def test_defers_for_read_operation(data_fixture):
    owner, member, workspace, field = _setup(data_fixture, EDITOR)
    FieldPermission.objects.create(field=field, editable_by_role=ADMIN)

    manager = FieldPermissionManagerType()
    check = PermissionCheck(member, ReadFieldOperationType.type, field)
    result = manager.check_multiple_permissions([check], workspace)

    # Read is not a governed op → defer (the field stays readable).
    assert check not in result


@pytest.mark.django_db
def test_admin_update_permission_op(data_fixture):
    owner, member, workspace, field = _setup(data_fixture, EDITOR)
    RbacHandler().assign_role(owner, workspace, ADMIN)

    manager = FieldPermissionManagerType()
    editor_check = PermissionCheck(
        member, UpdateFieldPermissionOperationType.type, field
    )
    admin_check = PermissionCheck(owner, UpdateFieldPermissionOperationType.type, field)
    result = manager.check_multiple_permissions([editor_check, admin_check], workspace)

    assert isinstance(result[editor_check], FieldEditProhibitedError)
    assert result[admin_check] is True


@pytest.mark.django_db
def test_no_n_plus_one_rule_query(data_fixture, django_assert_num_queries):
    owner, member, workspace, field = _setup(data_fixture, EDITOR)
    database = field.table.database
    fields = [field] + [
        data_fixture.create_text_field(table=field.table) for _ in range(4)
    ]
    for f in fields:
        FieldPermission.objects.create(field=f, editable_by_role=ADMIN)

    manager = FieldPermissionManagerType()
    checks = [
        PermissionCheck(member, WriteFieldValuesOperationType.type, f) for f in fields
    ]

    # Rules (1) + field→application (1) + role index (1) = a constant number of
    # queries regardless of the number of fields checked. Assert it does not scale
    # with N (no per-field rule lookup).
    with django_assert_num_queries(3):
        result = manager.check_multiple_permissions(checks, workspace)

    for check in checks:
        assert isinstance(result[check], FieldEditProhibitedError)


# --- QA gap-fill (bmad-qa-generate-e2e-tests) --------------------------------
# Task 7 AC #2 ("single enforcement path — new surfaces consume the layer") and the
# backend half of AC #1's read-only render (get_permissions_object) had no direct
# coverage. Added below.


@pytest.mark.django_db
def test_single_path_governs_data_source_write_surface(data_fixture):
    """AC #2 — the Application-Builder LocalBaserow data source emits the SAME
    ``write_values`` op (``service_types.py:2069``) the row handler does, so the one
    ``FieldPermissionManagerType`` in the chain governs it with zero surface-specific
    code. Assert: (a) the op the data source emits is in the governed set, (b) the
    manager is the single chain entry that owns it, and (c) a check built exactly as the
    data source builds it is denied for a restricted field."""

    owner, member, workspace, field = _setup(data_fixture, EDITOR)
    FieldPermission.objects.create(field=field, editable_by_role=ADMIN)

    # (a) Both the row handler and the LocalBaserow data source emit this op string.
    assert WriteFieldValuesOperationType.type in FIELD_EDIT_OPERATIONS
    # (b) A single chain entry — no parallel/per-surface manager.
    assert settings.PERMISSION_MANAGERS.count("field_permissions") == 1

    manager = FieldPermissionManagerType()
    # (c) The check is shape-identical to the data-source emission:
    # PermissionCheck(user, WriteFieldValuesOperationType.type, field).
    data_source_check = PermissionCheck(
        member, WriteFieldValuesOperationType.type, field
    )
    result = manager.check_multiple_permissions([data_source_check], workspace)

    assert isinstance(result[data_source_check], FieldEditProhibitedError)


@pytest.mark.django_db
def test_get_permissions_object_lists_restricted_fields_for_below_threshold(
    data_fixture,
):
    """Backend half of AC #1's read-only render: a below-threshold actor's
    ``get_permissions_object`` payload names the field they may not edit, which the
    frontend manager consumes to render the cell read-only."""

    owner, member, workspace, field = _setup(data_fixture, VIEWER)
    FieldPermission.objects.create(field=field, editable_by_role=ADMIN)

    payload = FieldPermissionManagerType().get_permissions_object(member, workspace)

    assert payload == {"restricted_field_ids": [field.id]}


@pytest.mark.django_db
def test_get_permissions_object_none_for_actor_at_or_above_threshold(data_fixture):
    """An Admin is at/above every threshold → nothing is restricted → ``None`` so the
    frontend manager defers and editing stays enabled."""

    owner, member, workspace, field = _setup(data_fixture, EDITOR)
    RbacHandler().assign_role(owner, workspace, ADMIN)
    FieldPermission.objects.create(field=field, editable_by_role=ADMIN)

    payload = FieldPermissionManagerType().get_permissions_object(owner, workspace)

    assert payload is None


@pytest.mark.django_db
def test_get_permissions_object_none_when_no_rules(data_fixture):
    """A workspace with zero ``FieldPermission`` rows yields ``None`` — no regression,
    the frontend manager defers everywhere."""

    owner, member, workspace, field = _setup(data_fixture, VIEWER)

    payload = FieldPermissionManagerType().get_permissions_object(member, workspace)

    assert payload is None

from django.db import IntegrityError

import pytest

from baserow.core.rbac.models import RoleAssignment
from baserow.core.rbac.roles import ADMIN, EDITOR, VIEWER


@pytest.mark.django_db
def test_create_workspace_scoped_role_assignment(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)

    assignment = RoleAssignment.objects.create(
        user=user, workspace=workspace, role=EDITOR
    )

    assert assignment.application_id is None
    assert assignment.role == EDITOR
    assert assignment.created_on is not None


@pytest.mark.django_db
def test_create_database_scoped_role_assignment(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)

    assignment = RoleAssignment.objects.create(
        user=user,
        workspace=workspace,
        application=database.application_ptr,
        role=VIEWER,
    )

    assert assignment.application_id == database.application_ptr.id
    assert assignment.role == VIEWER


@pytest.mark.django_db
def test_workspace_scope_uniqueness(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)

    RoleAssignment.objects.create(user=user, workspace=workspace, role=EDITOR)

    with pytest.raises(IntegrityError):
        RoleAssignment.objects.create(user=user, workspace=workspace, role=ADMIN)


@pytest.mark.django_db
def test_database_scope_uniqueness(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    application = database.application_ptr

    RoleAssignment.objects.create(
        user=user, workspace=workspace, application=application, role=EDITOR
    )

    with pytest.raises(IntegrityError):
        RoleAssignment.objects.create(
            user=user, workspace=workspace, application=application, role=VIEWER
        )


@pytest.mark.django_db
def test_workspace_and_database_scopes_coexist(data_fixture):
    """A workspace-scoped and a database-scoped assignment for the same user are
    distinct rows (the partial unique constraints do not collide)."""

    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)

    RoleAssignment.objects.create(user=user, workspace=workspace, role=EDITOR)
    RoleAssignment.objects.create(
        user=user,
        workspace=workspace,
        application=database.application_ptr,
        role=VIEWER,
    )

    assert RoleAssignment.objects.filter(user=user, workspace=workspace).count() == 2

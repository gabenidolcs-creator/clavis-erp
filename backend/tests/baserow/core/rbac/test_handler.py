import pytest

from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.models import RoleAssignment
from baserow.core.rbac.roles import ADMIN, EDITOR, VIEWER


@pytest.mark.django_db
def test_assign_role_creates_assignment(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)

    assignment = RbacHandler().assign_role(user, workspace, EDITOR)

    assert assignment.role == EDITOR
    assert RoleAssignment.objects.count() == 1


@pytest.mark.django_db
def test_assign_role_is_idempotent_update(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)

    RbacHandler().assign_role(user, workspace, EDITOR)
    updated = RbacHandler().assign_role(user, workspace, ADMIN)

    assert RoleAssignment.objects.count() == 1
    assert updated.role == ADMIN


@pytest.mark.django_db
def test_assign_role_rejects_unknown_role(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)

    with pytest.raises(ValueError):
        RbacHandler().assign_role(user, workspace, "SUPERUSER")


@pytest.mark.django_db
def test_assign_role_rejects_application_in_other_workspace(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    other_workspace = data_fixture.create_workspace(user=user)
    foreign_db = data_fixture.create_database_application(workspace=other_workspace)

    with pytest.raises(ValueError):
        RbacHandler().assign_role(
            user, workspace, VIEWER, application=foreign_db.application_ptr
        )
    assert RoleAssignment.objects.count() == 0


@pytest.mark.django_db
def test_get_effective_role_workspace_scope(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    RbacHandler().assign_role(user, workspace, EDITOR)

    assert RbacHandler().get_effective_role(user, workspace) == EDITOR


@pytest.mark.django_db
def test_get_effective_role_none_when_unassigned(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)

    assert RbacHandler().get_effective_role(user, workspace) is None


@pytest.mark.django_db
def test_most_specific_scope_wins(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    application = database.application_ptr

    RbacHandler().assign_role(user, workspace, EDITOR)
    RbacHandler().assign_role(user, workspace, VIEWER, application=application)

    # Database scope overrides workspace scope for that database.
    assert (
        RbacHandler().get_effective_role(user, workspace, application=application)
        == VIEWER
    )
    # Workspace scope still applies elsewhere.
    assert RbacHandler().get_effective_role(user, workspace) == EDITOR


@pytest.mark.django_db
def test_database_scope_falls_back_to_workspace(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)

    RbacHandler().assign_role(user, workspace, EDITOR)

    # No database-scoped assignment -> falls back to the workspace-scoped role.
    assert (
        RbacHandler().get_effective_role(
            user, workspace, application=database.application_ptr
        )
        == EDITOR
    )


@pytest.mark.django_db
def test_list_and_remove_role_assignments(data_fixture):
    user_a = data_fixture.create_user()
    user_b = data_fixture.create_user()
    workspace = data_fixture.create_workspace(users=[user_a, user_b])

    RbacHandler().assign_role(user_a, workspace, EDITOR)
    RbacHandler().assign_role(user_b, workspace, VIEWER)

    assert len(RbacHandler().list_role_assignments(workspace)) == 2

    RbacHandler().remove_role_assignment(user_a, workspace)

    remaining = RbacHandler().list_role_assignments(workspace)
    assert len(remaining) == 1
    assert remaining[0].user_id == user_b.id

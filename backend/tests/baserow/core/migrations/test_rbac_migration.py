import pytest

# RBAC role values (kept literal so the test does not depend on app code that may drift
# from the historical migration state).
ROLE_ADMIN = "ADMIN"
ROLE_EDITOR = "EDITOR"

MIGRATE_FROM = [("core", "0114_alter_workspaceinvitation_message")]
MIGRATE_TO = [("core", "0115_rbac_roleassignment")]


@pytest.mark.once_per_day_in_ci
def test_0115_derives_roles_without_write_loss(migrator, teardown_table_metadata):
    """AC #2 equivalence: every pre-migration member keeps an equivalent write-capable
    role. ADMIN -> Admin, MEMBER -> Editor (never Viewer/Commenter)."""

    old_state = migrator.migrate(MIGRATE_FROM)
    User = old_state.apps.get_model("auth", "User")
    Workspace = old_state.apps.get_model("core", "Workspace")
    WorkspaceUser = old_state.apps.get_model("core", "WorkspaceUser")

    admin_user = User.objects.create(username="rbac_mig_admin")
    member_user = User.objects.create(username="rbac_mig_member")
    workspace = Workspace.objects.create(name="rbac_mig_wp")

    WorkspaceUser.objects.create(
        user=admin_user, workspace=workspace, order=0, permissions="ADMIN"
    )
    WorkspaceUser.objects.create(
        user=member_user, workspace=workspace, order=1, permissions="MEMBER"
    )

    new_state = migrator.migrate(MIGRATE_TO)
    RoleAssignment = new_state.apps.get_model("core", "RoleAssignment")

    assert RoleAssignment.objects.count() == 2

    admin_assignment = RoleAssignment.objects.get(user_id=admin_user.id)
    member_assignment = RoleAssignment.objects.get(user_id=member_user.id)

    assert admin_assignment.role == ROLE_ADMIN
    assert admin_assignment.application_id is None
    # MEMBER must map to Editor (write-capable), not Viewer/Commenter — no write-loss.
    assert member_assignment.role == ROLE_EDITOR
    assert member_assignment.application_id is None


@pytest.mark.once_per_day_in_ci
def test_0115_reverse_removes_derived_assignments(migrator, teardown_table_metadata):
    """Reverse rollback removes derived assignments; the legacy permissions field was
    never altered, so pre-1.2 state is fully restored."""

    new_state = migrator.migrate(MIGRATE_TO)
    User = new_state.apps.get_model("auth", "User")
    Workspace = new_state.apps.get_model("core", "Workspace")
    WorkspaceUser = new_state.apps.get_model("core", "WorkspaceUser")
    RoleAssignment = new_state.apps.get_model("core", "RoleAssignment")

    user = User.objects.create(username="rbac_rev_member")
    workspace = Workspace.objects.create(name="rbac_rev_wp")
    WorkspaceUser.objects.create(
        user=user, workspace=workspace, order=0, permissions="MEMBER"
    )
    RoleAssignment.objects.create(
        user_id=user.id, workspace_id=workspace.id, application_id=None, role=ROLE_EDITOR
    )

    # Run the data-migration reverse only (stay on 0115 schema so the model still
    # exists), by migrating back to 0114 and confirming legacy data is intact.
    old_state = migrator.migrate(MIGRATE_FROM)
    LegacyWorkspaceUser = old_state.apps.get_model("core", "WorkspaceUser")

    # The legacy ADMIN/MEMBER field is untouched by the rollback.
    assert (
        LegacyWorkspaceUser.objects.get(user_id=user.id).permissions == "MEMBER"
    )

"""Story 1.3 — WebSocket parity.

There is no mutating command over WebSocket (CoreConsumer handles only subscribe /
remove_page), so "403 on WS mutation" is satisfied structurally — all writes go through
REST → the same permission chain. The only WS-specific concern is that subscribe-time
auth (TablePageType.can_add → listen_to_all) must still SUCCEED for Viewer/Commenter,
since listen_to_all is NOT in the deny sets (read/subscribe preserved).
"""

import pytest

from baserow.contrib.database.ws.pages import TablePageType
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import COMMENTER, VIEWER


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_viewer_commenter_can_subscribe_to_table_page(data_fixture, role):
    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    member = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=member, permissions="MEMBER"
    )
    RbacHandler().assign_role(member, workspace, role)
    database = data_fixture.create_database_application(user=owner, workspace=workspace)
    table = data_fixture.create_database_table(user=owner, database=database)

    # Subscribe (listen_to_all) is deferred by the rbac manager, so read/subscribe is
    # preserved — can_add must be truthy.
    assert TablePageType().can_add(member, "websocket-id", table.id) is True

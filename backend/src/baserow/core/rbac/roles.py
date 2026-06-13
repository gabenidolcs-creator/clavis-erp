"""Fixed-tier RBAC roles, defined as code constants (no DB-driven role table).

Capability ordering (most to least capable): ``Admin > Editor > Commenter > Viewer``.
This is a *fixed* hierarchy — the custom-role builder is explicitly out of scope
(FR-29). Roles are layered above the legacy ADMIN/MEMBER ``WorkspaceUser.permissions``
field and never replace it.
"""

# Role tier constants. These are RBAC role values stored on ``RoleAssignment.role`` and
# are distinct from the legacy ``WorkspaceUser.permissions`` ADMIN/MEMBER strings.
VIEWER = "VIEWER"
COMMENTER = "COMMENTER"
EDITOR = "EDITOR"
ADMIN = "ADMIN"

# Interface-only is NOT a capability tier — it is orthogonal to the
# VIEWER→COMMENTER→EDITOR→ADMIN ladder. It is absent from ROLE_ORDER so that
# role_rank() and role_at_least() remain correct for the 4-tier ordering.
INTERFACE_ONLY = "INTERFACE_ONLY"

# Ordered from least to most capable. Index in this list == capability rank.
# DO NOT add INTERFACE_ONLY here.
ROLE_ORDER = [VIEWER, COMMENTER, EDITOR, ADMIN]

ROLE_CHOICES = [
    (VIEWER, "Viewer"),
    (COMMENTER, "Commenter"),
    (EDITOR, "Editor"),
    (ADMIN, "Admin"),
    (INTERFACE_ONLY, "Interface Collaborator"),
]

ALL_ROLES = [VIEWER, COMMENTER, EDITOR, ADMIN, INTERFACE_ONLY]


def is_valid_role(role: str) -> bool:
    """Whether ``role`` is one of the known roles (including interface-only)."""

    return role in ALL_ROLES


def role_rank(role: str) -> int:
    """Capability rank of ``role`` (higher == more capable).

    :raises ValueError: if ``role`` is not a known fixed tier.
    """

    try:
        return ROLE_ORDER.index(role)
    except ValueError as exc:
        raise ValueError(f"Unknown role: {role!r}") from exc


def role_at_least(role: str, minimum: str) -> bool:
    """Whether ``role`` is at least as capable as ``minimum``."""

    return role_rank(role) >= role_rank(minimum)

"""Clean-room RBAC role layer (Story 1.2, Bucket A).

Fixed-tier role hierarchy (Viewer / Commenter / Editor / Admin) layered *above* the
legacy ``WorkspaceUser.permissions`` (ADMIN/MEMBER) field. This is a clean-room
reimplementation; it does not copy or adapt any premium/enterprise source.

See ``docs/clean-room/specs/1-2-rbac-role-model.md`` and the provenance record
``docs/clean-room/provenance/1-2-rbac-role-model-and-migration.md``.
"""

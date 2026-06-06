import abc

from baserow.contrib.database.table.operations import DatabaseTableOperationType
from baserow.core.registries import OperationType


class FieldOperationType(OperationType, abc.ABC):
    context_scope_name = "database_field"


class CreateFieldOperationType(DatabaseTableOperationType):
    type = "database.table.create_field"


class ListFieldsOperationType(DatabaseTableOperationType):
    type = "database.table.list_fields"
    object_scope_name = "database_field"


class ReadFieldOperationType(FieldOperationType):
    type = "database.table.field.read"


class UpdateFieldOperationType(FieldOperationType):
    type = "database.table.field.update"


class DeleteFieldOperationType(FieldOperationType):
    type = "database.table.field.delete"


class DeleteRelatedLinkRowFieldOperationType(DatabaseTableOperationType):
    type = "database.table.field.delete_related_link_row_field"


class RestoreFieldOperationType(FieldOperationType):
    type = "database.table.field.restore"


class DuplicateFieldOperationType(FieldOperationType):
    type = "database.table.field.duplicate"


class WriteFieldValuesOperationType(FieldOperationType):
    type = "database.table.field.write_values"


class SubmitAnonymousFieldValuesOperationType(FieldOperationType):
    type = "database.table.field.submit_anonymous_values"


class UpdateFieldPermissionOperationType(FieldOperationType):
    """Story 1.4: managing a field's edit-restriction rule. Admin-only — its ``type``
    string is added to ``BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS`` so only the
    Admin tier may set/change the threshold."""

    type = "database.table.field.update_permission"

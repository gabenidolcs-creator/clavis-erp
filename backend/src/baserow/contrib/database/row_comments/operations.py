from baserow.contrib.database.table.operations import DatabaseTableOperationType


class RowCommentListOperationType(DatabaseTableOperationType):
    type = "database.table.row_comment.list"


class RowCommentCreateOperationType(DatabaseTableOperationType):
    type = "database.table.row_comment.create"


class RowCommentUpdateOperationType(DatabaseTableOperationType):
    type = "database.table.row_comment.update"


class RowCommentDeleteOperationType(DatabaseTableOperationType):
    type = "database.table.row_comment.delete"

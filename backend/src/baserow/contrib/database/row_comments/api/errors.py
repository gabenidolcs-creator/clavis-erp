from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

ERROR_ROW_COMMENT_DOES_NOT_EXIST = (
    "ERROR_ROW_COMMENT_DOES_NOT_EXIST",
    HTTP_404_NOT_FOUND,
    "The requested comment does not exist.",
)

ERROR_ROW_COMMENT_NOT_OWNED_BY_USER = (
    "ERROR_ROW_COMMENT_NOT_OWNED_BY_USER",
    HTTP_403_FORBIDDEN,
    "You can only modify your own comments unless you are an Admin.",
)

ERROR_INVALID_MENTION = (
    "ERROR_INVALID_MENTION",
    HTTP_400_BAD_REQUEST,
    "The @mention targets user {e.user_id} who does not have access to this row.",
)

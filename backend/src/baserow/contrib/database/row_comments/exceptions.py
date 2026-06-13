class RowCommentDoesNotExist(Exception):
    """Raised when trying to get a comment that doesn't exist."""


class RowCommentNotOwnedByUser(Exception):
    """Raised when a non-admin tries to modify another user's comment."""


class RowCommentMentionAccessError(Exception):
    """Raised when an @mention targets a user who cannot access the row."""

    def __init__(self, user_id=None, *args, **kwargs):
        self.user_id = user_id
        super().__init__(*args, **kwargs)

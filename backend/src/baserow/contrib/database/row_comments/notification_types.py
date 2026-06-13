from django.utils.translation import gettext as _

from baserow.core.notifications.registries import (
    EmailNotificationTypeMixin,
    NotificationType,
)


class RowCommentMentionNotificationType(EmailNotificationTypeMixin, NotificationType):
    type = "row_comment_mention"
    has_web_frontend_route = True

    @classmethod
    def get_notification_title_for_email(cls, notification, context):
        sender_name = (
            notification.sender.first_name
            if notification.sender
            else _("An unknown user")
        )
        return _("%(sender)s mentioned you in a comment on row %(row_id)s.") % {
            "sender": sender_name,
            "row_id": notification.data.get("row_id", ""),
        }

    @classmethod
    def get_notification_description_for_email(cls, notification, context):
        return notification.data.get("comment_preview", "")

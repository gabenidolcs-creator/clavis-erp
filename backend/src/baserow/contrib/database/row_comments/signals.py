import django.dispatch

row_comment_created = django.dispatch.Signal()
row_comment_updated = django.dispatch.Signal()
row_comment_deleted = django.dispatch.Signal()

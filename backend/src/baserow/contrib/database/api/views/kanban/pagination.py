from rest_framework.pagination import LimitOffsetPagination


class KanbanLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 100

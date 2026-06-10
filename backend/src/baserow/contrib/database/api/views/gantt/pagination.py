from rest_framework.pagination import LimitOffsetPagination


class GanttLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 100

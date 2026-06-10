from rest_framework.pagination import LimitOffsetPagination


class TimelineLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 100

from rest_framework.pagination import LimitOffsetPagination


class CalendarLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 100

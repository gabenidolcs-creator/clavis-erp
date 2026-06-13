from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from baserow.api.decorators import map_exceptions, validate_body
from baserow.api.errors import ERROR_PERMISSION_DENIED, ERROR_USER_NOT_IN_GROUP
from baserow.api.pagination import PageNumberPagination
from baserow.contrib.database.api.tables.errors import ERROR_TABLE_DOES_NOT_EXIST
from baserow.contrib.database.row_comments.api.errors import (
    ERROR_INVALID_MENTION,
    ERROR_ROW_COMMENT_DOES_NOT_EXIST,
    ERROR_ROW_COMMENT_NOT_OWNED_BY_USER,
)
from baserow.contrib.database.row_comments.api.serializers import (
    CreateRowCommentSerializer,
    RowCommentSerializer,
    UpdateRowCommentSerializer,
)
from baserow.contrib.database.row_comments.exceptions import (
    RowCommentDoesNotExist,
    RowCommentMentionAccessError,
    RowCommentNotOwnedByUser,
)
from baserow.contrib.database.row_comments.handler import RowCommentHandler
from baserow.contrib.database.table.exceptions import TableDoesNotExist
from baserow.core.exceptions import PermissionDenied, UserNotInWorkspace


class RowCommentsView(APIView):
    permission_classes = (IsAuthenticated,)

    @map_exceptions(
        {
            TableDoesNotExist: ERROR_TABLE_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            PermissionDenied: ERROR_PERMISSION_DENIED,
        }
    )
    def get(self, request: Request, table_id: int, row_id: int) -> Response:
        queryset = RowCommentHandler.get_comments(request.user, table_id, row_id)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, self)
        serializer = RowCommentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @map_exceptions(
        {
            TableDoesNotExist: ERROR_TABLE_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            PermissionDenied: ERROR_PERMISSION_DENIED,
            RowCommentMentionAccessError: ERROR_INVALID_MENTION,
        }
    )
    @validate_body(CreateRowCommentSerializer)
    def post(
        self, request: Request, table_id: int, row_id: int, data: dict
    ) -> Response:
        comment = RowCommentHandler.create_comment(
            request.user, table_id, row_id, data["message"]
        )
        return Response(RowCommentSerializer(comment).data, status=HTTP_201_CREATED)


class RowCommentView(APIView):
    permission_classes = (IsAuthenticated,)

    @map_exceptions(
        {
            RowCommentDoesNotExist: ERROR_ROW_COMMENT_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            PermissionDenied: ERROR_PERMISSION_DENIED,
            RowCommentNotOwnedByUser: ERROR_ROW_COMMENT_NOT_OWNED_BY_USER,
        }
    )
    @validate_body(UpdateRowCommentSerializer)
    def patch(
        self,
        request: Request,
        table_id: int,
        row_id: int,
        comment_id: int,
        data: dict,
    ) -> Response:
        comment = RowCommentHandler.update_comment(
            request.user, comment_id, data["message"]
        )
        return Response(RowCommentSerializer(comment).data)

    @map_exceptions(
        {
            RowCommentDoesNotExist: ERROR_ROW_COMMENT_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            PermissionDenied: ERROR_PERMISSION_DENIED,
            RowCommentNotOwnedByUser: ERROR_ROW_COMMENT_NOT_OWNED_BY_USER,
        }
    )
    def delete(
        self, request: Request, table_id: int, row_id: int, comment_id: int
    ) -> Response:
        RowCommentHandler.delete_comment(request.user, comment_id)
        return Response(status=HTTP_204_NO_CONTENT)

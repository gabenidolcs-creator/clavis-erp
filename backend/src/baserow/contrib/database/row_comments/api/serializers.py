from rest_framework import serializers

from baserow.contrib.database.row_comments.models import RowComment


class RowCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = RowComment
        fields = ["id", "author", "message", "created_on", "updated_on"]
        read_only_fields = ["id", "author", "created_on", "updated_on"]

    def get_author(self, obj):
        user = obj.user
        if user is None:
            return {"id": None, "name": ""}
        return {
            "id": user.id,
            "name": getattr(user, "first_name", "") or str(user),
        }


class CreateRowCommentSerializer(serializers.Serializer):
    message = serializers.JSONField()


class UpdateRowCommentSerializer(serializers.Serializer):
    message = serializers.JSONField()

from rest_framework import serializers

from baserow.contrib.database.views.gantt.models import TaskDependency
from baserow.contrib.database.views.models import GanttViewFieldOptions


class GanttViewFieldOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GanttViewFieldOptions
        fields = ("hidden", "order")


class TaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDependency
        fields = (
            "id",
            "table",
            "predecessor_row_id",
            "successor_row_id",
            "dependency_type",
        )


class CreateTaskDependencySerializer(serializers.Serializer):
    predecessor_row_id = serializers.IntegerField(
        min_value=1,
        help_text="The id of the row that must come first (the predecessor).",
    )
    successor_row_id = serializers.IntegerField(
        min_value=1,
        help_text="The id of the dependent row that comes after (the successor).",
    )
    dependency_type = serializers.ChoiceField(
        choices=["FS"],
        default="FS",
        required=False,
        help_text="The dependency type. Only FS (finish-to-start) is supported.",
    )

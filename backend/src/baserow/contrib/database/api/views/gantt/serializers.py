from rest_framework import serializers

from baserow.contrib.database.views.gantt.models import TaskDependency
from baserow.contrib.database.views.models import GanttViewFieldOptions


class GanttViewFieldOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GanttViewFieldOptions
        fields = ("hidden", "order")


class TaskDependencySerializer(serializers.ModelSerializer):
    violated = serializers.SerializerMethodField(
        help_text="Whether this FS edge is currently violated, i.e. the "
        "successor starts before the predecessor finishes. Derived at read "
        "time from the rows' dates — not a persisted column. The connector "
        "renders in a conflict style when true (Story 3.10 / AC #3)."
    )

    class Meta:
        model = TaskDependency
        fields = (
            "id",
            "table",
            "predecessor_row_id",
            "successor_row_id",
            "dependency_type",
            "violated",
        )

    def get_violated(self, instance) -> bool:
        # The view computes the violated edge set once (one date read for the
        # whole table) and passes it in via context, so the serializer does not
        # re-derive date math per edge.
        violated_edges = self.context.get("violated_edges")
        if not violated_edges:
            return False
        return (
            instance.predecessor_row_id,
            instance.successor_row_id,
        ) in violated_edges


class RescheduleCascadePreviewRequestSerializer(serializers.Serializer):
    predecessor_row_id = serializers.IntegerField(
        min_value=1,
        help_text="The id of the moved predecessor row whose new dates trigger "
        "the cascade.",
    )
    new_start = serializers.CharField(
        allow_null=True,
        help_text="The predecessor's new start date (ISO `YYYY-MM-DD` for a "
        "date-only field, or an ISO timestamp for a datetime field).",
    )
    new_end = serializers.CharField(
        allow_null=True,
        help_text="The predecessor's new end date in the same ISO shape as "
        "`new_start`.",
    )


class CascadeAffectedSuccessorSerializer(serializers.Serializer):
    row_id = serializers.IntegerField()
    current_start = serializers.CharField(allow_null=True)
    current_end = serializers.CharField(allow_null=True)
    new_start = serializers.CharField(allow_null=True)
    new_end = serializers.CharField(allow_null=True)


class RescheduleCascadePreviewResponseSerializer(serializers.Serializer):
    affected_successors = CascadeAffectedSuccessorSerializer(many=True)
    cascade_count = serializers.IntegerField(
        help_text="The transitive count of dependents that would shift — the "
        "full downstream FS chain, computed before the prompt (AC #1)."
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

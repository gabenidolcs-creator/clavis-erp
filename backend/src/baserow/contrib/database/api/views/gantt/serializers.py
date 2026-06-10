from rest_framework import serializers

from baserow.contrib.database.views.models import GanttViewFieldOptions


class GanttViewFieldOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GanttViewFieldOptions
        fields = ("hidden", "order")

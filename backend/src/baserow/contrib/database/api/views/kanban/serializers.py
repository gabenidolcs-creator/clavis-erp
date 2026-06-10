from rest_framework import serializers

from baserow.contrib.database.views.models import KanbanViewFieldOptions


class KanbanViewFieldOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = KanbanViewFieldOptions
        fields = ("hidden", "order")

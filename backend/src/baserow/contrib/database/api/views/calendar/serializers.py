from rest_framework import serializers

from baserow.contrib.database.views.models import CalendarViewFieldOptions


class CalendarViewFieldOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarViewFieldOptions
        fields = ("hidden", "order")

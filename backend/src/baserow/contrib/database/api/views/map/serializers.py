from rest_framework import serializers

from baserow.contrib.database.views.models import MapViewFieldOptions


class MapViewFieldOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapViewFieldOptions
        fields = ("hidden", "order")


class MapViewPinSerializer(serializers.Serializer):
    row_id = serializers.IntegerField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class MapViewUnresolvableSerializer(serializers.Serializer):
    row_id = serializers.IntegerField()


class MapViewRowsResponseSerializer(serializers.Serializer):
    pins = MapViewPinSerializer(many=True)
    unresolvable = MapViewUnresolvableSerializer(many=True)

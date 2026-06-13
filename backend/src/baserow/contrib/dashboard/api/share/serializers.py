from rest_framework import serializers

from baserow.contrib.dashboard.models import Dashboard


class DashboardShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ("public", "slug")
        read_only_fields = ("public", "slug")


class DashboardPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ("id", "name", "description")
        read_only_fields = ("id", "name", "description")

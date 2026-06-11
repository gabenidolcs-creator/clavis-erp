import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GeocodedAddress",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "address_hash",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                (
                    "latitude",
                    models.DecimalField(decimal_places=6, max_digits=9),
                ),
                (
                    "longitude",
                    models.DecimalField(decimal_places=6, max_digits=9),
                ),
                ("provider", models.CharField(max_length=32)),
                (
                    "created_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "app_label": "geocoding",
            },
        ),
    ]

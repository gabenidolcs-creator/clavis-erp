# Generated for Story 1.8: Password-Protected Share Links (FR-17)

from django.db import migrations, models


class Migration(migrations.Migration):
    """Story 1.8: increase max_length of public_view_password from 128 to 256.

    Django's Argon2PasswordHasher default params produce ~106 char encoded strings.
    Increasing to 256 provides a safety margin for any future work-factor tuning.
    No data migration needed — existing PBKDF2 hashes remain valid and verifiable.
    """

    dependencies = [
        ("database", "0214_view_locked"),
    ]

    operations = [
        migrations.AlterField(
            model_name="view",
            name="public_view_password",
            field=models.CharField(
                blank=True,
                help_text="The password required to access the public view URL.",
                max_length=256,
            ),
        ),
    ]

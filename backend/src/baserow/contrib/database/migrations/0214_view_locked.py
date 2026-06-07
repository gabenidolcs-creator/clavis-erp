# Generated for Story 1.7: Locked Views (FR-32)

from django.db import migrations, models


class Migration(migrations.Migration):
    """Story 1.7: add the ``locked`` flag to the ``View`` model.

    When True, view configuration (filters, sorts, field options, decorations,
    group-bys, layout) is read-only for users other than the lock owner and
    workspace admins. Data within the view (rows) remains editable per Role.
    Lock owner is stored in the existing ``owned_by`` FK (``created_by_id``
    column). No new FK needed.
    """

    dependencies = [
        ("database", "0213_fieldpermission_readable_by_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="view",
            name="locked",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "When True, view configuration (filters, sorts, field options) is "
                    "read-only for users other than the lock owner and workspace admins."
                ),
            ),
        ),
    ]

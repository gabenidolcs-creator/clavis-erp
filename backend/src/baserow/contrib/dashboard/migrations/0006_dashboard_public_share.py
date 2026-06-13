import secrets

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0005_chartwidget_line_scatter"),
    ]

    operations = [
        migrations.AddField(
            model_name="dashboard",
            name="slug",
            field=models.SlugField(
                default=secrets.token_urlsafe, max_length=64, unique=True
            ),
        ),
        migrations.AddField(
            model_name="dashboard",
            name="public",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]

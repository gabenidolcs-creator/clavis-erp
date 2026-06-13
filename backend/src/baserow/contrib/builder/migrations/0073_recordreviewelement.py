import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('builder', '0072_viewembedelement'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecordReviewElement',
            fields=[
                ('element_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='builder.element')),
                ('data_source', models.ForeignKey(blank=True, help_text='Builder data source providing rows for record-review navigation.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='builder.datasource')),
            ],
            options={
                'abstract': False,
            },
            bases=('builder.element',),
        ),
    ]

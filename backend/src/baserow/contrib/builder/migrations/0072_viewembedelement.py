import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('builder', '0071_metricelement'),
        ('database', '0225_mapview_mapviewfieldoptions'),
    ]

    operations = [
        migrations.CreateModel(
            name='ViewEmbedElement',
            fields=[
                ('element_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='builder.element')),
                ('view', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='builder_embeds', to='database.view')),
            ],
            options={
                'abstract': False,
            },
            bases=('builder.element',),
        ),
    ]

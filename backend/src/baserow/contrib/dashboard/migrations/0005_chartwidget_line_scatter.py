from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_chartwidget'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chartwidget',
            name='chart_type',
            field=models.CharField(
                choices=[
                    ('bar', 'Bar'),
                    ('pie', 'Pie'),
                    ('doughnut', 'Doughnut'),
                    ('line', 'Line'),
                    ('scatter', 'Scatter'),
                ],
                default='bar',
                max_length=32,
            ),
        ),
    ]

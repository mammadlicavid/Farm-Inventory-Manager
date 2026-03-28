from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='additional_info',
            field=models.TextField(blank=True, default='', verbose_name='Əlavə Məlumat'),
        ),
    ]

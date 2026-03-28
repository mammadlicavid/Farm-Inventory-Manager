from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0002_supplier_additional_info'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='supplier',
            name='is_favorite',
        ),
    ]

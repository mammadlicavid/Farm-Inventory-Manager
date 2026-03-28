from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0003_remove_supplier_is_favorite'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='supplier',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Təchizatçı',
                'verbose_name_plural': 'Təchizatçılar',
            },
        ),
    ]

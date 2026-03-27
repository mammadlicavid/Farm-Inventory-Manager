from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0004_alter_supplier_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplier',
            name='last_order_date',
            field=models.DateField(blank=True, null=True, verbose_name='Son Sifariş Tarixi'),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='location',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Ünvan'),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Telefon Nömrəsi'),
        ),
    ]

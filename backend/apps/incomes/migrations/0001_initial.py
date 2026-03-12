from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Income',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=120, verbose_name='Kateqoriya')),
                ('item_name', models.CharField(max_length=120, verbose_name='Məhsul adı')),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Miqdar')),
                ('unit', models.CharField(choices=[('kq', 'kq'), ('ton', 'ton'), ('qram', 'qram'), ('litr', 'litr'), ('ml', 'ml'), ('ədəd', 'ədəd'), ('dəstə', 'dəstə'), ('bağlama', 'bağlama')], max_length=20, verbose_name='Ölçü vahidi')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Məbləğ')),
                ('gender', models.CharField(blank=True, choices=[('erkek', 'Erkək'), ('disi', 'Dişi')], max_length=10, null=True, verbose_name='Cinsiyyət')),
                ('additional_info', models.TextField(blank=True, null=True, verbose_name='Əlavə məlumat')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='Tarix')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='incomes_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Gəlir',
                'verbose_name_plural': 'Gəlirlər',
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]

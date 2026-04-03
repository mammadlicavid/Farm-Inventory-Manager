from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_stockalertrule"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="is_system_generated",
            field=models.BooleanField(default=False, verbose_name="Sistem tərəfindən yaradılıb"),
        ),
        migrations.AddField(
            model_name="notification",
            name="source_key",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="Mənbə açarı"),
        ),
        migrations.AlterField(
            model_name="notification",
            name="category",
            field=models.CharField(
                choices=[
                    ("vaksinasiya", "Vaksinasiya"),
                    ("odenis", "Ödəniş"),
                    ("ekin", "Əkin"),
                    ("ehtiyat", "Ehtiyat"),
                    ("diger", "Digər"),
                ],
                default="diger",
                max_length=20,
                verbose_name="Kateqoriya",
            ),
        ),
    ]

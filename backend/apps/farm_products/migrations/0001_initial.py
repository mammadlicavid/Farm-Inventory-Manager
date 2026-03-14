from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FarmProductCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Kateqoriya Adı")),
            ],
            options={
                "verbose_name": "Təsərrüfat Məhsulu Kateqoriyası",
                "verbose_name_plural": "Təsərrüfat Məhsulu Kateqoriyaları",
            },
        ),
        migrations.CreateModel(
            name="FarmProductItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Məhsul Adı")),
                (
                    "unit",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("kq", "kq"),
                            ("litr", "litr"),
                            ("ədəd", "ədəd"),
                            ("dəstə", "dəstə"),
                            ("bağlama", "bağlama"),
                            ("kq / bağlama", "kq / bağlama"),
                        ],
                        max_length=20,
                        null=True,
                        verbose_name="Ölçü Vahidi",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="farm_products.farmproductcategory",
                        verbose_name="Ana Kateqoriya",
                    ),
                ),
            ],
            options={
                "verbose_name": "Təsərrüfat Məhsulu Növü",
                "verbose_name_plural": "Təsərrüfat Məhsulu Növləri",
            },
        ),
        migrations.CreateModel(
            name="FarmProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("manual_name", models.CharField(blank=True, max_length=120, null=True, verbose_name="Xüsusi Ad")),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Miqdar")),
                (
                    "unit",
                    models.CharField(
                        choices=[
                            ("kq", "kq"),
                            ("litr", "litr"),
                            ("ədəd", "ədəd"),
                            ("dəstə", "dəstə"),
                            ("bağlama", "bağlama"),
                            ("kq / bağlama", "kq / bağlama"),
                        ],
                        max_length=20,
                        verbose_name="Ölçü Vahidi",
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=0,
                        max_digits=10,
                        null=True,
                        verbose_name="Qiymət",
                    ),
                ),
                (
                    "additional_info",
                    models.TextField(blank=True, null=True, verbose_name="Əlavə məlumat"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventory",
                        to="farm_products.farmproductitem",
                        verbose_name="Məhsul",
                    ),
                ),
            ],
            options={
                "verbose_name": "Təsərrüfat Məhsulu",
                "verbose_name_plural": "Təsərrüfat Məhsulları",
                "ordering": ["-created_at"],
            },
        ),
    ]

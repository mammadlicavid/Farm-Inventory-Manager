from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StockAlertRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("seed", "Toxum"), ("tool", "Alət"), ("farm", "Təsərrüfat məhsulu")], max_length=20)),
                ("item_key", models.CharField(max_length=255, verbose_name="Məhsul açarı")),
                ("item_name", models.CharField(max_length=255, verbose_name="Məhsul adı")),
                ("unit", models.CharField(blank=True, max_length=20, verbose_name="Ölçü vahidi")),
                ("threshold", models.DecimalField(decimal_places=4, max_digits=10, verbose_name="Xəbərdarlıq həddi")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktivdir")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_alert_rules",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Ehtiyat xəbərdarlıq qaydası",
                "verbose_name_plural": "Ehtiyat xəbərdarlıq qaydaları",
                "ordering": ["item_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="stockalertrule",
            constraint=models.UniqueConstraint(
                fields=("created_by", "item_key"),
                name="notifications_unique_stock_alert_rule_per_user",
            ),
        ),
    ]

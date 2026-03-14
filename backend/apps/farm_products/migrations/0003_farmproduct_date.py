from django.db import migrations, models
import django.utils.timezone


def _backfill_farmproduct_date(apps, schema_editor):
    FarmProduct = apps.get_model("farm_products", "FarmProduct")
    for product in FarmProduct.objects.all().only("id", "created_at", "date"):
        if product.created_at:
            product.date = product.created_at.date()
            product.save(update_fields=["date"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("farm_products", "0002_alter_farmproduct_unit_alter_farmproductitem_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmproduct",
            name="date",
            field=models.DateField(default=django.utils.timezone.now, verbose_name="Tarix"),
        ),
        migrations.RunPython(_backfill_farmproduct_date, _noop),
    ]

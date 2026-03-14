from django.db import migrations, models
import django.utils.timezone


def _backfill_seed_date(apps, schema_editor):
    Seed = apps.get_model("seeds", "Seed")
    for seed in Seed.objects.all().only("id", "created_at", "date"):
        if seed.created_at:
            seed.date = seed.created_at.date()
            seed.save(update_fields=["date"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("seeds", "0005_alter_seed_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="seed",
            name="date",
            field=models.DateField(default=django.utils.timezone.now, verbose_name="Tarix"),
        ),
        migrations.RunPython(_backfill_seed_date, _noop),
    ]

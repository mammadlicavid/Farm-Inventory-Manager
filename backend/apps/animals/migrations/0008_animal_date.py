from django.db import migrations, models
import django.utils.timezone


def _backfill_animal_date(apps, schema_editor):
    Animal = apps.get_model("animals", "Animal")
    for animal in Animal.objects.all().only("id", "created_at", "date"):
        if animal.created_at:
            animal.date = animal.created_at.date()
            animal.save(update_fields=["date"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("animals", "0007_alter_animal_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="animal",
            name="date",
            field=models.DateField(default=django.utils.timezone.now, verbose_name="Tarix"),
        ),
        migrations.RunPython(_backfill_animal_date, _noop),
    ]

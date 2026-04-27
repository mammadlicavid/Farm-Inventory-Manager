from django.db import migrations, models


def backfill_units(apps, schema_editor):
    UserSettings = apps.get_model("sidebar_menu", "UserSettings")
    for settings_obj in UserSettings.objects.all():
        # If DB already enforces NOT NULL, these should exist,
        # but we keep this defensive to heal any legacy rows.
        changed = False
        if not getattr(settings_obj, "weight_unit", None):
            settings_obj.weight_unit = "kg"
            changed = True
        if not getattr(settings_obj, "volume_unit", None):
            settings_obj.volume_unit = "litr"
            changed = True

        unit_value = (getattr(settings_obj, "unit", "") or "").strip()
        if "_" in unit_value:
            w, v = unit_value.split("_", 1)
            w = (w or "").strip()
            v = (v or "").strip()
            if w in {"kg", "lb"} and settings_obj.weight_unit != w:
                settings_obj.weight_unit = w
                changed = True
            if v in {"litr", "gallon"} and settings_obj.volume_unit != v:
                settings_obj.volume_unit = v
                changed = True

        if changed:
            settings_obj.save(update_fields=["weight_unit", "volume_unit"])


class Migration(migrations.Migration):
    dependencies = [
        ("sidebar_menu", "0004_alter_usersettings_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersettings",
            name="volume_unit",
            field=models.CharField(
                choices=[("litr", "litr"), ("gallon", "gallon")],
                default="litr",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="usersettings",
            name="weight_unit",
            field=models.CharField(
                choices=[("kg", "kq"), ("lb", "pound")],
                default="kg",
                max_length=10,
            ),
        ),
        migrations.RunPython(backfill_units, migrations.RunPython.noop),
    ]

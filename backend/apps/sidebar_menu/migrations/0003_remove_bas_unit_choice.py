from django.db import migrations, models


def migrate_bas_to_kg(apps, schema_editor):
    UserSettings = apps.get_model("sidebar_menu", "UserSettings")
    UserSettings.objects.filter(unit="bas").update(unit="kg")


class Migration(migrations.Migration):

    dependencies = [
        ("sidebar_menu", "0002_remove_usersettings_theme_usersettings_currency_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_bas_to_kg, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="usersettings",
            name="unit",
            field=models.CharField(
                choices=[("kg", "kg"), ("litr", "litr")],
                default="kg",
                max_length=10,
            ),
        ),
    ]

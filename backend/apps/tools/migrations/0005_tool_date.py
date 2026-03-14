from django.db import migrations, models
import django.utils.timezone


def _backfill_tool_date(apps, schema_editor):
    Tool = apps.get_model("tools", "Tool")
    for tool in Tool.objects.all().only("id", "created_at", "date"):
        if tool.created_at:
            tool.date = tool.created_at.date()
            tool.save(update_fields=["date"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tools", "0004_tool_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="tool",
            name="date",
            field=models.DateField(default=django.utils.timezone.now, verbose_name="Tarix"),
        ),
        migrations.RunPython(_backfill_tool_date, _noop),
    ]

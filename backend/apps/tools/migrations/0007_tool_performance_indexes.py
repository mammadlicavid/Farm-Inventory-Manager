from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tools", "0006_alter_tool_options"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="tool",
            index=models.Index(fields=["created_by", "item"], name="tools_tool_created_8cfec7_idx"),
        ),
        migrations.AddIndex(
            model_name="tool",
            index=models.Index(fields=["created_by", "manual_name"], name="tools_tool_created_087153_idx"),
        ),
        migrations.AddIndex(
            model_name="tool",
            index=models.Index(fields=["created_by", "date"], name="tools_tool_created_760bc8_idx"),
        ),
        migrations.AddIndex(
            model_name="tool",
            index=models.Index(fields=["created_by", "updated_at"], name="tools_tool_created_4f8fde_idx"),
        ),
    ]

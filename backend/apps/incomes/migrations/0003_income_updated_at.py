from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("incomes", "0002_income_content_type_object_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="income",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]

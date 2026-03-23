from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0005_expense_content_type_expense_object_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]

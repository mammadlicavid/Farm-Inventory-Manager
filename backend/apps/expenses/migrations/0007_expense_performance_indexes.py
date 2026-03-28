from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0006_expense_updated_at"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["created_by", "subcategory"], name="expenses_ex_created_ead3ca_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["created_by", "manual_name"], name="expenses_ex_created_fc6c10_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["created_by", "date"], name="expenses_ex_created_e20584_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["created_by", "updated_at"], name="expenses_ex_created_6fd6f7_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["content_type", "object_id"], name="expenses_ex_content_835246_idx"),
        ),
    ]

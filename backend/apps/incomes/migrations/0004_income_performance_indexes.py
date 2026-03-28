from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("incomes", "0003_income_updated_at"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="income",
            index=models.Index(fields=["created_by", "category"], name="incomes_inc_created_31f95c_idx"),
        ),
        migrations.AddIndex(
            model_name="income",
            index=models.Index(fields=["created_by", "item_name"], name="incomes_inc_created_9dd1c1_idx"),
        ),
        migrations.AddIndex(
            model_name="income",
            index=models.Index(fields=["created_by", "date"], name="incomes_inc_created_3d4123_idx"),
        ),
        migrations.AddIndex(
            model_name="income",
            index=models.Index(fields=["created_by", "updated_at"], name="incomes_inc_created_35f249_idx"),
        ),
        migrations.AddIndex(
            model_name="income",
            index=models.Index(fields=["content_type", "object_id"], name="incomes_inc_content_c31f56_idx"),
        ),
    ]

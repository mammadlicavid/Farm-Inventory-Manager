from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seeds", "0007_alter_seed_options"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="seed",
            index=models.Index(fields=["created_by", "item"], name="seeds_seed_created_ca8e2a_idx"),
        ),
        migrations.AddIndex(
            model_name="seed",
            index=models.Index(fields=["created_by", "manual_name"], name="seeds_seed_created_31c50b_idx"),
        ),
        migrations.AddIndex(
            model_name="seed",
            index=models.Index(fields=["created_by", "date"], name="seeds_seed_created_f263c1_idx"),
        ),
        migrations.AddIndex(
            model_name="seed",
            index=models.Index(fields=["created_by", "updated_at"], name="seeds_seed_created_95588b_idx"),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("farm_products", "0004_alter_farmproduct_options"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="farmproduct",
            index=models.Index(fields=["created_by", "item"], name="farm_produc_created_f970e5_idx"),
        ),
        migrations.AddIndex(
            model_name="farmproduct",
            index=models.Index(fields=["created_by", "manual_name"], name="farm_produc_created_1bbc66_idx"),
        ),
        migrations.AddIndex(
            model_name="farmproduct",
            index=models.Index(fields=["created_by", "unit"], name="farm_produc_created_322675_idx"),
        ),
        migrations.AddIndex(
            model_name="farmproduct",
            index=models.Index(fields=["created_by", "date"], name="farm_produc_created_cf6ab6_idx"),
        ),
        migrations.AddIndex(
            model_name="farmproduct",
            index=models.Index(fields=["created_by", "updated_at"], name="farm_produc_created_24d89e_idx"),
        ),
    ]

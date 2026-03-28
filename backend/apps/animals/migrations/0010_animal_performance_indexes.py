from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("animals", "0009_alter_animal_options"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="animal",
            index=models.Index(fields=["created_by", "subcategory"], name="animals_an_created_55e49e_idx"),
        ),
        migrations.AddIndex(
            model_name="animal",
            index=models.Index(fields=["created_by", "manual_name"], name="animals_an_created_5cf02c_idx"),
        ),
        migrations.AddIndex(
            model_name="animal",
            index=models.Index(fields=["created_by", "gender"], name="animals_an_created_f0e7bc_idx"),
        ),
        migrations.AddIndex(
            model_name="animal",
            index=models.Index(fields=["created_by", "date"], name="animals_an_created_8f5bf6_idx"),
        ),
        migrations.AddIndex(
            model_name="animal",
            index=models.Index(fields=["created_by", "updated_at"], name="animals_an_created_58d5f9_idx"),
        ),
        migrations.AddIndex(
            model_name="animal",
            index=models.Index(fields=["identification_no"], name="animals_an_identif_efe528_idx"),
        ),
    ]

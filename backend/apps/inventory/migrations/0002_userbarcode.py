from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserBarcode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32, unique=True)),
                ("form_type", models.CharField(choices=[("expense", "Xərc"), ("income", "Gəlir"), ("animal", "Heyvan"), ("seed", "Toxum"), ("tool", "Alət"), ("farm", "Təsərrüfat məhsulu")], max_length=20)),
                ("target_type", models.CharField(choices=[("form", "Form"), ("subcategory", "Alt kateqoriya"), ("item", "Məhsul"), ("manual", "Manual info")], max_length=20)),
                ("label", models.CharField(max_length=200)),
                ("signature", models.CharField(max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Qlobal Barkod",
                "verbose_name_plural": "Qlobal Barkodlar",
            },
        ),
        migrations.AddConstraint(
            model_name="userbarcode",
            constraint=models.UniqueConstraint(fields=("signature",), name="inventory_unique_barcode_signature"),
        ),
    ]

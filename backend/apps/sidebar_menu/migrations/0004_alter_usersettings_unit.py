from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sidebar_menu", "0003_remove_bas_unit_choice"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usersettings",
            name="unit",
            field=models.CharField(
                choices=[("kg_litr", "kq / litr"), ("kg_gallon", "kq / gallon"), ("lb_litr", "pound / litr"), ("lb_gallon", "pound / gallon")],
                default="kg_litr",
                max_length=10,
            ),
        ),
    ]

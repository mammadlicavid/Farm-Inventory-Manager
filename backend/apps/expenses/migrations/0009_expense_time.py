from django.db import migrations, models
import django.utils.timezone

import common.datetime_defaults


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0008_rename_expenses_ex_created_ead3ca_idx_expenses_ex_created_419f8b_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expense",
            name="date",
            field=models.DateField(default=django.utils.timezone.now, verbose_name="Tarix"),
        ),
        migrations.AddField(
            model_name="expense",
            name="time",
            field=models.TimeField(default=common.datetime_defaults.current_local_time, verbose_name="Saat"),
        ),
    ]

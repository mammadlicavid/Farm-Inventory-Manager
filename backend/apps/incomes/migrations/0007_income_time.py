from django.db import migrations, models

import common.datetime_defaults


class Migration(migrations.Migration):

    dependencies = [
        ("incomes", "0006_alter_income_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="income",
            name="time",
            field=models.TimeField(default=common.datetime_defaults.current_local_time, verbose_name="Saat"),
        ),
    ]

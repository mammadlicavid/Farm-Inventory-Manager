from django.db import migrations, models

import common.datetime_defaults


class Migration(migrations.Migration):

    dependencies = [
        ("farm_products", "0008_farmproduct_zero_price_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmproduct",
            name="time",
            field=models.TimeField(default=common.datetime_defaults.current_local_time, verbose_name="Saat"),
        ),
    ]

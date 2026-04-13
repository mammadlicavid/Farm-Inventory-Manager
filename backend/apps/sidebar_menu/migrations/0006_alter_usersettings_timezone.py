from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sidebar_menu", "0005_usersettings_volume_weight_units_state_only"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usersettings",
            name="timezone",
            field=models.CharField(
                choices=[
                    ("Asia/Baku", "Bakı"),
                    ("Asia/Tbilisi", "Tbilisi"),
                    ("Europe/Moscow", "Moskva"),
                    ("Europe/Istanbul", "İstanbul"),
                    ("Asia/Dubai", "Dubay"),
                    ("Europe/London", "London"),
                    ("Europe/Berlin", "Berlin"),
                    ("Europe/Paris", "Paris"),
                    ("Europe/Rome", "Roma"),
                    ("Europe/Madrid", "Madrid"),
                    ("Europe/Kyiv", "Kiyev"),
                    ("Asia/Almaty", "Almatı"),
                    ("Asia/Tashkent", "Daşkənd"),
                    ("Asia/Karachi", "Kəraçi"),
                    ("Asia/Kolkata", "Delhi / Kolkata"),
                    ("Asia/Shanghai", "Şanxay"),
                    ("Asia/Tokyo", "Tokio"),
                    ("America/New_York", "New York"),
                    ("America/Chicago", "Chicago"),
                    ("America/Denver", "Denver"),
                    ("America/Los_Angeles", "Los Angeles"),
                ],
                default="Asia/Baku",
                max_length=50,
            ),
        ),
    ]

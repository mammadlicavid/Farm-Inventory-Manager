from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sync", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="devicesyncstate",
            index=models.Index(fields=["user", "device_id"], name="sync_device_user_id_8fe63b_idx"),
        ),
        migrations.AddIndex(
            model_name="devicesyncstate",
            index=models.Index(fields=["user", "updated_at"], name="sync_device_user_id_1e0ca0_idx"),
        ),
        migrations.AddIndex(
            model_name="syncoperation",
            index=models.Index(fields=["user", "device_id", "operation_id"], name="sync_syncop_user_id_79f090_idx"),
        ),
        migrations.AddIndex(
            model_name="syncoperation",
            index=models.Index(fields=["user", "status", "received_at"], name="sync_syncop_user_id_0e2dda_idx"),
        ),
        migrations.AddIndex(
            model_name="syncoperation",
            index=models.Index(fields=["user", "processed_at"], name="sync_syncop_user_id_427c8b_idx"),
        ),
    ]

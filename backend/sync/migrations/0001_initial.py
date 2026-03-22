from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceSyncState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_id", models.CharField(max_length=120)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="device_sync_states", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "Device Sync State",
                "verbose_name_plural": "Device Sync States",
                "ordering": ["-updated_at"],
                "unique_together": {("user", "device_id")},
            },
        ),
        migrations.CreateModel(
            name="SyncOperation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_id", models.CharField(max_length=120)),
                ("operation_id", models.CharField(max_length=120)),
                ("entity_type", models.CharField(max_length=50)),
                ("action", models.CharField(max_length=50)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("completed", "Completed"), ("failed", "Failed")], default="pending", max_length=20)),
                ("target_model", models.CharField(blank=True, max_length=120)),
                ("target_object_id", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sync_operations", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "Sync Operation",
                "verbose_name_plural": "Sync Operations",
                "ordering": ["-received_at"],
                "unique_together": {("user", "device_id", "operation_id")},
            },
        ),
    ]

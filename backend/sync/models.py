from django.conf import settings
from django.db import models


class DeviceSyncState(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_sync_states",
    )
    device_id = models.CharField(max_length=120)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "device_id")
        ordering = ["-updated_at"]
        verbose_name = "Device Sync State"
        verbose_name_plural = "Device Sync States"
        indexes = [
            models.Index(fields=["user", "device_id"]),
            models.Index(fields=["user", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.user} / {self.device_id}"


class SyncOperation(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sync_operations",
    )
    device_id = models.CharField(max_length=120)
    operation_id = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    target_model = models.CharField(max_length=120, blank=True)
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "device_id", "operation_id")
        ordering = ["-received_at"]
        verbose_name = "Sync Operation"
        verbose_name_plural = "Sync Operations"
        indexes = [
            models.Index(fields=["user", "device_id", "operation_id"]),
            models.Index(fields=["user", "status", "received_at"]),
            models.Index(fields=["user", "processed_at"]),
        ]

    def __str__(self):
        return f"{self.entity_type}:{self.action}:{self.operation_id}"

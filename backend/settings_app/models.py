from django.conf import settings
from django.db import models


class UserSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings"
    )

    big_text = models.BooleanField(default=False)
    auto_sync = models.BooleanField(default=True)

    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('litr', 'Litr'),
        ('bas', 'Baş'),
    ]

    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default='kg'
    )

    CURRENCY_CHOICES = [
        ('AZN', 'Manat'),
        ('USD', 'Dollar'),
        ('EUR', 'Euro'),
    ]

    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='AZN'
    )

    def __str__(self):
        return f"{self.user.username} Settings"

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)
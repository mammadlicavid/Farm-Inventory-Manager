from django.db import models
from django.contrib.auth.models import User


class UserSettings(models.Model):
    LANGUAGE_CHOICES = [
        ('az', 'Azərbaycan dili'),
        ('en', 'English'),
        ('ru', 'Русский'),
    ]
    TIMEZONE_CHOICES = [
        ('Asia/Baku',     'Bakı (UTC+4)'),
        ('Europe/London', 'London (UTC+0)'),
        ('Europe/Moscow', 'Moskva (UTC+3)'),
    ]
    UNIT_CHOICES = [
        ('kg',   'kg'),
        ('litr', 'litr'),
        ('bas',  'baş'),
    ]
    CURRENCY_CHOICES = [
        ('AZN', 'AZN ₼'),
        ('EUR', 'EUR €'),
        ('USD', 'USD $'),
    ]

    user                  = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sidebar_settings')
    language              = models.CharField(max_length=10,  choices=LANGUAGE_CHOICES,  default='az')
    timezone              = models.CharField(max_length=50,  choices=TIMEZONE_CHOICES,  default='Asia/Baku')
    unit                  = models.CharField(max_length=10,  choices=UNIT_CHOICES,      default='kg')
    currency              = models.CharField(max_length=5,   choices=CURRENCY_CHOICES,  default='AZN')
    email_notifications   = models.BooleanField(default=True)
    system_notifications  = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - Parametrlər"

    class Meta:
        app_label            = 'sidebar_menu'
        verbose_name         = 'İstifadəçi Parametrləri'
        verbose_name_plural  = 'İstifadəçi Parametrləri'
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.auth.models import User


TIMEZONE_GROUPS = [
    (
        _("Qafqaz və yaxın region"),
        [
            ("Asia/Baku", _("Bakı")),
            ("Asia/Tbilisi", _("Tbilisi")),
            ("Europe/Moscow", _("Moskva")),
            ("Europe/Istanbul", _("İstanbul")),
            ("Asia/Dubai", _("Dubay")),
        ],
    ),
    (
        _("Avropa"),
        [
            ("Europe/London", _("London")),
            ("Europe/Berlin", _("Berlin")),
            ("Europe/Paris", _("Paris")),
            ("Europe/Rome", _("Roma")),
            ("Europe/Madrid", _("Madrid")),
            ("Europe/Kyiv", _("Kiyev")),
        ],
    ),
    (
        _("Asiya"),
        [
            ("Asia/Almaty", _("Almatı")),
            ("Asia/Tashkent", _("Daşkənd")),
            ("Asia/Karachi", _("Kəraçi")),
            ("Asia/Kolkata", _("Delhi / Kolkata")),
            ("Asia/Shanghai", _("Şanxay")),
            ("Asia/Tokyo", _("Tokio")),
        ],
    ),
    (
        _("Amerika"),
        [
            ("America/New_York", _("New York")),
            ("America/Chicago", _("Chicago")),
            ("America/Denver", _("Denver")),
            ("America/Los_Angeles", _("Los Angeles")),
        ],
    ),
]


class UserSettings(models.Model):
    LANGUAGE_CHOICES = [
        ('az', 'Azərbaycan dili'),
        ('en', 'English'),
        ('ru', 'Русский'),
    ]
    TIMEZONE_CHOICES = [
        (zone_name, city_label)
        for _, zone_entries in TIMEZONE_GROUPS
        for zone_name, city_label in zone_entries
    ]
    UNIT_CHOICES = [
        ('kg_litr', 'kq / litr'),
        ('kg_gallon', 'kq / gallon'),
        ('lb_litr', 'pound / litr'),
        ('lb_gallon', 'pound / gallon'),
    ]

    WEIGHT_UNIT_CHOICES = [
        ("kg", "kq"),
        ("lb", "pound"),
    ]

    VOLUME_UNIT_CHOICES = [
        ("litr", "litr"),
        ("gallon", "gallon"),
    ]
    CURRENCY_CHOICES = [
        ('AZN', 'AZN ₼'),
        ('EUR', 'EUR €'),
        ('USD', 'USD $'),
    ]

    user                  = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sidebar_settings')
    language              = models.CharField(max_length=10,  choices=LANGUAGE_CHOICES,  default='az')
    timezone              = models.CharField(max_length=50,  choices=TIMEZONE_CHOICES,  default='Asia/Baku')
    unit                  = models.CharField(max_length=10,  choices=UNIT_CHOICES,      default='kg_litr')
    volume_unit           = models.CharField(max_length=10,  choices=VOLUME_UNIT_CHOICES, default="litr")
    weight_unit           = models.CharField(max_length=10,  choices=WEIGHT_UNIT_CHOICES, default="kg")
    currency              = models.CharField(max_length=5,   choices=CURRENCY_CHOICES,  default='AZN')
    email_notifications   = models.BooleanField(default=True)
    system_notifications  = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - Parametrlər"

    class Meta:
        app_label            = 'sidebar_menu'
        verbose_name         = 'İstifadəçi Parametrləri'
        verbose_name_plural  = 'İstifadəçi Parametrləri'

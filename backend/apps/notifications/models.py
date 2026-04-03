from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('vaksinasiya', 'Vaksinasiya'),
        ('odenis', 'Ödəniş'),
        ('ekin', 'Əkin'),
        ('ehtiyat', 'Ehtiyat'),
        ('diger', 'Digər'),
    ]

    title = models.CharField(max_length=255, verbose_name='Başlıq')
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='diger',
        verbose_name='Kateqoriya',
    )
    due_date = models.DateField(verbose_name='Tarix')
    is_completed = models.BooleanField(default=False, verbose_name='Tamamlanıb')
    is_system_generated = models.BooleanField(default=False, verbose_name='Sistem tərəfindən yaradılıb')
    source_key = models.CharField(max_length=255, blank=True, null=True, verbose_name='Mənbə açarı')
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date']
        verbose_name = 'Xatırlatma'
        verbose_name_plural = 'Xatırlatmalar'

    def __str__(self):
        return self.title


class StockAlertRule(models.Model):
    SOURCE_SEED = "seed"
    SOURCE_TOOL = "tool"
    SOURCE_FARM = "farm"
    SOURCE_ANIMAL = "animal"

    SOURCE_CHOICES = [
        (SOURCE_SEED, "Toxum"),
        (SOURCE_TOOL, "Alət"),
        (SOURCE_FARM, "Təsərrüfat məhsulu"),
        (SOURCE_ANIMAL, "Heyvan"),
    ]

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="stock_alert_rules",
    )
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    item_key = models.CharField(max_length=255, verbose_name="Məhsul açarı")
    item_name = models.CharField(max_length=255, verbose_name="Məhsul adı")
    unit = models.CharField(max_length=20, blank=True, verbose_name="Ölçü vahidi")
    threshold = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Xəbərdarlıq həddi")
    is_active = models.BooleanField(default=True, verbose_name="Aktivdir")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["item_name"]
        verbose_name = "Ehtiyat xəbərdarlıq qaydası"
        verbose_name_plural = "Ehtiyat xəbərdarlıq qaydaları"
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "item_key"],
                name="notifications_unique_stock_alert_rule_per_user",
            )
        ]

    def __str__(self):
        return f"{self.item_name} <= {self.threshold} {self.unit}".strip()

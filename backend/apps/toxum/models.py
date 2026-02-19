from django.db import models
from django.conf import settings

class Seed(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ad")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Miqdar")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Qiymət")
    UNIT_CHOICES = [
        ('kg', 'kg'),
        ('ton', 'ton'),
        ('qram', 'qram'),
        ('ədəd', 'ədəd'),
    ]

    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="kg", verbose_name="Ölçü vahidi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Toxum"
        verbose_name_plural = "Toxumlar"
        ordering = ['-created_at']

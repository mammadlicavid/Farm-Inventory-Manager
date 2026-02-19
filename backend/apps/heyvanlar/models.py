from django.db import models
from django.conf import settings

class Animal(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ad")
    quantity = models.IntegerField(verbose_name="Miqdar", default=1)
    weight = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Çəki", null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Qiymət")

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
        verbose_name = "Heyvan"
        verbose_name_plural = "Heyvanlar"
        ordering = ['-created_at']

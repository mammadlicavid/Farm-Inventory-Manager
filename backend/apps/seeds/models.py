from django.db import models
from django.conf import settings

class SeedCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kateqoriya Adı")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Toxum Kateqoriyası"
        verbose_name_plural = "Toxum Kateqoriyaları"

class SeedItem(models.Model):
    category = models.ForeignKey(SeedCategory, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=100, verbose_name="Toxum Adı")

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    class Meta:
        verbose_name = "Toxum Növü"
        verbose_name_plural = "Toxum Növləri"

class Seed(models.Model):
    item = models.ForeignKey(SeedItem, on_delete=models.CASCADE, verbose_name="Toxum", null=True, blank=True)
    manual_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Xüsusi Ad")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Miqdar")
    unit = models.CharField(max_length=20, choices=[
        ('kg', 'kg'),
        ('ton', 'ton'),
        ('qram', 'qram'),
        ('ədəd', 'ədəd'),
    ], default='kg', verbose_name="Ölçü Vahidi")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Qiymət", default=0, null=True, blank=True)
    
    additional_info = models.TextField(blank=True, null=True, verbose_name="Əlavə məlumat")
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        name = self.item.name if self.item else self.manual_name
        return f"{name} - {self.quantity} {self.unit}"

    class Meta:
        verbose_name = "Toxum Inventarı"
        verbose_name_plural = "Toxum Inventarları"
        ordering = ['-created_at']

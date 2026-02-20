from django.db import models
from django.conf import settings

class ToolCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kateqoriya Adı")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Alət Kateqoriyası"
        verbose_name_plural = "Alət Kateqoriyaları"

class ToolItem(models.Model):
    category = models.ForeignKey(ToolCategory, on_delete=models.CASCADE, related_name="items", verbose_name="Ana Kateqoriya")
    name = models.CharField(max_length=100, verbose_name="Alət Adı")

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        verbose_name = "Alət Növü"
        verbose_name_plural = "Alət Növləri"

class Tool(models.Model):
    item = models.ForeignKey(ToolItem, on_delete=models.CASCADE, related_name="inventory", verbose_name="Alət", null=True, blank=True)
    manual_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Xüsusi Ad")
    quantity = models.IntegerField(verbose_name="Miqdar")
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
        return f"{name} - {self.quantity} ədəd"

    class Meta:
        verbose_name = "Alət"
        verbose_name_plural = "Alətlər"
        ordering = ['-created_at']

from django.db import models
from django.conf import settings

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kateqoriya Adı")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Xərc Kateqoriyası"
        verbose_name_plural = "Xərc Kateqoriyaları"

class ExpenseSubCategory(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name="subcategories", verbose_name="Ana Kateqoriya")
    name = models.CharField(max_length=100, verbose_name="Alt Kateqoriya Adı")

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        verbose_name = "Xərc Alt Kateqoriyası"
        verbose_name_plural = "Xərc Alt Kateqoriyaları"

class Expense(models.Model):
    title = models.CharField(max_length=200, verbose_name="Başlıq")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Məbləğ")
    
    # Temporarily nullable to allow migration
    subcategory = models.ForeignKey(
        ExpenseSubCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="expenses", 
        verbose_name="Alt Kateqoriya"
    )
    manual_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Xüsusi Ad")
    
    additional_info = models.TextField(blank=True, null=True, verbose_name="Əlavə məlumat")
    date = models.DateField(auto_now_add=True, verbose_name="Tarix")
    
    # Generic linking to inventory items
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.contrib.contenttypes.models import ContentType
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount}₼"

    class Meta:
        verbose_name = "Xərc"
        verbose_name_plural = "Xərclər"
        ordering = ['-date', '-created_at']

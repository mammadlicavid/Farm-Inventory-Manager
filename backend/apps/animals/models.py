from django.db import models
from django.conf import settings

class AnimalCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kateqoriya Adı")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Heyvan Kateqoriyası"
        verbose_name_plural = "Heyvan Kateqoriyaları"

class AnimalSubCategory(models.Model):
    category = models.ForeignKey(AnimalCategory, on_delete=models.CASCADE, related_name="subcategories", verbose_name="Ana Kateqoriya")
    name = models.CharField(max_length=100, verbose_name="Alt Kateqoriya Adı")

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        verbose_name = "Heyvan Alt Kateqoriyası"
        verbose_name_plural = "Heyvan Alt Kateqoriyaları"

class Animal(models.Model):
    GENDER_CHOICES = [
        ('erkek', 'Erkək'),
        ('disi', 'Dişi'),
    ]
    
    STATUS_CHOICES = [
        ('aktiv', 'Aktiv'),
        ('satilib', 'Satılıb'),
        ('telef', 'Tələf olub'),
    ]

    subcategory = models.ForeignKey(
        AnimalSubCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="animals", 
        verbose_name="Alt Kateqoriya"
    )
    manual_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Xüsusi Ad")
    
    # Optional field for "Other" category or general identification
    identification_no = models.CharField(max_length=50, verbose_name="İdentifikasiya No", blank=True, null=True)
    additional_info = models.TextField(verbose_name="Əlavə məlumat", blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="Cinsiyyət", default='erkek')
    weight = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Çəki", null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Qiymət", default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aktiv', verbose_name="Status")

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
        name = self.subcategory.name if self.subcategory else self.manual_name
        return f"{name or 'Heyvan'} - {self.identification_no or 'No ID'}"

    class Meta:
        verbose_name = "Heyvan"
        verbose_name_plural = "Heyvanlar"
        ordering = ['-created_at']

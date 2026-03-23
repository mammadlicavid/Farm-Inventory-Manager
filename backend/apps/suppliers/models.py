from django.db import models
from django.conf import settings
from django.utils import timezone

class Supplier(models.Model):
    CATEGORY_CHOICES = [
        ('Toxum', 'Toxum'),
        ('Gübrə', 'Gübrə'),
        ('Alətlər', 'Alətlər'),
        ('Heyvan', 'Heyvan'),
        ('Digər', 'Digər'),
    ]

    name = models.CharField(max_length=200, verbose_name="Təchizatçı Adı")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Digər', verbose_name="Kateqoriya")
    location = models.CharField(max_length=200, verbose_name="Ünvan")
    rating = models.IntegerField(default=5, verbose_name="Reytinq")
    last_order_date = models.DateField(default=timezone.now, verbose_name="Son Sifariş Tarixi")
    is_favorite = models.BooleanField(default=False, verbose_name="Seçilmiş")
    phone = models.CharField(max_length=50, verbose_name="Telefon Nömrəsi")

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
        return self.name

    class Meta:
        verbose_name = "Təchizatçı"
        verbose_name_plural = "Təchizatçılar"
        ordering = ['-is_favorite', '-created_at']

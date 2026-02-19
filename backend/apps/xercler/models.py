from django.db import models
from django.conf import settings

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('SƏ', 'Səpin'),
        ('YEM', 'Heyvan yemi'),
        ('YAN', 'Yanacaq'),
        ('GUB', 'Gübrə'),
        ('TEM', 'Təmir'),
        ('DIG', 'Digər'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name="Kateqoriya")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Məbləğ")
    description = models.TextField(blank=True, verbose_name="İzah")
    date = models.DateField(auto_now_add=True, verbose_name="Tarix")
    created_at = models.DateTimeField(auto_now_add=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )

    def __str__(self):
        return f"{self.category} - {self.amount} AZN"

    class Meta:
        verbose_name = "Xərc"
        verbose_name_plural = "Xərclər"
        ordering = ['-date', '-created_at']

from django.db import models
from django.conf import settings

class Alet(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ad")
    quantity = models.IntegerField(verbose_name="Miqdar")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Qiymət")
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    
    TYPE_CHOICES = [
        ('Traktor', 'Traktor'),
        ('Kənd təsərrüfatı aləti', 'Kənd təsərrüfatı aləti'),
        ('Digər', 'Digər'),
    ]
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='Digər', verbose_name="Növ")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Alət"
        verbose_name_plural = "Alətlər"
        ordering = ['-created_at']

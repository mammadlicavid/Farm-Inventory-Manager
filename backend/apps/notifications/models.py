from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('vaksinasiya', 'Vaksinasiya'),
        ('odenis', 'Ödəniş'),
        ('ekin', 'Əkin'),
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

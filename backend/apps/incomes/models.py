from django.db import models
from django.conf import settings
from django.utils import timezone


UNIT_KQ = "kq"
UNIT_TON = "ton"
UNIT_QRAM = "qram"
UNIT_LITR = "litr"
UNIT_ML = "ml"
UNIT_EDAD = "ədəd"
UNIT_DESTE = "dəstə"
UNIT_BAGLAMA = "bağlama"

UNIT_CHOICES = [
    (UNIT_KQ, UNIT_KQ),
    (UNIT_TON, UNIT_TON),
    (UNIT_QRAM, UNIT_QRAM),
    (UNIT_LITR, UNIT_LITR),
    (UNIT_ML, UNIT_ML),
    (UNIT_EDAD, UNIT_EDAD),
    (UNIT_DESTE, UNIT_DESTE),
    (UNIT_BAGLAMA, UNIT_BAGLAMA),
]

GENDER_MALE = "erkek"
GENDER_FEMALE = "disi"

GENDER_CHOICES = [
    (GENDER_MALE, "Erkək"),
    (GENDER_FEMALE, "Dişi"),
]


class Income(models.Model):
    category = models.CharField(max_length=120, verbose_name="Kateqoriya")
    item_name = models.CharField(max_length=120, verbose_name="Məhsul adı")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Miqdar")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, verbose_name="Ölçü vahidi")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Məbləğ")
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name="Cinsiyyət",
    )
    additional_info = models.TextField(blank=True, null=True, verbose_name="Əlavə məlumat")
    date = models.DateField(default=timezone.now, verbose_name="Tarix")

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
        related_name="incomes_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.item_name} - {self.amount}₼"

    class Meta:
        verbose_name = "Gəlir"
        verbose_name_plural = "Gəlirlər"
        ordering = ["-date", "-created_at"]

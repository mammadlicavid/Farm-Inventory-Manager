from django.db import models
from django.conf import settings


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
    (UNIT_ML, "millilitr"),
    (UNIT_EDAD, UNIT_EDAD),
    (UNIT_DESTE, UNIT_DESTE),
    (UNIT_BAGLAMA, UNIT_BAGLAMA),
]


class FarmProductCategory(models.Model):
    name = models.CharField(max_length=120, verbose_name="Kateqoriya Adı")

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Təsərrüfat Məhsulu Kateqoriyası"
        verbose_name_plural = "Təsərrüfat Məhsulu Kateqoriyaları"


class FarmProductItem(models.Model):
    category = models.ForeignKey(
        FarmProductCategory,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Ana Kateqoriya",
    )
    name = models.CharField(max_length=120, verbose_name="Məhsul Adı")
    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        blank=True,
        null=True,
        verbose_name="Ölçü Vahidi",
    )

    def __str__(self) -> str:
        return f"{self.category.name} - {self.name}"

    class Meta:
        verbose_name = "Təsərrüfat Məhsulu Növü"
        verbose_name_plural = "Təsərrüfat Məhsulu Növləri"


class FarmProduct(models.Model):
    item = models.ForeignKey(
        FarmProductItem,
        on_delete=models.CASCADE,
        related_name="inventory",
        verbose_name="Məhsul",
        null=True,
        blank=True,
    )
    manual_name = models.CharField(max_length=120, blank=True, null=True, verbose_name="Xüsusi Ad")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Miqdar")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, verbose_name="Ölçü Vahidi")
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

    def __str__(self) -> str:
        name = self.item.name if self.item else self.manual_name
        return f"{name} - {self.quantity} {self.unit}"

    class Meta:
        verbose_name = "Təsərrüfat Məhsulu"
        verbose_name_plural = "Təsərrüfat Məhsulları"
        ordering = ["-created_at"]

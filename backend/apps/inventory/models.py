from django.db import models

# Create your models here.

class ScanItem(models.Model):
    CATEGORY_CHOICES = [
        ("toxumlar", "Toxumlar"),
        ("aletler", "Alətlər"),
        ("heyvanlar", "Heyvanlar"),
        ("teserrufat", "Təsərrüfat məhsulları"),
        ("xercler", "Xərclər"),
        ("diger", "Digər"),
    ]

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    unit = models.CharField(max_length=30, blank=True, null=True)
    default_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
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


class UserBarcode(models.Model):
    FORM_TYPE_CHOICES = [
        ("expense", "Xərc"),
        ("income", "Gəlir"),
        ("animal", "Heyvan"),
        ("seed", "Toxum"),
        ("tool", "Alət"),
        ("farm", "Təsərrüfat məhsulu"),
    ]

    TARGET_TYPE_CHOICES = [
        ("form", "Form"),
        ("subcategory", "Alt kateqoriya"),
        ("item", "Məhsul"),
        ("manual", "Manual info"),
    ]

    code = models.CharField(max_length=32, unique=True)
    form_type = models.CharField(max_length=20, choices=FORM_TYPE_CHOICES)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)
    label = models.CharField(max_length=200)
    signature = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Qlobal Barkod"
        verbose_name_plural = "Qlobal Barkodlar"
        constraints = [
            models.UniqueConstraint(
                fields=["signature"],
                name="inventory_unique_barcode_signature",
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.label}"

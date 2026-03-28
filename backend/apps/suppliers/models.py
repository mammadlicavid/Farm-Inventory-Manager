from django.db import models
from django.conf import settings

class Supplier(models.Model):
    CATEGORY_CHOICES = [
        ('Toxum', 'Toxum'),
        ('Gübrə', 'Gübrə'),
        ('Pestisid', 'Pestisid'),
        ('Baytarlıq', 'Baytarlıq'),
        ('Yem', 'Yem'),
        ('Alətlər', 'Alətlər'),
        ('Kənd Texnikası', 'Kənd Texnikası'),
        ('Suvarma', 'Suvarma'),
        ('Heyvan', 'Heyvan'),
        ('Digər', 'Digər'),
    ]

    name = models.CharField(max_length=200, verbose_name="Təchizatçı Adı")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Digər', verbose_name="Kateqoriya")
    manual_category = models.CharField(max_length=200, blank=True, default="", verbose_name="Kateqoriya (Digər)")
    location = models.CharField(max_length=200, blank=True, default="", verbose_name="Ünvan")
    rating = models.IntegerField(default=5, verbose_name="Reytinq")
    last_order_date = models.DateField(null=True, blank=True, verbose_name="Son Sifariş Tarixi")
    phone = models.CharField(max_length=50, blank=True, default="", verbose_name="Telefon Nömrəsi")
    additional_info = models.TextField(blank=True, default="", verbose_name="Əlavə Məlumat")

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

    @staticmethod
    def normalize_phone(value):
        return ''.join((value or '').split())

    @property
    def formatted_phone(self):
        phone = self.normalize_phone(self.phone)
        if phone.startswith('+994') and len(phone) == 13:
            return f"{phone[:4]} {phone[4:6]} {phone[6:9]} {phone[9:11]} {phone[11:13]}"
        if phone.startswith('994') and len(phone) == 12:
            phone = f"+{phone}"
            return f"{phone[:4]} {phone[4:6]} {phone[6:9]} {phone[9:11]} {phone[11:13]}"
        return self.phone

    def save(self, *args, **kwargs):
        self.phone = self.normalize_phone(self.phone)
        if self.category != "Digər":
            self.manual_category = ""
        super().save(*args, **kwargs)

    @property
    def display_category(self):
        if self.category == "Digər" and self.manual_category:
            return self.manual_category
        return self.category

    @property
    def category_css_class(self):
        return {
            "Toxum": "toxum",
            "Gübrə": "gubre",
            "Pestisid": "pestisid",
            "Baytarlıq": "baytarliq",
            "Yem": "yem",
            "Alətlər": "aletler",
            "Kənd Texnikası": "texnika",
            "Suvarma": "suvarma",
            "Heyvan": "heyvan",
            "Digər": "diger",
        }.get(self.category, "diger")

    class Meta:
        verbose_name = "Təchizatçı"
        verbose_name_plural = "Təchizatçılar"
        ordering = ['-created_at']

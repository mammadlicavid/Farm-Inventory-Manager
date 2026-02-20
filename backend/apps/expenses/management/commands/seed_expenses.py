from django.core.management.base import BaseCommand
from expenses.models import ExpenseCategory, ExpenseSubCategory

class Command(BaseCommand):
    help = 'Seeds the database with default expense categories and subcategories in Azerbaijani'

    def handle(self, *args, **kwargs):
        # Clear existing to avoid mix
        ExpenseSubCategory.objects.all().delete()
        ExpenseCategory.objects.all().delete()

        data = {
            "Heyvandarlıq": ["Yem", "Baytarlıq", "Peyvəndləmə", "Heyvan alışı"],
            "Bitkiçilik": ["Toxumlar", "Gübrə", "Pesticidlər", "Suvarma"],
            "İşçi qüvvəsi": ["Maaşlar", "Sığorta"],
            "Texnika və Maşınlar": ["Yanacaq", "Təmir və Baxım", "Texnika alışı"],
            "İnfrastruktur": ["Elektrik", "Su", "Tikinti"],
            "Logistika və Satış": ["Nəqliyyat", "Qablaşdırma"],
            "Maliyyə və Digər": ["Vergilər", "Kredit faizləri"],
            "Digər": []
        }

        for cat_name, subcats in data.items():
            category, created = ExpenseCategory.objects.get_or_create(name=cat_name)
            self.stdout.write(self.style.SUCCESS(f'Kateqoriya yaradıldı: {cat_name}'))
            
            for subcat_name in subcats:
                ExpenseSubCategory.objects.get_or_create(
                    category=category, 
                    name=subcat_name
                )
                self.stdout.write(self.style.SUCCESS(f'  Alt kateqoriya yaradıldı: {subcat_name}'))
        
        self.stdout.write(self.style.SUCCESS('Xərc kateqoriyaları uğurla yeniləndi!'))

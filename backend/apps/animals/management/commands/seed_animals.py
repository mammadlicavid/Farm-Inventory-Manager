from django.core.management.base import BaseCommand
from animals.models import AnimalCategory, AnimalSubCategory

class Command(BaseCommand):
    help = 'Seeds the database with animal categories and subcategories'

    def handle(self, *args, **kwargs):
        data = {
            "İribuynuzlular": ["İnək", "Dana", "Camış"],
            "Xırdabuynuzlular": ["Qoyun", "Keçi"],
            "Quşlar": ["Toyuq", "Hinduşka", "Qaz", "Ördək", "Bildircin"],
            "Təkdırnaqlılar": ["At", "Eşşək", "Qatır"],
            "Digər": []
        }

        for cat_name, subcats in data.items():
            category, created = AnimalCategory.objects.get_or_create(name=cat_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {cat_name}'))
            
            for subcat_name in subcats:
                subcategory, sub_created = AnimalSubCategory.objects.get_or_create(
                    category=category, 
                    name=subcat_name
                )
                if sub_created:
                    self.stdout.write(self.style.SUCCESS(f'  Created subcategory: {subcat_name}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded animal categories and subcategories'))

from django.core.management.base import BaseCommand
from tools.models import ToolCategory, ToolItem

class Command(BaseCommand):
    help = 'Seeds the database with tool categories and items'

    def handle(self, *args, **kwargs):
        data = {
            "Əl Alətləri": ["Bel", "Kürək", "Dırmıq", "Balta", "Bıçaq", "Mala"],
            "Suvarma Alətləri": ["Şlanq", "Püskürdücü", "Nasos", "Vedrə"],
            "Kənd Təsərrüfatı Texnikası": ["Traktor", "Kultivator", "Kotan", "Səpən"],
            "Baxım və Təmir": ["Açar dəsti", "Drel", "Çəkic", "Lir"],
            "Digər": []
        }

        for cat_name, items in data.items():
            category, created = ToolCategory.objects.get_or_create(name=cat_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {cat_name}'))
            
            for item_name in items:
                item, item_created = ToolItem.objects.get_or_create(
                    category=category, 
                    name=item_name
                )
                if item_created:
                    self.stdout.write(self.style.SUCCESS(f'  Created tool item: {item_name}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded tool categories and items'))

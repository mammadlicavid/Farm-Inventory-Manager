from django.core.management.base import BaseCommand
from seeds.models import SeedCategory, SeedItem

class Command(BaseCommand):
    help = 'Seeds the database with predefined seed categories and items'

    def handle(self, *args, **kwargs):
        data = {
            "Taxıl Bitkiləri": ["Buğda", "Arpa", "Çovdar", "Vələmir", "Qarğıdalı", "Çəltik"],
            "Paxlalılar": ["Lobya", "Noxud", "Mərcimək"],
            "Yağlı Bitkilər": ["Günəbaxan", "Pambıq", "Soya", "Şəkər çuğunduru"],
            "Yem Bitkiləri": ["Yonca", "Koronilla", "Seradella"],
            "Tərəvəzlər": ["Pomidor", "Xiyar", "Bibər", "Badımcan", "Kahı", "İspanaq"],
            "Bostan Bitkiləri": ["Qarpız", "Yemiş", "Boranı"],
            "Meyvə Bitkiləri": [],
            "Digər": []
        }

        total_items = 0
        for cat_name, items in data.items():
            category, created = SeedCategory.objects.get_or_create(name=cat_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {cat_name}'))
            
            for item_name in items:
                item, item_created = SeedItem.objects.get_or_create(
                    category=category, 
                    name=item_name
                )
                if item_created:
                    total_items += 1
                    self.stdout.write(self.style.SUCCESS(f'  Created item: {item_name}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(data)} categories and {total_items} items'))

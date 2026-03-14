from django.core.management.base import BaseCommand
from django.db.models import Value
from django.db.models.functions import Concat

from seeds.models import SeedCategory, SeedItem

class Command(BaseCommand):
    help = 'Seeds the database with predefined seed categories and items'

    def handle(self, *args, **kwargs):
        data = {
            "Taxıl toxumları": ["Buğda toxumu", "Arpa toxumu", "Çovdar toxumu", "Vələmir toxumu", "Qarğıdalı toxumu", "Çəltik toxumu"],
            "Paxlalı toxumları": ["Lobya toxumu", "Noxud toxumu", "Mərcimək toxumu"],
            "Yağlı bitki toxumları": ["Günəbaxan toxumu", "Pambıq toxumu", "Soya toxumu", "Şəkər çuğunduru toxumu"],
            "Yem bitki toxumları": ["Yonca toxumu", "Koronilla toxumu", "Seradella toxumu"],
            "Tərəvəz toxumları": ["Pomidor toxumu", "Xiyar toxumu", "Bibər toxumu", "Badımcan toxumu", "Kahı toxumu", "İspanaq toxumu"],
            "Bostan toxumları": ["Qarpız toxumu", "Yemiş toxumu", "Boranı toxumu"],
            "Meyvə toxumları": ["Alma toxumu", "Armud toxumu", "Şaftalı toxumu", "Ərik toxumu", "Albalı toxumu", "Gilas toxumu", "Nar toxumu", "Üzüm toxumu", "Gavalı toxumu", "Heyva toxumu"],
            "Digər": []
        }

        rename_categories = {
            "Taxıl Bitkiləri": "Taxıl toxumları",
            "Paxlalılar": "Paxlalı toxumları",
            "Yağlı Bitkilər": "Yağlı bitki toxumları",
            "Yem Bitkiləri": "Yem bitki toxumları",
            "Tərəvəzlər": "Tərəvəz toxumları",
            "Bostan Bitkiləri": "Bostan toxumları",
            "Meyvə Bitkiləri": "Meyvə toxumları",
            "Digər toxumlar": "Digər",
        }

        for old_name, new_name in rename_categories.items():
            SeedCategory.objects.filter(name=old_name).update(name=new_name)

        SeedItem.objects.exclude(name__iexact="Digər").exclude(name__iendswith="toxumu").update(
            name=Concat("name", Value(" toxumu"))
        )

        for cat_name, items in data.items():
            if cat_name != "Digər" and "Digər" not in items:
                items.append("Digər")

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

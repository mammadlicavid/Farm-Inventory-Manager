from django.core.management.base import BaseCommand

from farm_products.models import FarmProductCategory, FarmProductItem


class Command(BaseCommand):
    help = "Seeds the database with predefined farm product categories and items"

    def handle(self, *args, **kwargs):
        data = {
            "Süd və Süd Məhsulları": [
                ("İnək südü", "litr"),
                ("Camış südü", "litr"),
                ("Keçi südü", "litr"),
                ("İnək pendiri", "kq"),
                ("Camış pendiri", "kq"),
                ("Keçi pendiri", "kq"),
                ("Qatıq", "kq"),
                ("Ayran", "litr"),
                ("Kərə yağı", "kq"),
                ("Qaymaq", "kq"),
            ],
            "Yumurta": [
                ("Toyuq yumurtası", "ədəd"),
                ("Hinduşka yumurtası", "ədəd"),
                ("Qaz yumurtası", "ədəd"),
                ("Ördək yumurtası", "ədəd"),
                ("Bildircin yumurtası", "ədəd"),
            ],
            "Ət Məhsulları": [
                ("Mal əti", "kq"),
                ("Dana əti", "kq"),
                ("Camış əti", "kq"),
                ("Qoyun əti", "kq"),
                ("Keçi əti", "kq"),
                ("Toyuq əti", "kq"),
                ("Hinduşka əti", "kq"),
                ("Qaz əti", "kq"),
                ("Ördək əti", "kq"),
                ("Bildircin əti", "kq"),
            ],
            "Meyvə": [
                ("Alma", "kq"),
                ("Armud", "kq"),
                ("Şaftalı", "kq"),
                ("Ərik", "kq"),
                ("Albalı", "kq"),
                ("Gilas", "kq"),
                ("Nar", "kq"),
                ("Üzüm", "kq"),
                ("Gavalı", "kq"),
                ("Heyva", "kq"),
            ],
            "Tərəvəz": [
                ("Pomidor", "kq"),
                ("Xiyar", "kq"),
                ("Bibər", "kq"),
                ("Badımcan", "kq"),
                ("Kahı", "kq"),
                ("İspanaq", "kq"),
                ("Soğan", "kq"),
                ("Sarımsaq", "kq"),
                ("Kartof", "kq"),
            ],
            "Göyərti": [
                ("Keşniş", "dəstə"),
                ("Şüyüt", "dəstə"),
                ("Cəfəri", "dəstə"),
                ("Yaşıl soğan", "dəstə"),
                ("Reyhan", "dəstə"),
                ("Tərxun", "dəstə"),
            ],
            "Taxıl Məhsulları": [
                ("Buğda", "kq"),
                ("Arpa", "kq"),
                ("Çovdar", "kq"),
                ("Vələmir", "kq"),
                ("Qarğıdalı", "kq"),
                ("Çəltik", "kq"),
            ],
            "Yem Bitkiləri": [
                ("Yonca", "kq"),
                ("Koronilla", "kq"),
                ("Seradella", "kq"),
            ],
            "Bostan Məhsulları": [
                ("Qarpız", "kq"),
                ("Yemiş", "kq"),
                ("Boranı", "kq"),
            ],
            "Bal və Arıçılıq": [
                ("Bal", "kq"),
                ("Arı mumu", "kq"),
                ("Arı südü", "kq"),
            ],
            "Gübrələr": [
                ("Mal peyini", "kq"),
                ("Qoyun peyini", "kq"),
                ("Keçi peyini", "kq"),
                ("Quş peyini", "kq"),
                ("Kompost", "kq"),
                ("Mineral gübrə", "kq"),
            ],
            "Digər": [],
        }

        rename_map = {
            "Süd və Süd Məhsulları (Litr / kq)": "Süd və Süd Məhsulları",
            "Yumurta (ədəd)": "Yumurta",
            "Ət Məhsulları (kq)": "Ət Məhsulları",
            "Meyvə (kq)": "Meyvə",
            "Tərəvəz (kq)": "Tərəvəz",
            "Göyərti (dəstə)": "Göyərti",
            "Taxıl Məhsulları (kq)": "Taxıl Məhsulları",
            "Yem Bitkiləri (kq / bağlama)": "Yem Bitkiləri",
            "Bostan Məhsulları (kq)": "Bostan Məhsulları",
            "Bal və Arıçılıq (kq)": "Bal və Arıçılıq",
            "Gübrələr (kq)": "Gübrələr",
            "Digər (kq / ədəd / litr / dəstə / bağlama)": "Digər",
        }

        for old_name, new_name in rename_map.items():
            FarmProductCategory.objects.filter(name=old_name).update(name=new_name)

        for cat_name, items in data.items():
            if not cat_name.startswith("Digər") and not any(name == "Digər" for name, _ in items):
                items.append(("Digər", None))
        diger_key = next((name for name in data if name.startswith("Digər")), None)
        if diger_key and not data[diger_key]:
            data[diger_key].append(("Digər", None))

        total_items = 0
        for cat_name, items in data.items():
            category, created = FarmProductCategory.objects.get_or_create(name=cat_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {cat_name}"))

            for item_name, unit in items:
                item, item_created = FarmProductItem.objects.get_or_create(
                    category=category,
                    name=item_name,
                    defaults={"unit": unit},
                )
                if not item_created and unit and item.unit != unit:
                    item.unit = unit
                    item.save(update_fields=["unit"])
                if item_created:
                    total_items += 1
                    self.stdout.write(self.style.SUCCESS(f"  Created item: {item_name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {len(data)} categories and {total_items} items"
            )
        )

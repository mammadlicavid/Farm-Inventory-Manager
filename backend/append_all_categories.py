import os
import polib

# Translation dictionary based on category_order.py
CATEGORIES_AND_ITEMS = {
    # Placeholders
    "Kateqoriya seçin": {"en": "Select category", "ru": "Выберите категорию"},
    "Alt kateqoriya seçin": {"en": "Select subcategory", "ru": "Выберите подкатегорию"},
    "Məhsul növü seçin": {"en": "Select product type", "ru": "Выберите тип продукта"},
    "Ana kateqoriya seçin": {"en": "Select main category", "ru": "Выберите основную категорию"},
    
    # Categories
    "Taxıl toxumları": {"en": "Grain seeds", "ru": "Семена зерновых"},
    "Paxlalı toxumları": {"en": "Legume seeds", "ru": "Семена бобовых"},
    "Yağlı bitki toxumları": {"en": "Oilseed seeds", "ru": "Семена масличных культур"},
    "Yem bitki toxumları": {"en": "Forage crop seeds", "ru": "Семена кормовых культур"},
    "Tərəvəz toxumları": {"en": "Vegetable seeds", "ru": "Семена овощей"},
    "Bostan toxumları": {"en": "Melon/Gourd seeds", "ru": "Семена бахчевых"},
    "Meyvə toxumları": {"en": "Fruit seeds", "ru": "Семена фруктов"},
    "İribuynuzlular": {"en": "Cattle", "ru": "Крупный рогатый скот"},
    "Xırdabuynuzlular": {"en": "Small ruminants", "ru": "Мелкий рогатый скот"},
    "Quşlar": {"en": "Poultry", "ru": "Птицы"},
    "Təkdırnaqlılar": {"en": "Solipeds", "ru": "Однокопытные"},
    "Süd və Süd Məhsulları": {"en": "Milk and Dairy Products", "ru": "Молоко и молочные продукты"},
    "Yumurta": {"en": "Eggs", "ru": "Яйца"},
    "Ət Məhsulları": {"en": "Meat Products", "ru": "Мясные продукты"},
    "Meyvə": {"en": "Fruit", "ru": "Фрукты"},
    "Tərəvəz": {"en": "Vegetables", "ru": "Овощи"},
    "Göyərti": {"en": "Greens", "ru": "Зелень"},
    "Taxıl Məhsulları": {"en": "Grain Products", "ru": "Зерновые продукты"},
    "Yem Bitkiləri": {"en": "Forage Crops", "ru": "Кормовые культуры"},
    "Bostan Məhsulları": {"en": "Melon Products", "ru": "Бахчевые продукты"},
    "Bal və Arıçılıq": {"en": "Honey and Beekeeping", "ru": "Мед и пчеловодство"},
    "Gübrələr": {"en": "Fertilizers", "ru": "Удобрения"},
    "Əl Alətləri": {"en": "Hand Tools", "ru": "Ручные инструменты"},
    "Suvarma Alətləri": {"en": "Irrigation Tools", "ru": "Инструменты для полива"},
    "Kənd Texnikası": {"en": "Farm Machinery", "ru": "Сельхозтехника"},
    "Baxım və Təmir": {"en": "Maintenance and Repair", "ru": "Обслуживание и ремонт"},
    "Digər": {"en": "Other", "ru": "Другое"},
    
    # Items (Seeds)
    "Buğda toxumu": {"en": "Wheat seed", "ru": "Семена пшеницы"},
    "Arpa toxumu": {"en": "Barley seed", "ru": "Семена ячменя"},
    "Çovdar toxumu": {"en": "Rye seed", "ru": "Семена ржи"},
    "Vələmir toxumu": {"en": "Oat seed", "ru": "Семена овса"},
    "Qarğıdalı toxumu": {"en": "Corn seed", "ru": "Семена кукурузы"},
    "Çəltik toxumu": {"en": "Rice seed", "ru": "Семена риса"},
    "Lobya toxumu": {"en": "Bean seed", "ru": "Семена фасоли"},
    "Noxud toxumu": {"en": "Pea seed", "ru": "Семена гороха"},
    "Mərcimək toxumu": {"en": "Lentil seed", "ru": "Семена чечевицы"},
    "Günəbaxan toxumu": {"en": "Sunflower seed", "ru": "Семена подсолнечника"},
    "Pambıq toxumu": {"en": "Cotton seed", "ru": "Семена хлопка"},
    "Soya toxumu": {"en": "Soybean seed", "ru": "Семена сои"},
    "Şəkər çuğunduru toxumu": {"en": "Sugar beet seed", "ru": "Семена сахарной свеклы"},
    "Yonca toxumu": {"en": "Alfalfa seed", "ru": "Семена люцерны"},
    "Koronilla toxumu": {"en": "Crown vetch seed", "ru": "Семена корониллы"},
    "Seradella toxumu": {"en": "Serradella seed", "ru": "Семена сераделлы"},
    "Pomidor toxumu": {"en": "Tomato seed", "ru": "Семена томата"},
    "Xiyar toxumu": {"en": "Cucumber seed", "ru": "Семена огурца"},
    "Bibər toxumu": {"en": "Pepper seed", "ru": "Семена перца"},
    "Badımcan toxumu": {"en": "Eggplant seed", "ru": "Семена баклажана"},
    "Kahı toxumu": {"en": "Lettuce seed", "ru": "Семена салата"},
    "İspanaq toxumu": {"en": "Spinach seed", "ru": "Семена шпината"},
    "Qarpız toxumu": {"en": "Watermelon seed", "ru": "Семена арбуза"},
    "Yemiş toxumu": {"en": "Melon seed", "ru": "Семена дыни"},
    "Boranı toxumu": {"en": "Pumpkin seed", "ru": "Семена тыквы"},
    "Alma toxumu": {"en": "Apple seed", "ru": "Семена яблони"},
    "Armud toxumu": {"en": "Pear seed", "ru": "Семена груши"},
    "Şaftalı toxumu": {"en": "Peach seed", "ru": "Семена персика"},
    "Ərik toxumu": {"en": "Apricot seed", "ru": "Семена абрикоса"},
    "Albalı toxumu": {"en": "Sour cherry seed", "ru": "Семена вишни"},
    "Gilas toxumu": {"en": "Sweet cherry seed", "ru": "Семена черешни"},
    "Nar toxumu": {"en": "Pomegranate seed", "ru": "Семена граната"},
    "Üzüm toxumu": {"en": "Grape seed", "ru": "Семена винограда"},
    "Gavalı toxumu": {"en": "Plum seed", "ru": "Семена сливы"},
    "Heyva toxumu": {"en": "Quince seed", "ru": "Семена айвы"},
    
    # Animals
    "İnək": {"en": "Cow", "ru": "Корова"},
    "Dana": {"en": "Calf", "ru": "Теленок"},
    "Camış": {"en": "Buffalo", "ru": "Буйвол"},
    "Qoyun": {"en": "Sheep", "ru": "Овца"},
    "Keçi": {"en": "Goat", "ru": "Коза"},
    "Toyuq": {"en": "Chicken", "ru": "Курица"},
    "Hinduşka": {"en": "Turkey", "ru": "Индейка"},
    "Qaz": {"en": "Goose", "ru": "Гусь"},
    "Ördək": {"en": "Duck", "ru": "Утка"},
    "Bildircin": {"en": "Quail", "ru": "Перепел"},
    "At": {"en": "Horse", "ru": "Лошадь"},
    "Eşşək": {"en": "Donkey", "ru": "Осел"},
    "Qatır": {"en": "Mule", "ru": "Мул"},
    
    # Tools
    "Bel": {"en": "Shovel", "ru": "Лопата"},
    "Kürək": {"en": "Spade", "ru": "Совок"},
    "Dırmıq": {"en": "Rake", "ru": "Грабли"},
    "Balta": {"en": "Axe", "ru": "Топор"},
    "Bıçaq": {"en": "Knife", "ru": "Нож"},
    "Mala": {"en": "Trowel", "ru": "Мастерок"},
    "Şlanq": {"en": "Hose", "ru": "Шланг"},
    "Püskürdücü": {"en": "Sprinkler", "ru": "Распылитель"},
    "Nasos": {"en": "Pump", "ru": "Насос"},
    "Vedrə": {"en": "Bucket", "ru": "Ведро"},
    "Traktor": {"en": "Tractor", "ru": "Трактор"},
    "Kultivator": {"en": "Cultivator", "ru": "Культиватор"},
    "Kotan": {"en": "Plow", "ru": "Плуг"},
    "Səpən": {"en": "Seeder", "ru": "Сеялка"},
    "Açar dəsti": {"en": "Wrench set", "ru": "Набор ключей"},
    "Drel": {"en": "Drill", "ru": "Дрель"},
    "Çəkic": {"en": "Hammer", "ru": "Молоток"},
    "Lir": {"en": "Lyre", "ru": "Лира"},
}

base_dir = "locale"
for lang in ["en", "ru"]:
    path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
    if os.path.exists(path):
        po = polib.pofile(path)
        existing = {entry.msgid for entry in po}
        for k, v in CATEGORIES_AND_ITEMS.items():
            if k not in existing:
                po.append(polib.POEntry(msgid=k, msgstr=v.get(lang, k)))
        po.save(path)
print("Updated all categories and items.")

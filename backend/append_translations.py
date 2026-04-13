from pathlib import Path

WORDS = {
    "Toxumlar": {"en": "Seeds", "ru": "Семена"},
    "Heyvanlar": {"en": "Animals", "ru": "Животные"},
    "Alətlər": {"en": "Tools", "ru": "Инструменты"},
    "Təsərrüfat Məhsulları": {"en": "Farm Products", "ru": "Фермерские продукты"},
    "Digər": {"en": "Other", "ru": "Другое"},
    "diger": {"en": "other", "ru": "другое"},
    "İnək": {"en": "Cow", "ru": "Корова"},
    "Qoyun": {"en": "Sheep", "ru": "Овца"},
    "Keçi": {"en": "Goat", "ru": "Коза"},
    "At": {"en": "Horse", "ru": "Лошадь"},
    "Toyuq": {"en": "Chicken", "ru": "Курица"},
    "Ördək": {"en": "Duck", "ru": "Утка"},
    "Qaz": {"en": "Goose", "ru": "Гусь"},
    "Hindüşka": {"en": "Turkey", "ru": "Индюк"},
    "Dəvəquşu": {"en": "Ostrich", "ru": "Страус"},
    "Dovşan": {"en": "Rabbit", "ru": "Кролик"},
    "Donuz": {"en": "Pig", "ru": "Свинья"},
    "Qaramal / İri Buynuzlu": {"en": "Cattle", "ru": "Крупный рогатый скот"},
    "Xırdabuynuzlu": {"en": "Small ruminant", "ru": "Мелкий рогатый скот"},
    "Quş": {"en": "Bird", "ru": "Птица"},
    "Digər Heyvan": {"en": "Other Animal", "ru": "Другое животное"},
    "Dənli bitkilər": {"en": "Cereals", "ru": "Зерновые культуры"},
    "Yem bitkiləri": {"en": "Forage crops", "ru": "Кормовые культуры"},
    "Tərəvəz": {"en": "Vegetable", "ru": "Овощи"},
    "Meyvə": {"en": "Fruit", "ru": "Фрукты"},
    "Texniki bitkilər": {"en": "Industrial crops", "ru": "Технические культуры"},
    "Buğda": {"en": "Wheat", "ru": "Пшеница"},
    "Arpa": {"en": "Barley", "ru": "Ячмень"},
    "Qarğıdalı": {"en": "Corn", "ru": "Кукуруза"},
    "Yonca": {"en": "Clover", "ru": "Клевер"},
    "Xaç yoncası": {"en": "Alfalfa", "ru": "Люцерна"},
    "Baxar": {"en": "Baxar", "ru": "Бахар"},
    "Koronilla": {"en": "Coronilla", "ru": "Вязель"},
    "Seradella": {"en": "Serradella", "ru": "Сераделла"},
    "Lüpin": {"en": "Lupin", "ru": "Люпин"},
    "Kartof": {"en": "Potato", "ru": "Картофель"},
    "Pomidor": {"en": "Tomato", "ru": "Помидор"},
    "Xiyar": {"en": "Cucumber", "ru": "Огурец"},
    "Pambıq": {"en": "Cotton", "ru": "Хлопок"},
    "Tütün": {"en": "Tobacco", "ru": "Табак"},
    "Bağban alətləri": {"en": "Gardening tools", "ru": "Садовые инструменты"},
    "Ağır texnika": {"en": "Heavy equipment", "ru": "Тяжелая техника"},
    "Təmizlik vasitələri": {"en": "Cleaning supplies", "ru": "Чистящие средства"},
    "Motorlu / Elektrikli": {"en": "Motorized / Electric", "ru": "Моторизованные / Электрические"},
    "Qoruyucu Geyim / Ləvazimat": {"en": "Protective Gear / Equipment", "ru": "Защитное снаряжение / Экипировка"},
    "Digər Alət": {"en": "Other Tool", "ru": "Другой инструмент"},
    "Traktor": {"en": "Tractor", "ru": "Трактор"},
    "Beli": {"en": "Spade", "ru": "Лопата"},
    "Kürək": {"en": "Shovel", "ru": "Совок"},
    "Dırmıq": {"en": "Rake", "ru": "Грабли"},
    "Dərman": {"en": "Medicine", "ru": "Лекарство"},
    "Maaş": {"en": "Salary", "ru": "Зарплата"},
    "Alış": {"en": "Purchase", "ru": "Покупка"},
    "Satış": {"en": "Sale", "ru": "Продажа"},
    "Süd": {"en": "Milk", "ru": "Молоко"},
    "Yumurta": {"en": "Egg", "ru": "Яйцо"},
    "Yun": {"en": "Wool", "ru": "Шерсть"},
    "Dəri": {"en": "Leather", "ru": "Кожа"},
    "Ət": {"en": "Meat", "ru": "Мясо"},
    "təsərrüfat": {"en": "farm", "ru": "ферма"},
    "Təsərrüfat": {"en": "Farm", "ru": "Ферма"},
    "toxumlar": {"en": "seeds", "ru": "семена"},
    "heyvanlar": {"en": "animals", "ru": "животные"},
    "aletler": {"en": "tools", "ru": "инструменты"}
}

BASE_DIR = Path(__file__).resolve().parent
LOCALE_DIR = BASE_DIR / "locale"

for lang in ["en", "ru"]:
    po_file_path = LOCALE_DIR / lang / "LC_MESSAGES" / "django.po"
    if po_file_path.exists():
        with po_file_path.open("r", encoding="utf-8") as f:
            content = f.read()
        
        append_data = []
        for base, transdict in WORDS.items():
            pattern1 = f'msgid "{base}"'
            pattern2 = f'msgid "{base.lower()}"'
            if pattern1 not in content and pattern2 not in content:
                msgstr = transdict.get(lang, base)
                append_data.append(f'\nmsgid "{base}"\nmsgstr "{msgstr}"\n')

        if append_data:
            with po_file_path.open("a", encoding="utf-8") as f:
                f.write("".join(append_data))
            print(f"Added {len(append_data)} words to {lang}")
        else:
            print(f"No new words for {lang}")

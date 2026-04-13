import os, json, polib

translations = {
    "Nə əlavə etmək istəyirsiniz?": {"en": "What do you want to add?", "ru": "Что вы хотите добавить?"},
    "Əvvəl növü seçin. Sonra məlumatı əl ilə, səs ilə və ya barkodla daxil edin.": {"en": "First select the type. Then enter the information manually, by voice or barcode.", "ru": "Сначала выберите тип. Затем введите информацию вручную, голосом или штрихкодом."},
    "Süd, yumurta, tərəvəz və digər hazır məhsulu əlavə edin.": {"en": "Add milk, eggs, vegetables, and other finished products.", "ru": "Добавьте молоко, яйца, овощи и другие готовые продукты."},
    "Ən sadə yol: yuxarıdan növü seçin. Form aşağıda dərhal açılacaq.": {"en": "The simplest way: choose the type from above. The form will open immediately below.", "ru": "Самый простой способ: выберите тип выше. Форма откроется сразу ниже."},
    "Daxiletmə üsulu": {"en": "Input method", "ru": "Метод ввода"},
    "Məlumatı necə daxil etmək istəyirsiniz?": {"en": "How do you want to enter the information?", "ru": "Как вы хотите ввести информацию?"},
    "Əl ilə forma yazın və ya barkod, kod, səs ilə sürətli doldurun.": {"en": "Fill out the form manually or use a barcode, code, or voice for quick entry.", "ru": "Заполните форму вручную или используйте штрих-код, код или голос для быстрого ввода."},
    "Barkodu Göstər": {"en": "Show Barcode", "ru": "Показать штрих-код"},
    "Səslə Əlavə Et": {"en": "Add by Voice", "ru": "Добавить голосом"},
    "Kodu Əl İlə Daxil Et": {"en": "Enter Code Manually", "ru": "Введите код вручную"},
    "Toxum miqdarı, vahidi və qiyməti daxil edin.": {"en": "Enter seed quantity, unit, and price.", "ru": "Введите количество семян, единицу измерения и цену."},
    "Yeni heyvan alışını və ya əlavə olunmasını yazın.": {"en": "Record a new animal purchase or addition.", "ru": "Запишите покупку или добавление нового животного."},
    "Ferma üçün alınan və ya əlavə olunan aləti yazın.": {"en": "Record tools purchased or added for the farm.", "ru": "Запишите инструменты, купленные или добавленные для фермы."}
}

base_dir = "locale"
for lang in ["en", "ru"]:
    path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
    if os.path.exists(path):
        po = polib.pofile(path)
        existing = {entry.msgid for entry in po}
        for k, v in translations.items():
            if k not in existing:
                po.append(polib.POEntry(msgid=k, msgstr=v[lang]))
        po.save(path)

print("Dictionary appended.")

import os
import polib

extra_translations = {
    # UI Buttons/Cards
    "Hazır məhsul": {"en": "Finished product", "ru": "Готовая продукция"},
    "Barkod Skan Et": {"en": "Scan Barcode", "ru": "Сканировать штрих-код"},
    "Səslə Əlavə Et": {"en": "Add by Voice", "ru": "Добавить голосом"},
    "Kodu Əllə Yaz": {"en": "Enter Code Manually", "ru": "Введите код вручную"},
    "Skanı Dayandır": {"en": "Stop Scanning", "ru": "Остановить сканирование"},
    
    # Form Titles & Subtitles
    "Xərc formu": {"en": "Expense form", "ru": "Форма расхода"},
    "Xərc formu açıldı.": {"en": "Expense form opened.", "ru": "Форма расхода открыта."},
    "Satış formu": {"en": "Sale form", "ru": "Форма продажи"},
    "Heyvan formu": {"en": "Animal form", "ru": "Форма животного"},
    "Toxum formu": {"en": "Seed form", "ru": "Форма семян"},
    "Alət formu": {"en": "Tool form", "ru": "Форма инструмента"},
    "Təsərrüfat formu": {"en": "Farm form", "ru": "Форма хозяйства"},
    
    # Headers and descriptions
    "Xərci necə daxil etmək istəyirsiniz?": {"en": "How do you want to enter the expense?", "ru": "Как вы хотите ввести расход?"},
    "Xərci əl ilə yazın və ya barkod, kod, səs ilə sürətli doldurun.": {
        "en": "Enter the expense manually or use barcode, code, or voice for quick entry.",
        "ru": "Введите расход вручную или используйте штрих-код, код или голос для быстрого ввода."
    },
    "Satışı necə daxil etmək istəyirsiniz?": {"en": "How do you want to enter the sale?", "ru": "Как вы хотите ввести продажу?"},
    "Satışı əl ilə yazın və ya barkod, kod, səs ilə sürətli doldurun.": {
        "en": "Enter the sale manually or use barcode, code, or voice for quick entry.",
        "ru": "Введите продажу вручную или используйте штрих-код, код или голос для быстрого ввода."
    },
    
    # Various UI
    "Scan olunan barkoda uyğun form açıldı.": {"en": "Form opened based on the scanned barcode.", "ru": "Форма открыта на основе отсканированного штрих-кода."},
    "Nə əlavə edirsiniz?": {"en": "What are you adding?", "ru": "Что вы добавляете?"},
    "Ana Kateqoriya": {"en": "Main Category", "ru": "Основная категория"},
    "Alt Kateqoriya": {"en": "Sub Category", "ru": "Подкатегория"},
    "Məhsul növü": {"en": "Product type", "ru": "Тип продукта"},
    "Ölçü vahidi": {"en": "Unit of measurement", "ru": "Единица измерения"},
    "Miqdar": {"en": "Quantity", "ru": "Количество"},
    "Məbləğ": {"en": "Amount", "ru": "Сумма"},
    "Tarix": {"en": "Date", "ru": "Дата"},
    "Əlavə məlumat": {"en": "Additional info", "ru": "Дополнительная информация"},
    "Xərci Saxla": {"en": "Save Expense", "ru": "Сохранить расход"},
    "Satışı Saxla": {"en": "Save Sale", "ru": "Сохранить продажу"},
    "Heyvanı Saxla": {"en": "Save Animal", "ru": "Сохранить животное"},
    "Toxumu Saxla": {"en": "Save Seed", "ru": "Сохранить семена"},
    "Aləti Saxla": {"en": "Save Tool", "ru": "Сохранить инструмент"},
    "Məhsulu Saxla": {"en": "Save Product", "ru": "Сохранить продукт"},
}

base_dir = "locale"
for lang in ["en", "ru"]:
    path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
    if os.path.exists(path):
        po = polib.pofile(path)
        existing = {entry.msgid for entry in po}
        # Reactivate any matches first
        for entry in po.obsolete_entries():
            if entry.msgid in extra_translations:
                entry.comment = "" # remove obsolete comment if it exists in comments
                # Note: polib doesn't have a direct 'reactivate' but we can append it back
                po.append(polib.POEntry(msgid=entry.msgid, msgstr=extra_translations[entry.msgid][lang]))
        
        # Add new ones
        for k, v in extra_translations.items():
            if k not in existing:
                po.append(polib.POEntry(msgid=k, msgstr=v[lang]))
        po.save(path)

print("UI translations appended.")

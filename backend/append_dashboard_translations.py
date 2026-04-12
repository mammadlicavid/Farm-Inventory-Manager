import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import polib

DASHBOARD_WORDS = {
    "Bu gün nə etmək istəyirsiniz?": {"en": "What do you want to do today?", "ru": "Что вы хотите сделать сегодня?"},
    "Salam, {{ name }}. Buradan stok əlavə edə, qalığa baxa, satış yaza və xərcləri qeyd edə bilərsiniz.": {"en": "Hello, %(name)s. From here you can add stock, view balance, record sales, and note expenses.", "ru": "Здравствуйте, %(name)s. Отсюда вы можете добавить запасы, посмотреть остаток, записать продажи и отметить расходы."},
    "Diqqət tələb edən {{ count }} xəbərdarlıq və xatırlatma var.": {"en": "There are %(count)s alerts and reminders requiring attention.", "ru": "Есть %(count)s предупреждений и напоминаний, требующих внимания."},
    "Əsas hərəkətlər": {"en": "Main actions", "ru": "Основные действия"},
    "Bu səhifədə nə edə bilərsiniz?": {"en": "What can you do on this page?", "ru": "Что вы можете сделать на этой странице?"},
    "Ən vacib işlər birbaşa açılır. Kateqoriya axtarmağa ehtiyac yoxdur.": {"en": "The most important tasks open directly. No need to search for a category.", "ru": "Самые важные задачи открываются напрямую. Нет необходимости искать категорию."},
    "Stok əlavə et": {"en": "Add stock", "ru": "Добавить сток"},
    "Heyvan, toxum, alət və ya məhsul daxil edin.": {"en": "Enter animal, seed, tool, or product.", "ru": "Введите животное, семя, инструмент или продукт."},
    "Stoka bax": {"en": "View stock", "ru": "Смотреть сток"},
    "Qalıq miqdarını görün və sayımı düzəldin.": {"en": "View the remaining quantity and adjust the count.", "ru": "Посмотрите остаток и скорректируйте количество."},
    "Məhsul sat": {"en": "Sell product", "ru": "Продать продукт"},
    "Satışdan gələn məbləği və miqdarı yazın.": {"en": "Enter the amount and quantity from the sale.", "ru": "Укажите сумму и количество от продажи."},
    "Xərc yaz": {"en": "Record expense", "ru": "Записать расход"},
    "Yem, yanacaq, gübrə və digər xərcləri qeyd edin.": {"en": "Record feed, fuel, fertilizer, and other expenses.", "ru": "Запишите расходы на корм, топливо, удобрения и другие."},
    "Maliyyə və tərəfdaşlar": {"en": "Finance and partners", "ru": "Финансы и партнеры"},
    "Əlavə iş bölmələri": {"en": "Additional work sections", "ru": "Дополнительные рабочие разделы"},
    "Hesabat hazırlamaq və təchizatçı siyahısını idarə etmək üçün bu bölmələri açın.": {"en": "Open these sections to prepare reports and manage the supplier list.", "ru": "Откройте эти разделы для подготовки отчетов и управления списком поставщиков."},
    "Hesabatlar": {"en": "Reports", "ru": "Отчеты"},
    "Gəlir, xərc, vergi və yüklənə bilən hesabatları açın.": {"en": "Open reports for income, expenses, taxes, and downloadable reports.", "ru": "Откройте отчеты по доходам, расходам, налогам и загружаемые отчеты."},
    "Təchizatçılar": {"en": "Suppliers", "ru": "Поставщики"},
    "Əlaqə məlumatı və alış etdiyiniz tərəfdaş siyahısını görün.": {"en": "View contact information and the list of partners you purchased from.", "ru": "Посмотрите контактную информацию и список партнеров, у которых вы совершали покупки."},
    "Bu həftə yeni əlavə": {"en": "New additions this week", "ru": "Новые поступления на этой неделе"},
    "Bu həftə əlavə olunan yeni stok qeydləri": {"en": "New stock records added this week", "ru": "Новые записи запасов, добавленные на этой неделе"},
    "Bu həftə gəlir": {"en": "Income this week", "ru": "Доход на этой неделе"},
    "Satış və digər gəlirlər": {"en": "Sales and other income", "ru": "Продажи и прочие доходы"},
    "Bu həftə xərc": {"en": "Expense this week", "ru": "Расход на этой неделе"},
    "Alışlar və gündəlik xərclər": {"en": "Purchases and daily expenses", "ru": "Покупки и ежедневные расходы"},
    "Həftəlik balans": {"en": "Weekly balance", "ru": "Недельный баланс"},
    "Gəlir və xərc fərqi": {"en": "Difference between income and expense", "ru": "Разница между доходом и расходом"},
    "Başlamaq üçün": {"en": "To get started", "ru": "Для начала"},
    "İş axını": {"en": "Workflow", "ru": "Рабочий процесс"},
    "Dashboard → Əlavə et → İzləyin → Satın": {"en": "Dashboard → Add → Track → Sell", "ru": "Приборная панель → Добавить → Отслеживать → Продать"},
    "İlk dəfə istifadə edirsinizsə, aşağıdakı addımlar proqramı ilk 10 saniyədə başa düşməyə kömək edəcək.": {"en": "If you are using it for the first time, the following steps will help you understand the program.", "ru": "Если вы используете его впервые, следующие шаги помогут вам понять программу."},
    "Hər gün eyni axınla işləyin: əvvəl əlavə edin, sonra izləyin, sonda satış və xərci yazın.": {"en": "Work with the same flow every day: first add, then track, and finally record sales and expenses.", "ru": "Каждый день работайте по одной и той же схеме: сначала добавьте, затем отследите, в конце запишите продажи и расходы."},
    "Əvvəl stok əlavə edin": {"en": "First add stock", "ru": "Сначала добавьте запасы"},
    "Yeni heyvanı, toxumu, aləti və ya hazır məhsulu yazın.": {"en": "Record a new animal, seed, tool, or finished product.", "ru": "Запишите новое животное, семя, инструмент или готовый продукт."},
    "Sonra qalığa baxın": {"en": "Then check the balance", "ru": "Затем проверьте остаток"},
    "Stok səhifəsində hansı məhsuldan nə qədər qaldığını görün.": {"en": "See how much of each product is left on the stock page.", "ru": "Посмотрите, сколько каждого продукта осталось на странице запасов."},
    "Satışı yazın": {"en": "Record sale", "ru": "Записать продажу"},
    "Məhsul satanda gəliri dərhal qeyd edin ki, stok azalsın və qazanc görünsün.": {"en": "When selling a product, record the income immediately so that stock decreases and profit represents.", "ru": "При продаже продукта сразу запишите доход, чтобы запасы уменьшились, и отобразилась прибыль."},
    "Azalan stoklar": {"en": "Decreasing stocks", "ru": "Уменьшающиеся запасы"},
    "Kritik səviyyəyə düşən məhsul sayı: {{ count }}": {"en": "Number of products falling to a critical level: %(count)s", "ru": "Количество продуктов, упавших до критического уровня: %(count)s"},
    "Limit": {"en": "Limit", "ru": "Лимит"},
    "Minimum limit": {"en": "Minimum limit", "ru": "Минимальный лимит"},
    "Hazırda kritik stok xəbərdarlığı yoxdur": {"en": "There is currently no critical stock alert", "ru": "В настоящее время нет критического предупреждения о запасах"},
    "Qalıq minimum limitdən aşağı düşəndə burada avtomatik görünəcək.": {"en": "It will automatically appear here when the balance falls below the minimum limit.", "ru": "Оно автоматически появится здесь, когда остаток опустится ниже минимального предела."},
    "Ətraflı bölmələr": {"en": "Detailed sections", "ru": "Подробные разделы"},
    "Bölmələr üzrə işləyin": {"en": "Work by sections", "ru": "Работа по разделам"},
    "Ayrı-ayrı inventar və maliyyə səhifələrinə birbaşa keçin.": {"en": "Go directly to individual inventory and financial pages.", "ru": "Перейдите прямо на отдельные страницы инвентаря и финансов."},
    "Heyvanlar": {"en": "Animals", "ru": "Животные"},
    "Alış, satış və say dəyişimini izləyin.": {"en": "Track purchase, sale, and quantity changes.", "ru": "Отслеживайте покупки, продажи и изменения количества."},
    "Toxumlar": {"en": "Seeds", "ru": "Семена"},
    "Toxum ehtiyatını və əlavə qeydləri açın.": {"en": "Open seed reserves and additional notes.", "ru": "Откройте запасы семян и дополнительные заметки."},
    "Alətlər": {"en": "Tools", "ru": "Инструменты"},
    "İş alətlərinin sayını və vəziyyətini görün.": {"en": "View the number and condition of tools.", "ru": "Посмотрите количество и состояние инструментов."},
    "Hazır məhsullar": {"en": "Finished products", "ru": "Готовые продукты"},
    "Süd, yumurta, tərəvəz və digər məhsulları açın.": {"en": "Open milk, eggs, vegetables, and other products.", "ru": "Откройте молоко, яйца, овощи и другие продукты."},
    "Gəlirlər": {"en": "Incomes", "ru": "Доходы"},
    "Bütün satış və gəlir qeydlərini görün.": {"en": "View all sales and income records.", "ru": "Посмотреть все записи о продажах и доходах."},
    "Xərclər": {"en": "Expenses", "ru": "Расходы"},
    "Yem, yanacaq və digər xərcləri yoxlayın.": {"en": "Check feed, fuel, and other expenses.", "ru": "Проверьте расходы на корм, топливо и другие."},
    "Hazırda": {"en": "Currently", "ru": "В настоящее время"},
    "Xatırlatmalar və ehtiyat xəbərdarlıqları": {"en": "Reminders and stock alerts", "ru": "Напоминания и предупреждения о запасах"},
    "Ümumi diqqət": {"en": "Total attention", "ru": "Общее внимание"},
    "Dashboard-da görünən ümumi say": {"en": "Total number appearing on Dashboard", "ru": "Общее количество, отображаемое на приборной панели"},
    "Ehtiyat xəbərdarlığı": {"en": "Stock alert", "ru": "Предупреждение о запасах"},
    "Kritik və azalan stoklar": {"en": "Critical and decreasing stocks", "ru": "Критичные и уменьшающиеся запасы"},
    "Xatırlatma": {"en": "Reminder", "ru": "Напоминание"},
    "Əl ilə əlavə etdiyiniz gözləyən qeydlər": {"en": "Pending records you added manually", "ru": "Ожидающие записи, которые вы добавили вручную"},
    "Ehtiyat xəbərdarlıqları ({{ count }})": {"en": "Stock alerts (%(count)s)", "ru": "Предупреждения о запасах (%(count)s)"},
    "Fərdi limit": {"en": "Custom limit", "ru": "Пользовательский предел"},
    "Hazırda aktiv ehtiyat xəbərdarlığı yoxdur.": {"en": "There is currently no active stock alert.", "ru": "В настоящее время нет активного предупреждения о запасах."},
    "Limit qur": {"en": "Set limit", "ru": "Установить лимит"},
    "Ana kateqoriya": {"en": "Main category", "ru": "Главная категория"},
    "Ana kateqoriya seçin": {"en": "Select main category", "ru": "Выберите главную категорию"},
    "Alt kateqoriya": {"en": "Subcategory", "ru": "Подкатегория"},
    "Alt kateqoriya seçin": {"en": "Select subcategory", "ru": "Выберите подкатегорию"},
    "Məhsul növü": {"en": "Product type", "ru": "Тип продукта"},
    "Məhsul növü seçin": {"en": "Select product type", "ru": "Выберите тип продукта"},
    "Xəbərdarlıq həddi": {"en": "Alert threshold", "ru": "Порог предупреждения"},
    "Məs: 20": {"en": "Ex: 20", "ru": "Например: 20"},
    "Yadda saxla": {"en": "Save", "ru": "Сохранить"},
    "Əvvəlcə anbara məhsul əlavə edin, sonra limit qura biləcəksiniz.": {"en": "First add product to the warehouse, then you can set a limit.", "ru": "Сначала добавьте продукт на склад, затем вы сможете установить лимит."},
    "Limitləri göstər": {"en": "Show limits", "ru": "Показать лимиты"},
    "Sistem": {"en": "System", "ru": "Система"},
    "Düzəliş et": {"en": "Edit", "ru": "Изменить"},
    "Hələ əlavə edilmiş limit yoxdur.": {"en": "No limit added yet.", "ru": "Предел пока не добавлен."},
    "Xatırlatmalar ({{ count }})": {"en": "Reminders (%(count)s)", "ru": "Напоминания (%(count)s)"},
    "Yeni xatırlatma əlavə et": {"en": "Add new reminder", "ru": "Добавить новое напоминание"},
    "Vaksinasiya": {"en": "Vaccination", "ru": "Вакцинация"},
    "Ödəniş": {"en": "Payment", "ru": "Оплата"},
    "Əkin": {"en": "Planting", "ru": "Посадка"},
    "Ehtiyat": {"en": "Reserve", "ru": "Запас"},
    "Digər": {"en": "Other", "ru": "Другое"},
    "Avtomatik": {"en": "Automatic", "ru": "Автоматически"},
    "Gözləyən xatırlatma yoxdur.": {"en": "No pending reminders.", "ru": "Нет ожидающих напоминаний."},
    "Tamamlanmış ({{ count }})": {"en": "Completed (%(count)s)", "ru": "Завершено (%(count)s)"},
    "Tamamlanmış xatırlatma yoxdur.": {"en": "No completed reminders.", "ru": "Нет завершенных напоминаний."},
    "Yeni xatırlatma": {"en": "New reminder", "ru": "Новое напоминание"},
    "Başlıq": {"en": "Title", "ru": "Заголовок"},
    "Məs: Qoyunlara vaksinasiya": {"en": "Ex: Vaccinating sheep", "ru": "Например: Вакцинация овец"},
    "Kateqoriya": {"en": "Category", "ru": "Категория"},
    "Tarix": {"en": "Date", "ru": "Дата"},
    "Əlavə et": {"en": "Add", "ru": "Добавить"},
    "Limiti düzəlt": {"en": "Edit limit", "ru": "Изменить предел"},
    "Yenilə": {"en": "Update", "ru": "Обновить"},
    "Ferma idarəsi": {"en": "Farm management", "ru": "Управление фермой"}
}

base_dir = "locale"
for lang in ["en", "ru"]:
    po_file_path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
    if os.path.exists(po_file_path):
        po = polib.pofile(po_file_path)
        existing_msgids = {entry.msgid for entry in po}
        
        for key, val in DASHBOARD_WORDS.items():
            # In blocktrans, {{ name }} becomes %(name)s. Wait, Django extracts as the exact key but replaces variables.
            # If the extraction used `extract_strings.py`, it extracted exactly what's in the template.
            # BUT Django `{% blocktrans %}` expects msgid to be the text with %(var)s.
            # If the user's template has `Salam, {{ name }}.` inside blocktrans, Django natively looks for `Salam, %(name)s.`.
            # Let's add BOTH versions to be absolutely safe against template modifications.
            dj_key = key.replace("{{ count }}", "%(count)s").replace("{{ name }}", "%(name)s").replace("\n", "").strip()
            
            # Version 1 (exact literal match from trans tag)
            if key not in existing_msgids:
                po.append(polib.POEntry(msgid=key, msgstr=val.get(lang, key)))
                existing_msgids.add(key)
            
            # Version 2 (django blocktrans syntax)
            if dj_key not in existing_msgids:
                po.append(polib.POEntry(msgid=dj_key, msgstr=val.get(lang, dj_key)))
                existing_msgids.add(dj_key)
                
        po.save(po_file_path)
        print(f"Updated {po_file_path}")

print("Done")

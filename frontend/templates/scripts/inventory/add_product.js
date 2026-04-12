{% load i18n common_extras static %}
document.addEventListener("DOMContentLoaded", function () {
    const expenseData = JSON.parse(document.getElementById("inventory-expense-data").textContent);
    const animalData = JSON.parse(document.getElementById("inventory-animal-data").textContent);
    const seedData = JSON.parse(document.getElementById("inventory-seed-data").textContent);
    const toolData = JSON.parse(document.getElementById("inventory-tool-data").textContent);
    const farmData = JSON.parse(document.getElementById("inventory-farm-data").textContent);
    const incomeCategories = JSON.parse(document.getElementById("inventory-income-categories").textContent);
    const incomeData = JSON.parse(document.getElementById("inventory-income-data").textContent);

    const scannerWrapper = document.getElementById("scanner-wrapper");
    const barcodeBtn = document.getElementById("barcode-btn");
    const barcodeBtnIcon = document.getElementById("barcode-btn-icon");
    const barcodeBtnLabel = document.getElementById("barcode-btn-label");
    const manualCodeToggleBtn = document.getElementById("manual-code-toggle-btn");
    const manualCodeWrapper = document.getElementById("manual-code-wrapper");
    const manualCodeInput = document.getElementById("manual-code-input");
    const manualCodeSubmitBtn = document.getElementById("manual-code-submit-btn");
    const voiceBtn = document.getElementById("voice-input-btn");
    const voiceBtnIcon = document.getElementById("voice-input-btn-icon");
    const voiceBtnLabel = document.getElementById("voice-input-btn-label");
    const voiceResult = document.getElementById("voice-result");
    const voiceRecorderPanel = document.getElementById("voice-recorder-panel");
    const voiceRecorderStatus = document.getElementById("voice-recorder-status");
    const voiceLevelBars = Array.from(document.querySelectorAll("#voice-level-meter .voice-level-bar"));
    const resultBox = document.getElementById("scan-result");
    const videoEl = document.getElementById("barcode-video");
    const formShell = document.getElementById("dynamic-form-shell");
    const activeFormTitle = document.getElementById("active-form-title");
    const activeFormSubtitle = document.getElementById("active-form-subtitle");
    const manualPanelButtons = Array.from(document.querySelectorAll("[data-manual-panel]"));
    const urlParams = new URLSearchParams(window.location.search);
    const addPageMode = ["income", "expense"].includes(urlParams.get("form")) ? urlParams.get("form") : "stock";
    const addPageFormTypes = new Set(
        addPageMode === "income"
            ? ["income"]
            : addPageMode === "expense"
                ? ["expense"]
                : manualPanelButtons.map((button) => button.dataset.manualPanel),
    );
    const zeroPriceSourceConfigs = [
        { formType: "animal", priceInputId: "animal-price", wrapId: "animal-zero-price-source-wrap", selectId: "animal-zero-price-source" },
        { formType: "seed", priceInputId: "seed-price", wrapId: "seed-zero-price-source-wrap", selectId: "seed-zero-price-source" },
        { formType: "tool", priceInputId: "tool-price", wrapId: "tool-zero-price-source-wrap", selectId: "tool-zero-price-source" },
        { formType: "farm", priceInputId: "farm-price", wrapId: "farm-zero-price-source-wrap", selectId: "farm-zero-price-source" },
    ];

    const weightUnitSystem = "{% unit_system request.user %}";
    const volumeUnitSystem = "{% volume_system request.user %}";
    const weightUnits = weightUnitSystem === "lb" ? ["kq", "qram"] : ["kq", "qram", "ton"];
    const volumeUnits = volumeUnitSystem === "gallon" ? ["litr"] : ["litr", "ml"];
    const allUnits = [...weightUnits, ...volumeUnits, "ədəd", "dəstə", "bağlama"];
    const KG_PER_POUND = 0.45359237;
    const GRAMS_PER_OUNCE = 28.349523125;
    const LITERS_PER_GALLON = 3.785411784;
    let codeReader = null;
    let controls = null;
    let scanning = false;
    let mediaRecorder = null;
    let voiceStream = null;
    let voiceChunks = [];
    let listening = false;
    let voiceTranscribing = false;
    let voiceAudioContext = null;
    let voiceAnalyser = null;
    let voiceAnimationFrame = null;
    let voiceLevelData = null;
    let voiceVocabularyWords = [];
    let voiceVocabularyPhrases = [];
    let voiceVocabularyReady = false;
    let voiceVocabularyScheduled = false;
    let barcodeLibraryPromise = null;

    const panelTitles = { expense: "{% trans 'Xərc formu' %}", income: "{% trans 'Satış formu' %}", animal: "{% trans 'Heyvan formu' %}", seed: "{% trans 'Toxum formu' %}", tool: "{% trans 'Alət formu' %}", farm: "{% trans 'Təsərrüfat formu' %}" };
    const voiceFormFilledSubtitles = {
        expense: "{% trans 'Səsdən xərc formu dolduruldu.' %}",
        income: "{% trans 'Səsdən satış formu dolduruldu.' %}",
        animal: "{% trans 'Səsdən heyvan formu dolduruldu.' %}",
        seed: "{% trans 'Səsdən toxum formu dolduruldu.' %}",
        tool: "{% trans 'Səsdən alət formu dolduruldu.' %}",
        farm: "{% trans 'Səsdən məhsul formu dolduruldu.' %}",
    };
    const voiceAcceptedMessages = {
        expense: "{% trans 'Səs qəbul olundu və xərc formu dolduruldu.' %}",
        income: "{% trans 'Səs qəbul olundu və satış formu dolduruldu.' %}",
        animal: "{% trans 'Səs qəbul olundu və heyvan formu dolduruldu.' %}",
        seed: "{% trans 'Səs qəbul olundu və toxum formu dolduruldu.' %}",
        tool: "{% trans 'Səs qəbul olundu və alət formu dolduruldu.' %}",
        farm: "{% trans 'Səs qəbul olundu və məhsul formu dolduruldu.' %}",
    };
    const todayIso = "{{ today|date:'Y-m-d' }}";
    const currentYear = Number("{{ today|date:'Y' }}");
    const currentMonth = Number("{{ today|date:'m' }}");
    const voiceInputLanguage = "{{ voice_input_language|default:'system'|escapejs }}";
    const activeVoiceLanguage = voiceInputLanguage === "system" ? "{{ request.LANGUAGE_CODE|default:'az'|escapejs }}".split("-")[0] : voiceInputLanguage;
    const voiceLanguagePhraseMap = {
        en: {
            "add income": "gelir elave et",
            "income add": "gelir elave et",
            "add expense": "xerc elave et",
            "expense add": "xerc elave et",
            "no paid in cash": "qeyd paid in cash",
            "no cash payment": "qeyd cash payment",
            "no cash": "qeyd cash",
            "add animal": "heyvan elave et",
            "add seed": "toxum elave et",
            "add tool": "alet elave et",
            "add product": "mehsul elave et",
            "additional info": "elave melumat",
            "note": "qeyd",
            "quantity": "miqdar",
            "amount": "mebleg",
            "price": "qiymet",
            "weight": "ceki",
            "date": "tarix",
            "gender": "cinsiyyet",
            "identification number": "identifikasiya",
            "id number": "id",
            "today": "bugun",
            "yesterday": "dunen",
            "tomorrow": "sabah",
            "day": "gun",
            "days": "gun",
            "week": "hefte",
            "weeks": "hefte",
            "ago": "evvel",
            "before": "evvel",
            "after": "sonra",
            "male": "erkek",
            "female": "disi",
            "piece": "eded",
            "pieces": "eded",
            "bundle": "deste",
            "pack": "baglama",
            "liter": "litr",
            "liters": "litr",
            "litre": "litr",
            "litres": "litr",
            "milliliter": "ml",
            "milliliters": "ml",
            "gram": "qram",
            "grams": "qram",
            "kilogram": "kiloqram",
            "kilograms": "kiloqram",
            "kilo": "kilo",
            "ton": "ton",
            "tons": "ton",
            "cow milk": "inek sudu",
            "buffalo milk": "camis sudu",
            "goat milk": "keci sudu",
            "cow cheese": "inek pendiri",
            "buffalo cheese": "camis pendiri",
            "goat cheese": "keci pendiri",
            "yogurt": "qatiq",
            "ayran": "ayran",
            "butter": "kere yagi",
            "cream": "qaymaq",
            "chicken egg": "toyuq yumurtasi",
            "turkey egg": "hinduska yumurtasi",
            "goose egg": "qaz yumurtasi",
            "duck egg": "ordek yumurtasi",
            "quail egg": "bildircin yumurtasi",
            "beef": "mal eti",
            "buffalo meat": "camis eti",
            "sheep meat": "qoyun eti",
            "goat meat": "keci eti",
            "chicken meat": "toyuq eti",
            "turkey meat": "hinduska eti",
            "goose meat": "qaz eti",
            "duck meat": "ordek eti",
            "quail meat": "bildircin eti",
            "cow": "inek",
            "calf": "dana",
            "buffalo": "camis",
            "sheep": "qoyun",
            "goat": "keci",
            "chicken": "toyuq",
            "turkey": "hinduska",
            "goose": "qaz",
            "duck": "ordek",
            "quail": "bildircin",
            "horse": "at",
            "donkey": "essek",
            "mule": "qatir",
            "wheat": "bugda",
            "barley": "arpa",
            "rye": "covdar",
            "oats": "velemir",
            "corn": "qargidali",
            "maize": "qargidali",
            "rice": "celtik",
            "alfalfa": "yonca",
            "tomato": "pomidor",
            "cucumber": "xiyar",
            "pepper": "biber",
            "eggplant": "badimcan",
            "lettuce": "kahi",
            "spinach": "ispanaq",
            "onion": "sogan",
            "garlic": "sarimsaq",
            "potato": "kartof",
            "apple": "alma",
            "pear": "armud",
            "peach": "saftali",
            "apricot": "erik",
            "cherry": "albalı",
            "pomegranate": "nar",
            "grape": "uzum",
            "plum": "gavali",
            "quince": "heyva",
            "honey": "bal",
            "wax": "mum",
            "seed": "toxum",
            "tool": "alet",
            "product": "mehsul",
            "animal": "heyvan",
            "expense": "xerc",
            "income": "gelir",
            "sale": "satis",
            "zero": "sifir",
            "one": "bir",
            "two": "iki",
            "three": "uc",
            "four": "dord",
            "five": "bes",
            "six": "alti",
            "seven": "yeddi",
            "eight": "sekkiz",
            "nine": "doqquz",
            "ten": "on",
            "twenty": "iyirmi",
            "thirty": "otuz",
            "forty": "qirx",
            "fifty": "elli",
            "sixty": "altmis",
            "seventy": "yetmis",
            "eighty": "seksen",
            "ninety": "doxsan",
            "hundred": "yuz",
            "thousand": "min",
            "point": "noqte",
        },
        ru: {
            "добавить доход": "gelir elave et",
            "добавить расход": "xerc elave et",
            "добавить животное": "heyvan elave et",
            "добавить семена": "toxum elave et",
            "добавить инструмент": "alet elave et",
            "добавить продукт": "mehsul elave et",
            "дополнительная информация": "elave melumat",
            "заметка": "qeyd",
            "количество": "miqdar",
            "сумма": "mebleg",
            "цена": "qiymet",
            "вес": "ceki",
            "дата": "tarix",
            "пол": "cinsiyyet",
            "идентификационный номер": "identifikasiya",
            "номер": "id",
            "сегодня": "bugun",
            "вчера": "dunen",
            "завтра": "sabah",
            "день": "gun",
            "дней": "gun",
            "неделя": "hefte",
            "недели": "hefte",
            "недель": "hefte",
            "назад": "evvel",
            "через": "sonra",
            "до": "evvel",
            "самец": "erkek",
            "самка": "disi",
            "штука": "eded",
            "штук": "eded",
            "упаковка": "baglama",
            "пучок": "deste",
            "литр": "litr",
            "литра": "litr",
            "литров": "litr",
            "миллилитр": "ml",
            "грамм": "qram",
            "грамма": "qram",
            "граммов": "qram",
            "килограмм": "kiloqram",
            "килограмма": "kiloqram",
            "килограммов": "kiloqram",
            "кило": "kilo",
            "тонна": "ton",
            "тонны": "ton",
            "тонн": "ton",
            "коровье молоко": "inek sudu",
            "буйволиное молоко": "camis sudu",
            "козье молоко": "keci sudu",
            "говядина": "mal eti",
            "мясо буйвола": "camis eti",
            "баранина": "qoyun eti",
            "козлятина": "keci eti",
            "куриное мясо": "toyuq eti",
            "мясо индейки": "hinduska eti",
            "мясо гуся": "qaz eti",
            "мясо утки": "ordek eti",
            "корова": "inek",
            "теленок": "dana",
            "буйвол": "camis",
            "овца": "qoyun",
            "коза": "keci",
            "курица": "toyuq",
            "индейка": "hinduska",
            "гусь": "qaz",
            "утка": "ordek",
            "перепелка": "bildircin",
            "лошадь": "at",
            "осел": "essek",
            "мул": "qatir",
            "пшеница": "bugda",
            "ячмень": "arpa",
            "рожь": "covdar",
            "овес": "velemir",
            "кукуруза": "qargidali",
            "рис": "celtik",
            "люцерна": "yonca",
            "помидор": "pomidor",
            "огурец": "xiyar",
            "перец": "biber",
            "баклажан": "badimcan",
            "салат": "kahi",
            "шпинат": "ispanaq",
            "лук": "sogan",
            "чеснок": "sarimsaq",
            "картофель": "kartof",
            "яблоко": "alma",
            "груша": "armud",
            "персик": "saftali",
            "абрикос": "erik",
            "вишня": "albalı",
            "гранат": "nar",
            "виноград": "uzum",
            "слива": "gavali",
            "айва": "heyva",
            "мед": "bal",
            "воск": "mum",
            "семена": "toxum",
            "инструмент": "alet",
            "продукт": "mehsul",
            "животное": "heyvan",
            "расход": "xerc",
            "доход": "gelir",
            "продажа": "satis",
            "ноль": "sifir",
            "один": "bir",
            "два": "iki",
            "три": "uc",
            "четыре": "dord",
            "пять": "bes",
            "шесть": "alti",
            "семь": "yeddi",
            "восемь": "sekkiz",
            "девять": "doqquz",
            "десять": "on",
            "двадцать": "iyirmi",
            "тридцать": "otuz",
            "сорок": "qirx",
            "пятьдесят": "elli",
            "шестьдесят": "altmis",
            "семьдесят": "yetmis",
            "восемьдесят": "seksen",
            "девяносто": "doxsan",
            "сто": "yuz",
            "тысяча": "min",
            "точка": "noqte",
        },
    };
    const voiceLanguageTokenMap = {
        en: {
            add: "elave",
            income: "gelir",
            expense: "xerc",
            sale: "satis",
            animal: "heyvan",
            animals: "heyvan",
            seed: "toxum",
            seeds: "toxum",
            tool: "alet",
            tools: "alet",
            product: "mehsul",
            products: "mehsul",
            quantity: "miqdar",
            amount: "mebleg",
            price: "qiymet",
            weight: "ceki",
            date: "tarix",
            gender: "cinsiyyet",
            note: "qeyd",
            notes: "qeyd",
            additional: "elave",
            info: "melumat",
            information: "melumat",
            id: "id",
            identification: "identifikasiya",
            today: "bugun",
            yesterday: "dunen",
            tomorrow: "sabah",
            day: "gun",
            days: "gun",
            week: "hefte",
            weeks: "hefte",
            ago: "evvel",
            before: "evvel",
            after: "sonra",
            male: "erkek",
            female: "disi",
            liter: "litr",
            liters: "litr",
            litre: "litr",
            litres: "litr",
            manat: "manat",
            milliliter: "ml",
            milliliters: "ml",
            gram: "qram",
            grams: "qram",
            kilogram: "kiloqram",
            kilograms: "kiloqram",
            kilo: "kilo",
            ton: "ton",
            tons: "ton",
            piece: "eded",
            pieces: "eded",
            bundle: "deste",
            bundles: "deste",
            pack: "baglama",
            packs: "baglama",
            cow: "inek",
            calf: "dana",
            buffalo: "camis",
            sheep: "qoyun",
            goat: "keci",
            chicken: "toyuq",
            turkey: "hinduska",
            goose: "qaz",
            duck: "ordek",
            quail: "bildircin",
            horse: "at",
            donkey: "essek",
            mule: "qatir",
            milk: "sudu",
            cheese: "pendiri",
            yogurt: "qatiq",
            cream: "qaymaq",
            butter: "kere",
            egg: "yumurtasi",
            eggs: "yumurtasi",
            meat: "eti",
            honey: "bal",
            wax: "mum",
            wheat: "bugda",
            barley: "arpa",
            rye: "covdar",
            oats: "velemir",
            corn: "qargidali",
            maize: "qargidali",
            rice: "celtik",
            alfalfa: "yonca",
            tomato: "pomidor",
            tomatoes: "pomidor",
            cucumber: "xiyar",
            cucumbers: "xiyar",
            pepper: "biber",
            peppers: "biber",
            eggplant: "badimcan",
            lettuce: "kahi",
            spinach: "ispanaq",
            onion: "sogan",
            onions: "sogan",
            garlic: "sarimsaq",
            potato: "kartof",
            potatoes: "kartof",
            apple: "alma",
            apples: "alma",
            pear: "armud",
            pears: "armud",
            peach: "saftali",
            peaches: "saftali",
            apricot: "erik",
            apricots: "erik",
            cherry: "albali",
            cherries: "albali",
            pomegranate: "nar",
            pomegranates: "nar",
            grape: "uzum",
            grapes: "uzum",
            plum: "gavali",
            plums: "gavali",
            quince: "heyva",
            fertilizer: "gubre",
            fuel: "yanacaq",
            diesel: "dizel",
            gasoline: "benzin",
            veterinary: "baytarliq",
            vaccine: "peyvend",
            vaccination: "peyvend",
            medicine: "derman",
            herbicide: "herbisid",
            water: "suvarma",
            irrigation: "suvarma",
            zero: "sifir",
            one: "bir",
            two: "iki",
            three: "uc",
            four: "dord",
            five: "bes",
            six: "alti",
            seven: "yeddi",
            eight: "sekkiz",
            nine: "doqquz",
            ten: "on",
            twenty: "iyirmi",
            thirty: "otuz",
            forty: "qirx",
            fifty: "elli",
            sixty: "altmis",
            seventy: "yetmis",
            eighty: "seksen",
            ninety: "doxsan",
            hundred: "yuz",
            thousand: "min",
            point: "noqte",
        },
        ru: {
            добавить: "elave",
            доход: "gelir",
            расход: "xerc",
            продажа: "satis",
            животное: "heyvan",
            животные: "heyvan",
            семя: "toxum",
            семена: "toxum",
            инструмент: "alet",
            инструменты: "alet",
            продукт: "mehsul",
            продукты: "mehsul",
            количество: "miqdar",
            сумма: "mebleg",
            цена: "qiymet",
            вес: "ceki",
            дата: "tarix",
            пол: "cinsiyyet",
            заметка: "qeyd",
            заметки: "qeyd",
            дополнительная: "elave",
            информация: "melumat",
            номер: "id",
            идентификация: "identifikasiya",
            сегодня: "bugun",
            вчера: "dunen",
            завтра: "sabah",
            день: "gun",
            дней: "gun",
            неделя: "hefte",
            недели: "hefte",
            недель: "hefte",
            назад: "evvel",
            после: "sonra",
            через: "sonra",
            самец: "erkek",
            самка: "disi",
            литр: "litr",
            литра: "litr",
            литров: "litr",
            манат: "manat",
            миллилитр: "ml",
            грамм: "qram",
            грамма: "qram",
            граммов: "qram",
            килограмм: "kiloqram",
            килограмма: "kiloqram",
            килограммов: "kiloqram",
            кило: "kilo",
            тонна: "ton",
            тонны: "ton",
            тонн: "ton",
            штука: "eded",
            штук: "eded",
            упаковка: "baglama",
            упаковки: "baglama",
            пучок: "deste",
            корова: "inek",
            теленок: "dana",
            буйвол: "camis",
            овца: "qoyun",
            коза: "keci",
            курица: "toyuq",
            индейка: "hinduska",
            гусь: "qaz",
            утка: "ordek",
            перепелка: "bildircin",
            лошадь: "at",
            осел: "essek",
            мул: "qatir",
            молоко: "sudu",
            сыр: "pendiri",
            йогурт: "qatiq",
            сливки: "qaymaq",
            масло: "kere",
            яйцо: "yumurtasi",
            яйца: "yumurtasi",
            мясо: "eti",
            мед: "bal",
            воск: "mum",
            пшеница: "bugda",
            ячмень: "arpa",
            рожь: "covdar",
            овес: "velemir",
            кукуруза: "qargidali",
            рис: "celtik",
            люцерна: "yonca",
            помидор: "pomidor",
            помидоры: "pomidor",
            огурец: "xiyar",
            огурцы: "xiyar",
            перец: "biber",
            баклажан: "badimcan",
            салат: "kahi",
            шпинат: "ispanaq",
            лук: "sogan",
            чеснок: "sarimsaq",
            картофель: "kartof",
            яблоко: "alma",
            груша: "armud",
            персик: "saftali",
            абрикос: "erik",
            вишня: "albali",
            гранат: "nar",
            виноград: "uzum",
            слива: "gavali",
            айва: "heyva",
            удобрение: "gubre",
            топливо: "yanacaq",
            дизель: "dizel",
            бензин: "benzin",
            ветеринарный: "baytarliq",
            вакцина: "peyvend",
            вакцинация: "peyvend",
            лекарство: "derman",
            гербицид: "herbisid",
            вода: "suvarma",
            орошение: "suvarma",
            ноль: "sifir",
            один: "bir",
            два: "iki",
            три: "uc",
            четыре: "dord",
            пять: "bes",
            шесть: "alti",
            семь: "yeddi",
            восемь: "sekkiz",
            девять: "doqquz",
            десять: "on",
            двадцать: "iyirmi",
            тридцать: "otuz",
            сорок: "qirx",
            пятьдесят: "elli",
            шестьдесят: "altmis",
            семьдесят: "yetmis",
            восемьдесят: "seksen",
            девяносто: "doxsan",
            сто: "yuz",
            тысяча: "min",
            точка: "noqte",
        },
    };
    const voiceLanguagePhraseEntries = Object.fromEntries(
        Object.entries(voiceLanguagePhraseMap).map(([lang, map]) => [lang, Object.entries(map).sort((a, b) => b[0].length - a[0].length)]),
    );
    const voiceLanguageTokenKeys = Object.fromEntries(
        Object.entries(voiceLanguageTokenMap).map(([lang, map]) => [lang, Object.keys(map).sort((a, b) => b.length - a.length)]),
    );
    const voiceNativeConfig = {
        en: {
            formTypePatterns: {
                expense: [/\badd\s+expense\b/, /\bexpense\b/],
                income: [/\badd\s+income\b/, /\bincome\b/, /\bsale\b/],
                animal: [/\badd\s+animal\b/, /\banimal\b/],
                seed: [/\badd\s+seed\b/, /\bseed\b/],
                tool: [/\badd\s+tool\b/, /\btool\b/],
                farm: [/\badd\s+product\b/, /\bproduct\b/],
            },
            actionPrefixes: {
                expense: ["add expense", "expense add", "expense"],
                income: ["add income", "income add", "income", "sale"],
                animal: ["add animal", "animal"],
                seed: ["add seed", "seed"],
                tool: ["add tool", "tool"],
                farm: ["add product", "product"],
            },
            stopTokens: ["quantity", "amount", "price", "weight", "date", "gender", "id", "identification", "additional", "info", "information", "note", "today", "yesterday", "tomorrow", "ago", "before", "after", "day", "days", "week", "weeks", "manat", "liter", "liters", "litre", "litres", "milliliter", "milliliters", "gram", "grams", "kilogram", "kilograms", "kilo", "ton", "tons", "piece", "pieces", "bundle", "bundles", "pack", "packs"],
        },
        ru: {
            formTypePatterns: {
                expense: [/\bдобавить\s+расход\b/, /\bрасход\b/],
                income: [/\bдобавить\s+доход\b/, /\bдоход\b/, /\bпродажа\b/],
                animal: [/\bдобавить\s+животное\b/, /\bживотное\b/],
                seed: [/\bдобавить\s+семен[а-я]*\b/, /\bсемен[а-я]*\b/],
                tool: [/\bдобавить\s+инструмент\b/, /\bинструмент\b/],
                farm: [/\bдобавить\s+продукт\b/, /\bпродукт\b/],
            },
            actionPrefixes: {
                expense: ["добавить расход", "расход"],
                income: ["добавить доход", "доход", "продажа"],
                animal: ["добавить животное", "животное"],
                seed: ["добавить семена", "добавить семя", "семена", "семя"],
                tool: ["добавить инструмент", "инструмент"],
                farm: ["добавить продукт", "продукт"],
            },
            stopTokens: ["количество", "сумма", "цена", "вес", "дата", "пол", "номер", "идентификация", "дополнительная", "информация", "заметка", "сегодня", "вчера", "завтра", "назад", "через", "после", "день", "дней", "неделя", "недели", "недель", "манат", "литр", "литра", "литров", "миллилитр", "грамм", "грамма", "граммов", "килограмм", "килограмма", "килограммов", "кило", "тонна", "тонны", "тонн", "штука", "штук", "упаковка", "упаковки", "пучок"],
        },
    };

    function fillOptions(select, rows, placeholder, mapFn) {
        select.innerHTML = "";
        const first = document.createElement("option");
        first.value = "";
        first.textContent = placeholder;
        select.appendChild(first);
        rows.forEach((row) => {
            const option = document.createElement("option");
            const mapped = mapFn(row);
            option.value = mapped.value;
            option.textContent = mapped.label;
            if (mapped.dataset) {
                Object.entries(mapped.dataset).forEach(([key, val]) => { option.dataset[key] = val; });
            }
            select.appendChild(option);
        });
    }

    function setActionState(activeKey) {
        barcodeBtn.classList.toggle("is-active", activeKey === "scan");
        manualCodeToggleBtn.classList.toggle("is-active", activeKey === "manual");
        voiceBtn.classList.toggle("is-active", activeKey === "voice");
    }

    function syncManualPanelSelection(activeFormType) {
        manualPanelButtons.forEach((button) => {
            button.classList.toggle("is-active", button.dataset.manualPanel === activeFormType);
        });
    }

    function syncBarcodeButtonLabel() {
        if (scanning) {
            barcodeBtnLabel.textContent = "{% trans 'Skanı Dayandır' %}";
            barcodeBtnIcon.className = "fa-solid fa-circle-stop";
        } else {
            barcodeBtnLabel.textContent = "{% trans 'Barkod Skan Et' %}";
            barcodeBtnIcon.className = "fa-solid fa-camera";
        }
        barcodeBtn.classList.toggle("is-scanning", scanning);
    }

    function syncAnimalIdentificationState() {
        const quantityInput = document.getElementById("animal-quantity");
        const idInput = document.getElementById("animal-id");
        const parsedQuantity = parseInt(quantityInput.value || "1", 10);
        if (Math.abs(parsedQuantity) !== 1) {
            idInput.value = "";
            idInput.disabled = true;
            idInput.placeholder = "{% trans 'Miqdar ±1 olmadıqda ID yazılmır' %}";
            return;
        }
        idInput.disabled = false;
        idInput.placeholder = "{% trans 'Məsələn: AZ12345' %}";
    }

    function setResultMessage(message, isError = false) {
        resultBox.textContent = message;
        resultBox.classList.toggle("is-error", Boolean(isError));
    }

    function handleBlockedBarcode(formType) {
        let message = "";
        if (addPageMode === "income") {
            message = "{% trans 'Bu səhifədə yalnız satış barkodları oxunur.' %}";
        } else if (addPageMode === "expense") {
            message = "{% trans 'Bu səhifədə yalnız xərc barkodları oxunur.' %}";
        } else if (formType === "income") {
            message = "{% trans 'Satış barkodu bu səhifə üçün deyil.' %}";
        } else if (formType === "expense") {
            message = "{% trans 'Xərc barkodu bu səhifə üçün deyil.' %}";
        }
        if (!message) return false;
        setResultMessage(message, true);
        return true;
    }

    function handleBlockedForm(formType) {
        if (addPageFormTypes.has(formType)) return false;
        let message = "";
        if (addPageMode === "income") {
            message = "{% trans 'Bu səhifə satış üçündür. Satış forması açıq saxlanıldı.' %}";
        } else if (addPageMode === "expense") {
            message = "{% trans 'Bu səhifə xərc üçündür. Xərc forması açıq saxlanıldı.' %}";
        } else if (formType === "income") {
            message = "{% trans 'Satış bu səhifədə deyil. “Məhsul sat” bölməsindən istifadə edin.' %}";
        } else if (formType === "expense") {
            message = "{% trans 'Xərc bu səhifədə deyil. “Xərc yaz” bölməsindən istifadə edin.' %}";
        }
        if (!message) return false;
        clearActiveForms();
        manualCodeWrapper.hidden = true;
        setActionState(null);
        setResultMessage(message, true);
        return true;
    }

    function setVoiceResult(message) {
        voiceResult.hidden = !message;
        if (!message) {
            voiceResult.innerHTML = "";
            return;
        }

        const safeMessage = String(message)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        const lines = safeMessage.split("\n").filter(Boolean);
        voiceResult.innerHTML = lines.map((line) => {
            const lineClass = line.startsWith("Deyilən:")
                ? "voice-result-line voice-result-line-heard"
                : (line.startsWith("Təxmin edilən:")
                    ? "voice-result-line voice-result-line-guess"
                    : "voice-result-line");
            if (line.startsWith("Deyilən:")) {
                return `<div class="${lineClass}"><span class="voice-result-label">{% trans "Deyilən:" %}</span>${line.slice("Deyilən:".length)}</div>`;
            }
            if (line.startsWith("Təxmin edilən:")) {
                return `<div class="${lineClass}"><span class="voice-result-label">{% trans "Təxmin edilən:" %}</span>${line.slice("Təxmin edilən:".length)}</div>`;
            }
            return `<div class="${lineClass}">${line}</div>`;
        }).join("");
    }

    function syncVoiceButtonLabel() {
        if (voiceTranscribing) {
            voiceBtnLabel.textContent = "{% trans 'Səs emal olunur...' %}";
            voiceBtnIcon.className = "fa-solid fa-spinner fa-spin";
        } else if (listening) {
            voiceBtnLabel.textContent = "{% trans 'Yazını Bitir' %}";
            voiceBtnIcon.className = "fa-solid fa-circle-stop";
        } else {
            voiceBtnLabel.textContent = "{% trans 'Səslə Əlavə Et' %}";
            voiceBtnIcon.className = "fa-solid fa-microphone";
        }
        voiceBtn.classList.toggle("is-recording", listening);
        voiceBtn.classList.toggle("is-transcribing", voiceTranscribing);
    }

    function setVoiceRecorderVisible(isVisible, statusMessage) {
        voiceRecorderPanel.hidden = !isVisible;
        if (statusMessage) voiceRecorderStatus.textContent = statusMessage;
        if (!isVisible) {
            voiceLevelBars.forEach((bar, index) => {
                bar.style.height = `${10 + ((index % 3) * 4)}px`;
            });
        }
    }

    function stopVoiceLevelMeter() {
        if (voiceAnimationFrame) {
            cancelAnimationFrame(voiceAnimationFrame);
            voiceAnimationFrame = null;
        }
        if (voiceAudioContext) {
            voiceAudioContext.close().catch(() => {});
            voiceAudioContext = null;
        }
        voiceAnalyser = null;
        voiceLevelData = null;
    }

    function startVoiceLevelMeter(stream) {
        stopVoiceLevelMeter();
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextClass) return;
        voiceAudioContext = new AudioContextClass();
        const source = voiceAudioContext.createMediaStreamSource(stream);
        voiceAnalyser = voiceAudioContext.createAnalyser();
        voiceAnalyser.fftSize = 64;
        voiceAnalyser.smoothingTimeConstant = 0.82;
        voiceLevelData = new Uint8Array(voiceAnalyser.frequencyBinCount);
        source.connect(voiceAnalyser);

        const renderLevels = () => {
            if (!voiceAnalyser || !voiceLevelData) return;
            voiceAnalyser.getByteFrequencyData(voiceLevelData);
            const bucketSize = Math.max(1, Math.floor(voiceLevelData.length / voiceLevelBars.length));
            voiceLevelBars.forEach((bar, index) => {
                const start = index * bucketSize;
                const end = Math.min(voiceLevelData.length, start + bucketSize);
                let sum = 0;
                for (let pointer = start; pointer < end; pointer += 1) sum += voiceLevelData[pointer];
                const average = end > start ? sum / (end - start) : 0;
                const height = Math.max(10, Math.min(56, 10 + (average / 255) * 46));
                bar.style.height = `${height}px`;
            });
            voiceAnimationFrame = requestAnimationFrame(renderLevels);
        };

        renderLevels();
    }

    function titleCaseAz(value) {
        const text = String(value || "").trim();
        if (!text) return "";
        return text
            .split(" ")
            .filter(Boolean)
            .map((part) => part.charAt(0).toLocaleUpperCase("az") + part.slice(1))
            .join(" ");
    }

    function getCsrfToken() {
        const cookie = document.cookie
            .split(";")
            .map((part) => part.trim())
            .find((part) => part.startsWith("csrftoken="));
        return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
    }

    function normalizeVoiceLanguageSourceToken(token) {
        const sourceLanguage = activeVoiceLanguage === "ru" ? "ru" : "en";
        return String(token || "")
            .toLocaleLowerCase(sourceLanguage)
            .replace(/ё/g, "е")
            .replace(/['’`"]/g, "")
            .replace(/(.)\1{2,}/g, "$1")
            .trim();
    }

    function normalizeNativeVoiceText(value) {
        const sourceLanguage = activeVoiceLanguage === "ru" ? "ru" : "en";
        return String(value || "")
            .toLocaleLowerCase(sourceLanguage)
            .replace(/ё/g, "е")
            .replace(/[.,;:!?-]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function voiceLanguageOrderedLetterScore(source, target) {
        const left = normalizeVoiceLanguageSourceToken(source);
        const right = normalizeVoiceLanguageSourceToken(target);
        if (!left || !right) return 0;
        let matchCount = 0;
        let pointer = 0;
        for (const char of left) {
            while (pointer < right.length && right[pointer] !== char) pointer += 1;
            if (pointer < right.length) {
                matchCount += 1;
                pointer += 1;
            }
        }
        return matchCount / left.length;
    }

    function voiceLanguageSoundKey(token) {
        const normalized = normalizeVoiceLanguageSourceToken(token);
        if (!normalized) return "";
        if (activeVoiceLanguage === "ru") {
            return normalized
                .replace(/ий|ый|ой/g, "i")
                .replace(/[ая]/g, "a")
                .replace(/[еэ]/g, "e")
                .replace(/[ёо]/g, "o")
                .replace(/[ую]/g, "u")
                .replace(/ж/g, "z")
                .replace(/ш|щ/g, "s")
                .replace(/ч/g, "c")
                .replace(/ц/g, "s")
                .replace(/й/g, "i")
                .replace(/ъ|ь/g, "")
                .replace(/([аеёиоуыэюя])\1+/g, "$1")
                .replace(/[аеёиоуыэюя]/g, "");
        }
        return normalized
            .replace(/ph/g, "f")
            .replace(/ck/g, "k")
            .replace(/qu/g, "k")
            .replace(/q/g, "k")
            .replace(/x/g, "ks")
            .replace(/c(?=[eiy])/g, "s")
            .replace(/c/g, "k")
            .replace(/w/g, "v")
            .replace(/y/g, "i")
            .replace(/z/g, "s")
            .replace(/([aeiou])\1+/g, "$1")
            .replace(/[aeiou]/g, "");
    }

    function voiceLanguageMaxDistance(source, target) {
        const size = Math.max(String(source || "").length, String(target || "").length);
        if (size <= 4) return 1;
        if (size <= 7) return 2;
        return 3;
    }

    function rawSimilarityScore(a, b) {
        const left = String(a || "");
        const right = String(b || "");
        if (!left || !right) return 0;
        if (left === right) return 1;
        return 1 - (levenshteinDistance(left, right) / Math.max(left.length, right.length, 1));
    }

    function resolveVoiceLanguageToken(token) {
        const tokenMap = voiceLanguageTokenMap[activeVoiceLanguage] || {};
        const tokenKeys = voiceLanguageTokenKeys[activeVoiceLanguage] || [];
        const normalized = normalizeVoiceLanguageSourceToken(token);
        if (!normalized) return "";
        if (tokenMap[normalized]) return tokenMap[normalized];

        const candidates = [normalized];
        if (activeVoiceLanguage === "en") {
            if (normalized.endsWith("ies") && normalized.length > 4) candidates.push(`${normalized.slice(0, -3)}y`);
            if (normalized.endsWith("es") && normalized.length > 3) candidates.push(normalized.slice(0, -2));
            if (normalized.endsWith("s") && normalized.length > 2) candidates.push(normalized.slice(0, -1));
            if (normalized.endsWith("ed") && normalized.length > 3) candidates.push(normalized.slice(0, -2));
            if (normalized.endsWith("ing") && normalized.length > 5) candidates.push(normalized.slice(0, -3));
        } else if (activeVoiceLanguage === "ru") {
            [
                "иями", "ями", "ами", "ями", "ого", "ему", "ому", "ыми", "ими",
                "ой", "ий", "ый", "ая", "яя", "ое", "ее", "ов", "ев", "ом", "ем",
                "ах", "ях", "ам", "ям", "ою", "ею", "у", "ю", "а", "я", "ы", "и",
                "е", "о",
            ].forEach((ending) => {
                if (normalized.endsWith(ending) && normalized.length - ending.length >= 3) {
                    candidates.push(normalized.slice(0, -ending.length));
                }
            });
        }

        for (const candidate of candidates) {
            if (tokenMap[candidate]) return tokenMap[candidate];
        }

        let best = "";
        let bestScore = 0;
        let bestDistance = Infinity;
        tokenKeys.forEach((source) => {
            const distance = levenshteinDistance(normalized, source);
            if (distance > voiceLanguageMaxDistance(normalized, source)) return;
            const score = Math.max(
                voiceLanguageOrderedLetterScore(normalized, source) * 0.95,
                1 - (distance / Math.max(normalized.length, source.length, 1)),
                rawSimilarityScore(voiceLanguageSoundKey(normalized), voiceLanguageSoundKey(source)) * 0.97,
            );
            if (score > bestScore || (score === bestScore && distance < bestDistance)) {
                best = source;
                bestScore = score;
                bestDistance = distance;
            }
        });
        if (best && bestScore >= 0.74) return tokenMap[best];
        return normalized;
    }

    function applyVoiceLanguageAliases(value) {
        const sourceLanguage = activeVoiceLanguage === "ru" ? "ru" : "en";
        let normalized = String(value || "").toLocaleLowerCase(sourceLanguage);
        normalized = normalized
            .replace(/[.,;:!?-]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
        const entries = voiceLanguagePhraseEntries[activeVoiceLanguage];
        if (!entries) return normalized;
        let result = ` ${normalized} `;
        entries.forEach(([source, target]) => {
            const escaped = source.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            result = result.replace(new RegExp(`(^| )${escaped}(?= |$)`, "g"), `$1${target}`);
        });
        result = result
            .trim()
            .split(/\s+/)
            .map(resolveVoiceLanguageToken)
            .join(" ");
        return result
            .replace(/\b([a-z0-9]+)(sudu|pendiri|yumurtasi|eti)\b/g, "$1 $2")
            .replace(/\b(elave)\s+(melumat)\b/g, "elave melumat")
            .replace(/\s+/g, " ")
            .trim();
    }

    function guessVoiceFormTypeNative(text) {
        const config = voiceNativeConfig[activeVoiceLanguage];
        if (!config) return "";
        const normalized = normalizeNativeVoiceText(text);
        for (const [formType, patterns] of Object.entries(config.formTypePatterns)) {
            if (patterns.some((pattern) => pattern.test(normalized))) return formType;
        }
        return "";
    }

    function extractNativeEntitySegment(text, formType) {
        const config = voiceNativeConfig[activeVoiceLanguage];
        if (!config || !formType) return "";
        let subject = normalizeNativeVoiceText(text);
        (config.actionPrefixes[formType] || []).forEach((prefix) => {
            if (subject.startsWith(`${prefix} `)) subject = subject.slice(prefix.length).trim();
            else if (subject === prefix) subject = "";
        });
        const tokens = subject.split(" ").filter(Boolean);
        const result = [];
        for (const token of tokens) {
            if (/^\d+(?:[.,]\d+)?$/.test(token)) break;
            if (config.stopTokens.includes(token)) break;
            result.push(token);
        }
        if (!result.length) return "";
        return sanitizeEntityTokens(applyVoiceLanguageAliases(result.join(" ")).split(" ")).join(" ").trim();
    }

    function normalizeVoiceText(value) {
        const prepared = activeVoiceLanguage === "az" ? String(value || "") : applyVoiceLanguageAliases(value);
        return prepared
            .toLocaleLowerCase("az")
            .replace(/ə/g, "e")
            .replace(/ı/g, "i")
            .replace(/ö/g, "o")
            .replace(/ü/g, "u")
            .replace(/ş/g, "s")
            .replace(/ç/g, "c")
            .replace(/ğ/g, "g")
            .replace(/[.,;:!?-]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function levenshteinDistance(a, b) {
        const left = String(a || "");
        const right = String(b || "");
        if (!left) return right.length;
        if (!right) return left.length;
        const rows = Array.from({ length: left.length + 1 }, () => new Array(right.length + 1).fill(0));
        for (let i = 0; i <= left.length; i += 1) rows[i][0] = i;
        for (let j = 0; j <= right.length; j += 1) rows[0][j] = j;
        for (let i = 1; i <= left.length; i += 1) {
            for (let j = 1; j <= right.length; j += 1) {
                const cost = left[i - 1] === right[j - 1] ? 0 : 1;
                rows[i][j] = Math.min(
                    rows[i - 1][j] + 1,
                    rows[i][j - 1] + 1,
                    rows[i - 1][j - 1] + cost,
                );
            }
        }
        return rows[left.length][right.length];
    }

    function similarityScore(a, b) {
        const left = normalizeVoiceText(a);
        const right = normalizeVoiceText(b);
        if (!left || !right) return 0;
        if (left === right) return 1;
        const maxLength = Math.max(left.length, right.length);
        if (!maxLength) return 0;
        return 1 - (levenshteinDistance(left, right) / maxLength);
    }

    function phoneticVoiceKey(value) {
        const normalized = normalizeVoiceText(value);
        if (!normalized) return "";
        return normalized
            .replace(/ph/g, "f")
            .replace(/q/g, "g")
            .replace(/x/g, "h")
            .replace(/c/g, "j")
            .replace(/v/g, "w")
            .replace(/y/g, "i")
            .replace(/s\b/g, "z")
            .replace(/t(?=[aeiou])/g, "d")
            .replace(/p/g, "b")
            .replace(/([aeiou])\1+/g, "$1")
            .replace(/([bcdfghjklmnpqrstvwxyz])\1+/g, "$1")
            .replace(/[aeiou]/g, "")
            .replace(/w/g, "v")
            .replace(/j/g, "s")
            .trim();
    }

    function advancedSimilarityScore(a, b) {
        const left = normalizeVoiceText(a);
        const right = normalizeVoiceText(b);
        if (!left || !right) return 0;
        if (left === right) return 1;

        const direct = similarityScore(left, right);
        const phonetic = similarityScore(phoneticVoiceKey(left), phoneticVoiceKey(right));
        const prefix = left.startsWith(right) || right.startsWith(left) ? Math.min(left.length, right.length) / Math.max(left.length, right.length) : 0;
        return Math.max(direct, phonetic * 0.96, prefix * 0.93);
    }

    function entitySoundKey(value) {
        return normalizeVoiceText(value)
            .replace(/[ckqg]/g, "k")
            .replace(/[td]/g, "t")
            .replace(/[bp]/g, "b")
            .replace(/[szj]/g, "s")
            .replace(/[aeiou]/g, "")
            .replace(/(.)\1+/g, "$1");
    }

    function orderedLetterScore(source, target) {
        const left = normalizeVoiceText(source);
        const right = normalizeVoiceText(target);
        if (!left || !right) return 0;
        let matchCount = 0;
        let pointer = 0;
        for (const char of left) {
            while (pointer < right.length && right[pointer] !== char) pointer += 1;
            if (pointer < right.length) {
                matchCount += 1;
                pointer += 1;
            }
        }
        return matchCount / left.length;
    }

    const voiceKeywordCandidates = [
        "xerc", "elave", "et", "gelir", "satis", "heyvan", "toxum", "alet", "mehsul",
        "gubre", "pestisid", "baytarliq", "yem", "suvarma", "miqdar", "say", "eded", "dene",
        "mebleg", "qiymet", "ceki", "tarix", "cinsiyyet", "identifikasiya", "id",
        "elave melumat", "qeyd", "kateqoriya", "alt kateqoriya", "mehsul", "novu",
        "manat", "litr", "ml", "qram", "ton", "kiloqram", "kilogram", "kilo", "kq", "kg",
        "gun", "evvel", "qabaq", "sonra",
        "inek", "dana", "qoyun", "keci", "toyuq", "xoruz", "cuce", "at", "essek", "qatir", "it", "pisik", "ordek", "qaz", "hinduska",
        "yumurta", "sud", "pendir", "qatiq", "nehre yagi", "sor", "yun", "deri", "et", "bal", "mum",
        "bugda", "arpa", "qargidali", "yonca", "pambiq", "sogan", "kartof", "pomidor", "xiyar",
        "traktor", "kotan", "dirmiq", "bel", "kurek", "balta", "misar", "nasos", "mala", "qayci", "drel",
        "derman", "herbisid", "ot", "saman", "quvveli", "isiq", "qaz", "yanacaq", "benzin", "dizel", "solyarka", "maas", "emek haqqi", "peyvend", "iyne",
        "erkek", "disi", "dunen", "bugun", "sabah",
        "sifir", "bir", "iki", "uc", "dord", "bes", "alti", "yeddi", "sekkiz", "doqquz",
        "on", "iyirmi", "otuz", "qirx", "elli", "altmis", "yetmis", "seksen", "doxsan", "yuz", "min"
    ];
    const safeFuzzyKeywordCandidates = [
        "gelir", "xerc", "heyvan", "toxum", "alet", "mehsul", "elave", "et",
        "miqdar", "mebleg", "qiymet", "ceki", "manat",
        "dunen", "bugun", "sabah", "gun", "evvel", "qabaq", "sonra",
        "kilo", "kiloqram", "qram", "ton", "litr", "ml", "kq",
        "disi", "erkek",
    ];
    const spokenNumberTokens = new Set([
        "sifir", "bir", "iki", "uc", "dord", "bes", "alti", "yeddi", "sekkiz", "doqquz",
        "on", "iyirmi", "otuz", "qirx", "elli", "altmis", "yetmis", "seksen", "doxsan",
        "yuz", "min", "vergul", "noqte", "nokte",
    ]);
    const spokenNumberVocabulary = [
        "sifir", "bir", "iki", "uc", "dord", "bes", "alti", "yeddi", "sekkiz", "doqquz",
        "on", "iyirmi", "otuz", "qirx", "elli", "altmis", "yetmis", "seksen", "doxsan",
        "yuz", "min",
    ];
    const leadingEntityNoiseTokens = new Set([
        "elave", "et", "ed", "evvel", "evve", "qabaq", "sonra", "tarix", "qeyd",
        "heyvan", "gelir", "xerc", "satis", "toxum", "alet", "mehsul",
    ]);
    const entityBoundaryTokens = new Set([
        "miqdar", "say", "eded", "dene", "mebleg", "qiymet", "ceki", "tarix", "cinsiyyet",
        "id", "identifikasiya", "elave", "qeyd", "kateqoriya", "novu", "manat", "ton",
        "qram", "kiloqram", "kilogram", "kilo", "cilo", "kq", "kg", "litr", "ml",
        "gun", "evvel", "qabaq", "sonra", "bugun", "dunen", "sabah",
    ]);

    const voiceKeywordAliases = {
        "xerc": "xerc", "xerca": "xerc", "xerci": "xerc", "xerce": "xerc", "xercl": "xerc", "xerj": "xerc", "herc": "xerc", "xercin": "xerc", "xercg": "xerc", "sarc": "xerc", "serc": "xerc", "xeraci": "xerc", "iserc": "xerc", "dserc": "xerc", "xelcele": "xerc", "xelceleve": "xerc", "xelce": "xerc", "helcele": "xerc",
        "celir": "gelir", "celdir": "gelir", "caldir": "gelir", "cellir": "gelir", "cellr": "gelir", "gelr": "gelir", "geli": "gelir", "jelir": "gelir", "qelir": "gelir", "delir": "gelir", "telir": "gelir", "belir": "gelir", "pelir": "gelir", "selir": "gelir", "jeldir": "gelir",
        "elave": "elave", "elavi": "elave", "elavii": "elave", "elavı": "elave", "elav": "elave", "elaf": "elave", "elaveyet": "elave et", "elaveyat": "elave et", "alave": "elave", "elawa": "elave", "ilawe": "elave", "ilafe": "elave", "olave": "elave", "ilave": "elave",
        "et": "et", "it": "et", "ed": "et", "evid": "et", "edid": "et", "td": "et", "ad": "et", "at": "et",
        "cibre": "gubre", "cubre": "gubre", "cubra": "gubre", "cubreye": "gubre", "cubreni": "gubre", "cubren": "gubre", "gubre": "gubre", "gubra": "gubre", "qubre": "gubre", "kubre": "gubre", "pubre": "gubre", "dubre": "gubre",
        "mebleg": "mebleg", "mebeleg": "mebleg", "mebeleq": "mebleg", "mebelegi": "mebleg", "mebeleqi": "mebleg", "mebleq": "mebleg", "meblegi": "mebleg", "mablag": "mebleg", "meblag": "mebleg", "mevleg": "mebleg", "mevlaq": "mebleg", "mebleyi": "mebleg", "meblegh": "mebleg",
        "qiymet": "qiymet", "qimet": "qiymet", "gimet": "qiymet", "geymet": "qiymet", "giymet": "qiymet", "qiyma": "qiymet", "qeymet": "qiymet", "qiymeti": "qiymet", "qimeti": "qiymet", "kiymet": "qiymet", "dimet": "qiymet",
        "ceki": "ceki", "cekin": "ceki", "ceksi": "ceki", "seki": "ceki", "ceci": "ceki", "caki": "ceki", "cekisi": "ceki", "cek": "ceki", "ciyek": "ceki", "teki": "ceki", "deki": "ceki",
        "miqdar": "miqdar", "miqtar": "miqdar", "mikdar": "miqdar", "miktar": "miqdar", "miqra": "miqdar", "miqti": "miqdar", "miqdari": "miqdar", "diqdar": "miqdar",
        "toxum": "toxum", "tohum": "toxum", "toxmu": "toxum", "toxm": "toxum", "toxma": "toxum", "toxumu": "toxum", "doksum": "toxum",
        "alet": "alet", "alat": "alet", "aletd": "alet", "aleti": "alet", "aladh": "alet", "dadet": "alet",
        "heyvan": "heyvan", "hevan": "heyvan", "eyvan": "heyvan", "ayvan": "heyvan", "heyfan": "heyvan", "heyvani": "heyvan", "deyvan": "heyvan",
        "mehsul": "mehsul", "mexsul": "mehsul", "mesul": "mehsul", "mehs": "mehsul", "mehsulu": "mehsul", "dehsul": "mehsul",
        "bugda": "bugda", "buxta": "bugda", "buhta": "bugda", "bogda": "bugda", "bugta": "bugda", "bugde": "bugda", "buxda": "bugda", "pugda": "bugda", "taxil": "bugda", "buqda": "bugda", "dugda": "bugda",
        "inek": "inek", "inec": "inek", "inac": "inek", "inay": "inek", "ineh": "inek", "inekde": "inek", "ineyi": "inek", "idek": "inek", "anek": "inek", "ineksi": "inek", "iyin": "inek", "inane": "inek", "inaki": "inek", "ines": "inek", "ineci": "inek", "ineki": "inek", "iniki": "inek", "inki": "inek", "ini": "inek",
        "disi": "disi", "dis": "disi", "dishi": "disi", "tisi": "disi", "pisi": "disi", "disileri": "disi", "disiler": "disi", "disi": "disi",
        "erkek": "erkek", "erkey": "erkek", "erkeh": "erkek", "arkak": "erkek", "erkeyi": "erkek", "darkey": "erkek", "erkekleri": "erkek", "erkeği": "erkek", "erkegin": "erkek",
        "at": "at", "ata": "at", "ati": "at", "atı": "at", "atin": "at", "atını": "at",
        "sud": "sud", "sudu": "sud", "sudun": "sud", "sut": "sud", "sutu": "sud", "shut": "sud",
        "pendir": "pendir", "pendiri": "pendir", "pendirin": "pendir",
        "qatiq": "qatiq", "qatiqi": "qatiq", "qatigi": "qatiq", "gatig": "qatiq", "gatiq": "qatiq",
        "yumurta": "yumurta", "yumurtasi": "yumurta", "yumurtani": "yumurta", "yumrto": "yumurta",
        "yun": "yun", "yunu": "yun", "yunun": "yun",
        "bal": "bal", "bali": "bal", "balin": "bal",
        "mum": "mum", "mumu": "mum", "mumun": "mum",
        "et": "et", "eti": "et", "etini": "et", "etin": "et",
        "dunen": "dunen", "dunenki": "dunen", "donen": "dunen", "dun": "dunen", "dune": "dunen", "dunem": "dunen", "dunle": "dunen", "dune": "dunen", "tunen": "dunen",
        "gun": "gun", "yun": "gun", "gunu": "gun", "dun": "gun", "kun": "gun",
        "evvel": "evvel", "evve": "evvel", "ewel": "evvel", "evel": "evvel", "əvvəl": "evvel", "avval": "evvel",
        "qabaq": "qabaq", "qabax": "qabaq", "qabak": "qabaq", "kabaq": "qabaq",
        "sonra": "sonra", "sonrsa": "sonra",
        "dekabir": "dekabr", "dekabr": "dekabr", "deqabr": "dekabr", "dikabr": "dekabr",
        "kilo": "kilo", "ulo": "kilo", "kulo": "kilo", "qilo": "kilo", "kilu": "kilo", "kili": "kilo", "dilo": "kilo",
        "kiloqram": "kiloqram", "kilaqram": "kiloqram", "kilogram": "kiloqram", "kiliqram": "kiloqram",
        "kq": "kq", "kaqe": "kq", "keko": "kq", "dq": "kq",
        "manat": "manat", "manatd": "manat", "manad": "manat", "manot": "manat", "mana": "manat", "man": "manat", "manati": "manat", "danat": "manat",
        "elimanat": "elli manat", "elmanat": "elli manat", "ellimanat": "elli manat",
        "elli": "elli", "eli": "elli", "evli": "elli", "avli": "elli", "ellii": "elli", "delli": "elli",
        "onc": "on", "oncu": "on", "once": "on", "oncesi": "on", "don": "on",
        "bir": "bir", "biri": "bir", "pir": "bir", "biy": "bir", "dir": "bir",
        "iki": "iki", "ik": "iki", "iyi": "iki", "igi": "iki", "idi": "iki",
        "uc": "uc", "ush": "uc", "us": "uc", "uc": "uc",
        "dord": "dord", "tort": "dord", "dort": "dord", "dor": "dord",
        "bes": "bes", "bash": "bes", "bas": "bes", "bes": "bes",
        "alti": "alti", "alt": "alti", "altdi": "alti", "dalti": "alti",
        "yeddi": "yeddi", "yedi": "yeddi", "yeti": "yeddi", "yetdi": "yeddi", "dedi": "yeddi",
        "sekkiz": "sekkiz", "sekiz": "sekkiz", "sekgiz": "sekkiz", "segiz": "sekkiz", "dekiz": "sekkiz",
        "doqquz": "doqquz", "doquz": "doqquz", "dogguz": "doqquz", "togquz": "doqquz", "doqus": "doqquz",
        "iyirmi": "iyirmi", "yirmi": "iyirmi", "ikirmi": "iyirmi", "igirmi": "iyirmi", "iyirimi": "iyirmi", "igirimi": "iyirmi", "dirmi": "iyirmi",
        "otuz": "otuz", "otz": "otuz", "oduz": "otuz", "oqtu": "otuz", "dotu": "otuz",
        "qirx": "qirx", "girx": "qirx", "qirh": "qirx", "kix": "qirx", "qrx": "qirx", "dirx": "qirx",
        "altmis": "altmis", "atmis": "altmis", "atmisd": "altmis", "damis": "altmis",
        "yetmis": "yetmis", "yetmisd": "yetmis", "demis": "yetmis",
        "seksen": "seksen", "saxsan": "seksen", "seksan": "seksen", "saksan": "seksen", "daksan": "seksen",
        "doxsan": "doxsan", "duxsan": "doxsan", "toksan": "doxsan", "doksan": "doxsan", "doxdan": "doxsan",
        "yuz": "yuz", "yus": "yuz", "duz": "yuz",
        "min": "min", "mim": "min", "dim": "min"
    };

    function collectVoiceVocabulary() {
        if (voiceVocabularyReady) return;
        const words = new Set();
        const phrases = new Set();

        function addPhrase(value) {
            const normalized = normalizeVoiceText(value);
            if (!normalized) return;
            phrases.add(normalized);
            normalized.split(" ").filter(Boolean).forEach((word) => words.add(word));
        }

        voiceKeywordCandidates.forEach(addPhrase);
        Object.keys(voiceKeywordAliases).forEach(addPhrase);
        Object.values(voiceKeywordAliases).forEach(addPhrase);

        voiceVocabularyWords = Array.from(words).sort((a, b) => b.length - a.length);
        voiceVocabularyPhrases = Array.from(phrases).sort((a, b) => b.length - a.length);
        voiceVocabularyReady = true;
    }

    function ensureVoiceVocabularyReady() {
        if (!voiceVocabularyReady) collectVoiceVocabulary();
    }

    function scheduleVoiceVocabularyCollection() {
        if (voiceVocabularyReady || voiceVocabularyScheduled) return;
        voiceVocabularyScheduled = true;
        const run = () => {
            voiceVocabularyScheduled = false;
            collectVoiceVocabulary();
        };
        if (typeof window.requestIdleCallback === "function") {
            window.requestIdleCallback(run, { timeout: 1200 });
            return;
        }
        window.setTimeout(run, 250);
    }

    function ensureBarcodeLibraryLoaded() {
        if (window.ZXingBrowser) return Promise.resolve(window.ZXingBrowser);
        if (barcodeLibraryPromise) return barcodeLibraryPromise;
        barcodeLibraryPromise = new Promise((resolve, reject) => {
            const existingScript = document.querySelector('script[data-zxing-browser="true"]');
            if (existingScript) {
                existingScript.addEventListener("load", () => resolve(window.ZXingBrowser), { once: true });
                existingScript.addEventListener("error", () => reject(new Error("{% trans 'Scanner kitabxanası yüklənmədi.' %}")), { once: true });
                return;
            }
            const script = document.createElement("script");
            script.src = "https://cdn.jsdelivr.net/npm/@zxing/browser@0.1.5/umd/zxing-browser.min.js";
            script.async = true;
            script.dataset.zxingBrowser = "true";
            script.addEventListener("load", () => resolve(window.ZXingBrowser), { once: true });
            script.addEventListener("error", () => reject(new Error("{% trans 'Scanner kitabxanası yüklənmədi.' %}")), { once: true });
            document.head.appendChild(script);
        });
        return barcodeLibraryPromise;
    }

    function candidateCompatible(source, candidate) {
        const left = normalizeVoiceText(source);
        const right = normalizeVoiceText(candidate);
        if (!left || !right) return false;
        if (left[0] === right[0]) return true;
        if (advancedSimilarityScore(left, right) >= 0.72) return true;
        const leftPhonetic = phoneticVoiceKey(left);
        const rightPhonetic = phoneticVoiceKey(right);
        if (leftPhonetic && rightPhonetic && leftPhonetic[0] === rightPhonetic[0]) return true;
        if (left.length <= 4 || right.length <= 4) return false;
        return left.slice(0, 2) === right.slice(0, 2) || leftPhonetic.slice(0, 2) === rightPhonetic.slice(0, 2);
    }

    function keywordMaxDistance(token, candidate) {
        const size = Math.max(String(token || "").length, String(candidate || "").length);
        if (size <= 4) return 1;
        if (size <= 7) return 2;
        return 3;
    }

    function reduceRepeatedLetters(value) {
        return String(value || "").replace(/(.)\1{2,}/g, "$1");
    }

    function normalizeVoiceToken(token) {
        const normalized = reduceRepeatedLetters(normalizeVoiceText(token));
        if (!normalized) return normalized;
        if (voiceKeywordAliases[normalized]) return voiceKeywordAliases[normalized];
        if (normalized.length >= 4) {
            let best = "";
            let bestDistance = Infinity;
            let bestScore = 0;
            safeFuzzyKeywordCandidates.forEach((candidate) => {
                const distance = levenshteinDistance(normalized, candidate);
                const maxDistance = keywordMaxDistance(normalized, candidate);
                if (distance > maxDistance || !candidateCompatible(normalized, candidate)) return;
                const score = Math.max(
                    advancedSimilarityScore(normalized, candidate),
                    orderedLetterScore(normalized, candidate),
                );
                if (score < 0.62) return;
                if (distance < bestDistance || (distance === bestDistance && score > bestScore)) {
                    best = candidate;
                    bestDistance = distance;
                    bestScore = score;
                }
            });
            if (best) return best;
        }
        return normalized;
    }

    function normalizeCompoundEntityText(value) {
        return String(value || "")
            .replace(/\b([a-z0-9]+?)(?:\s+)?(?:etli|ətli|eti|əti)\b/g, "$1 eti")
            .replace(/\b([a-z0-9]+?)(?:\s+)?(?:sudu|südü|sudlu|südlü)\b/g, "$1 sudu")
            .replace(/\b([a-z0-9]+?)(?:\s+)?(?:yumurtasi|yumurtası)\b/g, "$1 yumurtasi")
            .replace(/\b([a-z0-9]+?)(?:\s+)?(?:pendiri)\b/g, "$1 pendiri");
    }

    function canonicalizeVoiceText(value) {
        const normalized = normalizeVoiceText(value);
        if (!normalized) return "";
        let result = normalizeCompoundEntityText(normalized)
            .replace(/\bgelirelave\b/g, "gelir elave")
            .replace(/\bgelirelaveet\b/g, "gelir elave et")
            .replace(/\bgelirela\b/g, "gelir elave")
            .replace(/\bgelirele\b/g, "gelir elave")
            .replace(/\bgelirelave\s+et\b/g, "gelir elave et")
            .replace(/\belaveyet\b/g, "elave et")
            .replace(/\belaveyat\b/g, "elave et")
            .replace(/\belaveyət\b/g, "elave et")
            .replace(/\bmanada\b/g, "manat")
            .replace(/\bmanatda\b/g, "manat")
            .replace(/\beli\s*manat\b/g, "elli manat")
            .replace(/\belimanat\b/g, "elli manat")
            .replace(/\belli\s*manat\b/g, "elli manat")
            .replace(/\binecsuzdu\b/g, "inek sudu")
            .replace(/\bineksuzdu\b/g, "inek sudu")
            .replace(/\binecsudu\b/g, "inek sudu")
            .replace(/\bineksudu\b/g, "inek sudu")
            .replace(/\binec\s+suzdu\b/g, "inek sudu")
            .replace(/\binek\s+suzdu\b/g, "inek sudu")
            .replace(/\binec\s+sudu\b/g, "inek sudu")
            .replace(/\binek\s+sudu\b/g, "inek sudu")
            .replace(/\bhevde\b/g, "hefte")
            .replace(/\bhevdə\b/g, "hefte")
            .replace(/\bhavde\b/g, "hefte")
            .replace(/\bhafte\b/g, "hefte")
            .replace(/\bheftevvel\b/g, "hefte evvel")
            .replace(/\bhefteevvel\b/g, "hefte evvel")
            .replace(/\bheftevevel\b/g, "hefte evvel")
            .replace(/\bhefteve\b/g, "hefte evvel")
            .replace(/\bice hefte evvel\b/g, "iki hefte evvel")
            .replace(/\bice hefte eve\b/g, "iki hefte evvel")
            .replace(/\bice hefte evve\b/g, "iki hefte evvel")
            .replace(/\bhindi\s+dus?q(?:a|ay)?eti\b/g, "hinduska eti")
            .replace(/\bhindi\s+dus?q(?:a|ay)?eyti\b/g, "hinduska eti")
            .replace(/\bhindi\s+dus?q(?:a|ay)?ati\b/g, "hinduska eti")
            .replace(/\bhindus?qeti\b/g, "hinduska eti")
            .replace(/\bhindus?qati\b/g, "hinduska eti")
            .replace(/\bhindus?qeti\b/g, "hinduska eti")
            .replace(/\bhinduskaeti\b/g, "hinduska eti")
            .replace(/\b(bir|iki|uc|dord|bes|alti|yeddi|sekkiz|doqquz|on|iyirmi|otuz|qirx|elli|altmis|yetmis|seksen|doxsan|yuz|min)(cilo|kiloqram|kilogram|kilo|kq|kg|qram|ton|litr|ml|manat)\b/g, "$1 $2")
            .replace(/\bon\s*kilo\b/g, "on kilo")
            .replace(/\bceki\s+ne\s+qeder\b/g, "ceki")
            .replace(/\bmiqdar\s+ne\s+qeder\b/g, "miqdar")
            .replace(/\bqiymeti\b/g, "qiymet")
            .replace(/\bmeblegi\b/g, "mebleg")
            .replace(/\bcekisi\b/g, "ceki")
            .replace(/\bmiqdari\b/g, "miqdar")
            .replace(/\btarixi\b/g, "tarix")
            .replace(/\bxerci\b/g, "xerc")
            .replace(/\bmehsulu\b/g, "mehsul")
            .replace(/\btohumu\b/g, "toxum")
            .replace(/\baleti\b/g, "alet")
            .replace(/\bheyvani\b/g, "heyvan")
            .replace(/\belave it\b/g, "elave et")
            .replace(/\belave id\b/g, "elave et")
            .replace(/\belave idi\b/g, "elave et")
            .replace(/\bgelir elave id\b/g, "gelir elave et")
            .replace(/\bgelir elave it\b/g, "gelir elave et")
            .replace(/\bxerc elave id\b/g, "xerc elave et")
            .split(" ")
            .filter(Boolean)
            .map(normalizeVoiceToken)
            .join(" ")
            .replace(/\belave et\b/g, "elave et")
            .replace(/\bxerc elave et\b/g, "xerc elave et")
            .replace(/\bgelir elave et\b/g, "gelir elave et");

        voiceVocabularyPhrases.forEach((phrase) => {
            if (result.includes(phrase)) return;
            const phraseTokens = phrase.split(" ").filter(Boolean);
            const resultTokens = result.split(" ").filter(Boolean);
            if (phraseTokens.length < 2 || resultTokens.length < phraseTokens.length) return;

            for (let index = 0; index <= resultTokens.length - phraseTokens.length; index += 1) {
                const chunk = resultTokens.slice(index, index + phraseTokens.length);
                let scoreTotal = 0;
                for (let chunkIndex = 0; chunkIndex < phraseTokens.length; chunkIndex += 1) {
                    scoreTotal += advancedSimilarityScore(chunk[chunkIndex], phraseTokens[chunkIndex]);
                }
                const averageScore = scoreTotal / phraseTokens.length;
                if (averageScore >= 0.72) {
                    resultTokens.splice(index, phraseTokens.length, ...phraseTokens);
                    result = resultTokens.join(" ");
                    break;
                }
            }
        });

        return result;
    }

    function bestSpokenNumberCandidate(token) {
        const normalized = reduceRepeatedLetters(normalizeVoiceText(token));
        if (!normalized || /^\d+(?:[.,]\d+)?$/.test(normalized)) return normalized;
        const normalizedKeyword = normalizeVoiceToken(token);
        if (normalizedKeyword && !spokenNumberTokens.has(normalizedKeyword) && (
            safeFuzzyKeywordCandidates.includes(normalizedKeyword) ||
            entityBoundaryTokens.has(normalizedKeyword) ||
            leadingEntityNoiseTokens.has(normalizedKeyword)
        )) {
            return "";
        }
        const aliased = voiceKeywordAliases[normalized] || normalized;
        if (spokenNumberTokens.has(aliased)) return aliased;

        let best = "";
        let bestScore = 0;
        spokenNumberVocabulary.forEach((candidate) => {
            const score = Math.max(
                advancedSimilarityScore(aliased, candidate),
                orderedLetterScore(aliased, candidate) * 0.92,
            );
            if (score > bestScore) {
                best = candidate;
                bestScore = score;
            }
        });
        return bestScore >= 0.84 ? best : "";
    }

    function expandSpokenNumberToken(token) {
        const normalized = reduceRepeatedLetters(normalizeVoiceText(token));
        if (!normalized) return [];
        if (/^\d+(?:[.,]\d+)?$/.test(normalized)) return [normalized];

        const direct = bestSpokenNumberCandidate(normalized);
        if (direct && spokenNumberTokens.has(direct)) return [direct];
        const simpleParts = [];
        const specialTokens = ["yuz", "min"];
        for (const specialToken of specialTokens) {
            if (!normalized.includes(specialToken) || normalized === specialToken) continue;
            const [left, right] = normalized.split(specialToken);
            const leftCandidate = left ? bestSpokenNumberCandidate(left) : "";
            const rightCandidate = right ? bestSpokenNumberCandidate(right) : "";
            if (left && !leftCandidate) continue;
            if (right && !rightCandidate) continue;
            if (leftCandidate) simpleParts.push(leftCandidate);
            simpleParts.push(specialToken);
            if (rightCandidate) simpleParts.push(rightCandidate);
            break;
        }
        return simpleParts;
    }

    function normalizeSpokenNumberTokens(segment) {
        return normalizeVoiceText(segment)
            .split(" ")
            .filter(Boolean)
            .flatMap((token) => expandSpokenNumberToken(token))
            .filter(Boolean);
    }

    function isSpokenNumberToken(token) {
        const normalized = normalizeVoiceText(token);
        if (/^\d+(?:[.,]\d+)?$/.test(normalized)) return true;
        return expandSpokenNumberToken(token).length > 0;
    }

    function tokenizeCanonicalText(text) {
        return canonicalizeVoiceText(text).split(" ").filter(Boolean);
    }

    function sanitizeEntityTokens(tokens) {
        const cleaned = tokens
            .map((token) => normalizeVoiceToken(token))
            .filter(Boolean);

        while (cleaned.length && leadingEntityNoiseTokens.has(cleaned[0])) cleaned.shift();

        const result = [];
        for (const token of cleaned) {
            if (/^\d/.test(token)) break;
            if (entityBoundaryTokens.has(token)) break;
            if (isSpokenNumberToken(token) && result.length) break;
            if (leadingEntityNoiseTokens.has(token) && !result.length) continue;
            result.push(token);
        }
        return result;
    }

    function extractNumberSegmentBeforeKeyword(text, keywords) {
        const tokens = tokenizeCanonicalText(text);
        for (let index = 0; index < tokens.length; index += 1) {
            if (!keywords.includes(tokens[index])) continue;
            const collected = [];
            let sawDigitLiteral = false;
            for (let pointer = index - 1; pointer >= 0; pointer -= 1) {
                const token = tokens[pointer];
                if (!isSpokenNumberToken(token)) break;
                const isDigitLiteral = /^\d+(?:[.,]\d+)?$/.test(token);
                if (isDigitLiteral && sawDigitLiteral) break;
                if (isDigitLiteral) sawDigitLiteral = true;
                if (collected.length && isDigitLiteral && /^\d+(?:[.,]\d+)?$/.test(collected[0])) break;
                if (isSpokenNumberToken(token)) {
                    collected.unshift(token);
                    continue;
                }
                break;
            }
            if (collected.length) return collected.join(" ");
        }
        return "";
    }

    function extractNumberSegmentAfterKeyword(text, keywords) {
        const tokens = tokenizeCanonicalText(text);
        for (let index = 0; index < tokens.length; index += 1) {
            const token = normalizeVoiceToken(tokens[index]);
            if (!keywords.includes(token)) continue;
            const collected = [];
            for (let pointer = index + 1; pointer < tokens.length; pointer += 1) {
                const nextToken = tokens[pointer];
                if (!isSpokenNumberToken(nextToken)) break;
                collected.push(nextToken);
            }
            if (collected.length) return collected.join(" ");
        }
        return "";
    }

    function normalizeRelativeDayCount(rawValue) {
        const numeric = Number(rawValue);
        if (!Number.isFinite(numeric) || numeric <= 0) return null;
        if (numeric <= 31) return numeric;
        const text = String(rawValue || "").trim();
        const compactMatch = text.match(/^([1-9]\d?)(0{2,3})$/);
        if (compactMatch) {
            const reduced = Number(compactMatch[1]);
            if (reduced <= 31) return reduced;
        }
        return null;
    }

    const formTypeKeywordMap = {
        expense: ["xerc", "gubre", "pestisid", "baytarliq", "yem", "suvarma", "yanacaq", "dizel", "benzin"],
        income: ["gelir", "satis"],
        animal: ["heyvan", "inek", "dana", "qoyun", "keci", "toyuq", "at", "essek", "qatir"],
        seed: ["toxum", "bugda", "arpa", "qargidali", "yonca", "pambiq"],
        tool: ["alet", "traktor", "kurek", "bel", "kotan", "nasos", "drel"],
        farm: ["mehsul", "sud", "yumurta", "pendir", "qatiq", "bal", "mum"],
    };

    function bestKeywordFamilyMatch(tokens, keywords) {
        let best = 0;
        tokens.forEach((token) => {
            keywords.forEach((keyword) => {
                const score = Math.max(
                    advancedSimilarityScore(token, keyword),
                    orderedLetterScore(token, keyword),
                );
                if (score > best) best = score;
            });
        });
        return best;
    }

    function detectLeadingIntent(tokens) {
        if (!tokens.length) return "";
        const first = tokens[0] || "";
        const second = tokens[1] || "";
        const firstSecond = `${first} ${second}`.trim();

        const intents = [
            { formType: "income", keywords: ["gelir", "satis"] },
            { formType: "expense", keywords: ["xerc", "gubre", "pestisid", "baytarliq", "yem", "suvarma"] },
            { formType: "animal", keywords: ["heyvan"] },
            { formType: "seed", keywords: ["toxum"] },
            { formType: "tool", keywords: ["alet"] },
            { formType: "farm", keywords: ["mehsul"] },
        ];

        let bestType = "";
        let bestScore = 0;
        intents.forEach(({ formType, keywords }) => {
            keywords.forEach((keyword) => {
                const score = Math.max(
                    advancedSimilarityScore(first, keyword),
                    advancedSimilarityScore(firstSecond, `${keyword} elave`),
                    orderedLetterScore(first, keyword),
                );
                if (score > bestScore) {
                    bestType = formType;
                    bestScore = score;
                }
            });
        });
        return bestScore >= 0.72 ? bestType : "";
    }

    function prettifyCanonicalText(value) {
        return String(value || "")
            .replace(/\bgelir\b/g, "Gəlir")
            .replace(/\bxerc\b/g, "Xərc")
            .replace(/\bheyvan\b/g, "Heyvan")
            .replace(/\btoxum\b/g, "Toxum")
            .replace(/\balet\b/g, "Alət")
            .replace(/\bmehsul\b/g, "Məhsul")
            .replace(/\belave\b/g, "əlavə")
            .replace(/\bet\b/g, "et")
            .replace(/\binek\b/g, "İnək")
            .replace(/\bdisi\b/g, "Dişi")
            .replace(/\berkek\b/g, "Erkək")
            .replace(/\bbugda\b/g, "Buğda")
            .replace(/\barpa\b/g, "Arpa")
            .replace(/\byonca\b/g, "Yonca")
            .replace(/\bqiymet\b/g, "qiymət")
            .replace(/\bmebleg\b/g, "məbləğ")
            .replace(/\bmiqdar\b/g, "miqdar")
            .replace(/\bceki\b/g, "çəki")
            .replace(/\bdunen\b/g, "Dünən")
            .replace(/\bbugun\b/g, "Bu gün")
            .replace(/\bsabah\b/g, "Sabah")
            .replace(/\bevvel\b/g, "əvvəl")
            .replace(/\bgun\b/g, "gün")
            .replace(/\bmanat\b/g, "manat")
            .replace(/\bqram\b/g, "qram")
            .replace(/\bton\b/g, "ton")
            .replace(/\bkiloqram\b/g, "kiloqram")
            .replace(/\bkilo\b/g, "kilo")
            .replace(/\bkq\b/g, "kilo")
            .replace(/\bkg\b/g, "kilo");
    }

    function prettyUnitLabel(unitValue, unitLabel) {
        if (unitLabel) return prettifyCanonicalText(unitLabel);
        return prettifyCanonicalText(unitValue);
    }

    function summaryFieldOrder(draft, transcript) {
        const normalized = canonicalizeVoiceText(transcript);
        const entries = [];

        function addEntry(text, patterns, fallbackOrder) {
            if (!text) return;
            let index = Number.POSITIVE_INFINITY;
            patterns.forEach((pattern) => {
                const matchIndex = normalized.search(pattern);
                if (matchIndex !== -1) index = Math.min(index, matchIndex);
            });
            entries.push({ text, order: index !== Number.POSITIVE_INFINITY ? index : fallbackOrder });
        }

        const entityLabel =
            draft.item?.name ||
            draft.subcategory?.name ||
            draft.category?.name ||
            draft.categoryName ||
            "";
        const entityPatterns = entityLabel
            ? canonicalizeVoiceText(entityLabel).split(" ").filter(Boolean).map((token) => new RegExp(`\\b${escapeRegex(token)}\\b`))
            : [];

        addEntry(entityLabel ? titleCaseAz(entityLabel) : "", entityPatterns, 20);
        addEntry(draft.gender ? titleCaseAz(prettifyCanonicalText(draft.gender)) : "", [/\bdisi\b/, /\berkek\b/], 30);

        if (draft.quantity != null && draft.quantity !== "") {
            const quantityText = draft.formType === "animal"
                ? `Miqdar ${draft.quantity}`
                : `${draft.quantity}${draft.unit ? ` ${prettyUnitLabel(draft.unit, draft.unitLabel)}` : ""}`;
            addEntry(quantityText, [/\bmiqdar\b/, /\bsay\b/, /\beded\b/, /\bdene\b/, /\blitr\b/, /\bqram\b/, /\bg\b/, /\bton\b/, /\bkiloqram\b/, /\bkilogram\b/, /\bkilo\b/, /\bcilo\b/, /\bkq\b/, /\bkg\b/, /\bml\b/], 40);
        }

        if (draft.weight != null && draft.weight !== "") {
            const weightText = draft.formType === "animal" ? `Çəki ${draft.weight}` : `${draft.weight} kilo`;
            addEntry(weightText, [/\bceki\b/, /\bteki\b/, /\bdeki\b/], 50);
        }

        if (draft.amount != null && draft.amount !== "") addEntry(`${draft.amountExplicit ? "Məbləğ " : ""}${draft.amount} manat`, [/\bmebleg\b/, /\bmanat\b/], 60);
        else if (draft.price != null && draft.price !== "") addEntry(`${draft.priceExplicit ? "Məbləğ " : ""}${draft.price} manat`, [/\bqiymet\b/, /\bmanat\b/], 60);

        if (draft.date) {
            addEntry(
                draft.dateLabel || formatSummaryDate(draft.date),
                [/\bdunen\b/, /\bbugun\b/, /\bsabah\b/, /\bgun\b/, /\bhefte\b/, /\bevvel\b/, /\bqabaq\b/, /\bsonra\b/],
                70,
            );
        }

        return entries.sort((left, right) => left.order - right.order).map((entry) => entry.text);
    }

    function buildPrettyVoiceSummary(draft, transcript) {
        const parts = [];
        const formLabels = {
            expense: "Xərc əlavə et",
            income: "Gəlir əlavə et",
            animal: "Heyvan əlavə et",
            seed: "Toxum əlavə et",
            tool: "Alət əlavə et",
            farm: "Məhsul əlavə et",
        };
        if (draft.formType && formLabels[draft.formType]) parts.push(formLabels[draft.formType]);
        parts.push(...summaryFieldOrder(draft, transcript));

        const sentence = parts.filter(Boolean).join(", ");
        if (sentence) return `${sentence}.`;
        const fallback = prettifyCanonicalText(canonicalizeVoiceText(transcript));
        return fallback ? `${titleCaseAz(fallback)}.` : "";
    }

    function selectedOptionText(elementId) {
        const select = document.getElementById(elementId);
        if (!select) return "";
        const option = select.options[select.selectedIndex];
        return option && option.value ? option.textContent.trim() : "";
    }

    function fieldValue(elementId) {
        return document.getElementById(elementId)?.value?.trim?.() || "";
    }

    function formatSummaryDate(date) {
        if (!date) return "";
        if (date === todayIso) return "Bu gün";
        if (date === shiftToday(-1)) return "Dünən";
        if (date === shiftToday(1)) return "Sabah";
        return date;
    }

    function buildPrettyVoiceSummaryFromForm(formType, transcript, draft) {
        const parts = [];
        const formLabels = {
            expense: "Xərc əlavə et",
            income: "Gəlir əlavə et",
            animal: "Heyvan əlavə et",
            seed: "Toxum əlavə et",
            tool: "Alət əlavə et",
            farm: "Məhsul əlavə et",
        };
        if (formLabels[formType]) parts.push(formLabels[formType]);

        let entityLabel = "";
        if (formType === "income") entityLabel = selectedOptionText("income-item") || document.getElementById("income-manual-name")?.value || selectedOptionText("income-category");
        else if (formType === "animal") entityLabel = selectedOptionText("animal-subcategory") || document.getElementById("animal-manual-name")?.value || selectedOptionText("animal-category");
        else if (formType === "seed") entityLabel = selectedOptionText("seed-item") || document.getElementById("seed-manual-name")?.value || selectedOptionText("seed-category");
        else if (formType === "tool") entityLabel = selectedOptionText("tool-item") || document.getElementById("tool-manual-name")?.value || selectedOptionText("tool-category");
        else if (formType === "farm") entityLabel = selectedOptionText("farm-item") || document.getElementById("farm-manual-name")?.value || selectedOptionText("farm-category");
        else if (formType === "expense") entityLabel = selectedOptionText("expense-subcategory") || document.getElementById("expense-manual-name")?.value || selectedOptionText("expense-category");

        if (entityLabel) parts.push(titleCaseAz(entityLabel));

        if (formType === "income") {
            const quantity = fieldValue("income-quantity");
            const unit = selectedOptionText("income-unit") || fieldValue("income-unit");
            const amount = fieldValue("income-amount") || draft?.amount || draft?.price || "";
            const date = fieldValue("income-date") || draft?.date || "";
            if (quantity) parts.push(unit ? `${quantity} ${unit}` : quantity);
            if (amount) parts.push(`${draft?.amountExplicit || draft?.priceExplicit ? "Məbləğ " : ""}${amount} manat`);
            const prettyDate = formatSummaryDate(date);
            if (prettyDate) parts.push(prettyDate);
        } else if (formType === "animal") {
            const quantity = fieldValue("animal-quantity");
            const weight = fieldValue("animal-weight") || draft?.weight || "";
            const amount = fieldValue("animal-price") || draft?.price || draft?.amount || "";
            const date = fieldValue("animal-date") || draft?.date || "";
            if (quantity && quantity !== "1") parts.push(`${quantity} ədəd`);
            if (weight) parts.push(`${weight} kilo`);
            if (amount) parts.push(`${draft?.amountExplicit || draft?.priceExplicit ? "Məbləğ " : ""}${amount} manat`);
            const prettyDate = formatSummaryDate(date);
            if (prettyDate) parts.push(prettyDate);
        } else if (formType === "expense") {
            const amount = fieldValue("expense-amount") || draft?.amount || "";
            const date = fieldValue("expense-date") || draft?.date || "";
            if (amount) parts.push(`${draft?.amountExplicit || draft?.priceExplicit ? "Məbləğ " : ""}${amount} manat`);
            const prettyDate = formatSummaryDate(date);
            if (prettyDate) parts.push(prettyDate);
        } else if (formType === "seed") {
            const quantity = fieldValue("seed-quantity");
            const unit = selectedOptionText("seed-unit") || fieldValue("seed-unit");
            const amount = fieldValue("seed-price") || draft?.price || draft?.amount || "";
            const date = fieldValue("seed-date") || draft?.date || "";
            if (quantity) parts.push(unit ? `${quantity} ${unit}` : quantity);
            if (amount) parts.push(`${draft?.amountExplicit || draft?.priceExplicit ? "Məbləğ " : ""}${amount} manat`);
            const prettyDate = formatSummaryDate(date);
            if (prettyDate) parts.push(prettyDate);
        } else if (formType === "tool") {
            const quantity = fieldValue("tool-quantity");
            const amount = fieldValue("tool-price") || draft?.price || draft?.amount || "";
            const date = fieldValue("tool-date") || draft?.date || "";
            if (quantity) parts.push(`${quantity} ədəd`);
            if (amount) parts.push(`${draft?.amountExplicit || draft?.priceExplicit ? "Məbləğ " : ""}${amount} manat`);
            const prettyDate = formatSummaryDate(date);
            if (prettyDate) parts.push(prettyDate);
        } else if (formType === "farm") {
            const quantity = fieldValue("farm-quantity");
            const unit = selectedOptionText("farm-unit") || fieldValue("farm-unit");
            const amount = fieldValue("farm-price") || draft?.price || draft?.amount || "";
            const date = fieldValue("farm-date") || draft?.date || "";
            if (quantity) parts.push(unit ? `${quantity} ${unit}` : quantity);
            if (amount) parts.push(`${draft?.amountExplicit || draft?.priceExplicit ? "Məbləğ " : ""}${amount} manat`);
            const prettyDate = formatSummaryDate(date);
            if (prettyDate) parts.push(prettyDate);
        }

        const sentence = parts.filter(Boolean).join(", ");
        if (sentence) return `${sentence}.`;
        return buildPrettyVoiceSummary({}, transcript);
    }

    scheduleVoiceVocabularyCollection();

    function escapeRegex(value) {
        return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function createLocalDate(year, month, day) {
        const date = new Date(year, month - 1, day);
        if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
        return date;
    }

    function formatDateIso(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function shiftToday(days) {
        const base = new Date(`${todayIso}T00:00:00`);
        base.setDate(base.getDate() + days);
        return formatDateIso(base);
    }

    function normalizeMonthSpellings(value) {
        return value
            .replace(/\byan var\b/g, "yanvar")
            .replace(/\byanv ar\b/g, "yanvar")
            .replace(/\bfev ral\b/g, "fevral")
            .replace(/\bfeb ral\b/g, "fevral")
            .replace(/\bap rel\b/g, "aprel")
            .replace(/\biy un\b/g, "iyun")
            .replace(/\biy ul\b/g, "iyul")
            .replace(/\bav qust\b/g, "avqust")
            .replace(/\bsenty abr\b/g, "sentyabr")
            .replace(/\bokty abr\b/g, "oktyabr")
            .replace(/\bnoy abr\b/g, "noyabr")
            .replace(/\bdek abr\b/g, "dekabr");
    }

    function parseNumberWords(segment) {
        const units = { sifir: 0, bir: 1, iki: 2, uc: 3, dord: 4, bes: 5, alti: 6, yeddi: 7, sekkiz: 8, doqquz: 9 };
        const tens = { on: 10, iyirmi: 20, otuz: 30, qirx: 40, elli: 50, altmis: 60, yetmis: 70, seksen: 80, doxsan: 90 };
        const tokens = normalizeSpokenNumberTokens(segment);
        if (!tokens.length) return null;

        let total = 0;
        let current = 0;
        let fractional = "";
        let inFraction = false;
        let matched = false;

        for (const token of tokens) {
            if (token === "vergul" || token === "noqte" || token === "nokte") {
                inFraction = true;
                continue;
            }
            if (inFraction) {
                if (token in units) {
                    fractional += String(units[token]);
                    matched = true;
                    continue;
                }
                if (/^\d+$/.test(token)) {
                    fractional += token;
                    matched = true;
                    continue;
                }
                break;
            }
            if (token in tens) {
                current += tens[token];
                matched = true;
                continue;
            }
            if (token in units) {
                current += units[token];
                matched = true;
                continue;
            }
            if (token === "yuz") {
                current = (current || 1) * 100;
                matched = true;
                continue;
            }
            if (token === "min") {
                total += (current || 1) * 1000;
                current = 0;
                matched = true;
                continue;
            }
        }

        if (!matched) return null;
        const integerValue = total + current;
        if (!fractional) return integerValue;
        return Number(`${integerValue}.${fractional}`);
    }

    function parseSpokenNumber(segment) {
        if (!segment) return null;
        const digitMatch = segment.match(/-?\d+(?:[.,]\d+)?/);
        if (digitMatch) {
            const numeric = Number(digitMatch[0].replace(",", "."));
            const trailing = canonicalizeVoiceText(segment.slice(digitMatch.index + digitMatch[0].length));
            const trailingTokens = trailing.split(" ").filter(Boolean);
            const pureTrailingNumberPhrase = [];
            for (const token of trailingTokens) {
                if (!isSpokenNumberToken(token)) break;
                pureTrailingNumberPhrase.push(token);
            }
            const trailingWordValue = parseNumberWords(pureTrailingNumberPhrase.join(" "));
            if (trailingWordValue != null && trailingWordValue < 1000) return numeric + Number(trailingWordValue);
            return numeric;
        }
        const wordValue = parseNumberWords(segment);
        return wordValue == null ? null : Number(wordValue);
    }

    function extractFieldSegment(text, keywords, stopKeywords) {
        const normalized = canonicalizeVoiceText(text);
        for (const keyword of keywords) {
            const regex = new RegExp(`(?:^| )${escapeRegex(keyword)}(?:si|i|u|ü|a|e|ye|ya)?\\s+(.+?)(?=(?: ${stopKeywords.map(escapeRegex).join("| ")})|$)`);
            const match = normalized.match(regex);
            if (match && match[1]) return match[1].trim();
        }
        return "";
    }

    function extractSubjectSegment(text, formType) {
        const normalized = canonicalizeVoiceText(text);
        const actionPrefixes = {
            expense: ["xerc elave et", "xerc elave ed", "xerc"],
            income: ["gelir elave et", "gelir elave ed", "gelir", "satis elave et", "satis"],
            animal: ["heyvan elave et", "heyvan elave ed", "heyvan"],
            seed: ["toxum elave et", "toxum elave ed", "toxum"],
            tool: ["alet elave et", "alet elave ed", "alet"],
            farm: ["mehsul elave et", "mehsul elave ed", "mehsul"],
        };
        let subject = normalized;
        (actionPrefixes[formType] || []).forEach((prefix) => {
            if (subject.startsWith(`${prefix} `)) {
                subject = subject.slice(prefix.length).trim();
            } else if (subject === prefix) {
                subject = "";
            }
        });

        const stopWords = ["miqdar", "mebleg", "qiymet", "ceki", "tarix", "cinsiyyet", "id", "identifikasiya", "elave melumat", "qeyd"];
        let cutIndex = subject.length;
        stopWords.forEach((stopWord) => {
            const index = subject.indexOf(` ${stopWord}`);
            if (index !== -1) cutIndex = Math.min(cutIndex, index);
        });
        subject = subject.slice(0, cutIndex).trim();
        return sanitizeEntityTokens(subject.split(" ")).join(" ").trim();
    }

    function extractLeadEntitySegment(text, formType) {
        const chunks = String(text || "")
            .split(/[;,]/)
            .map((part) => String(part || "").trim())
            .filter(Boolean);
        const prefixes = {
            expense: ["xerc elave et", "xerc elave ed", "xerc"],
            income: ["gelir elave et", "gelir elave ed", "gelir", "satis elave et", "satis"],
            animal: ["heyvan elave et", "heyvan elave ed", "heyvan"],
            seed: ["toxum elave et", "toxum elave ed", "toxum"],
            tool: ["alet elave et", "alet elave ed", "alet"],
            farm: ["mehsul elave et", "mehsul elave ed", "mehsul"],
        };

        for (const chunk of chunks) {
            let cleaned = canonicalizeVoiceText(chunk);
            (prefixes[formType] || []).forEach((prefix) => {
                if (cleaned.startsWith(`${prefix} `)) cleaned = cleaned.slice(prefix.length).trim();
                else if (cleaned === prefix) cleaned = "";
            });
            const entityTokens = sanitizeEntityTokens(cleaned.split(" "));
            if (entityTokens.length) return entityTokens.join(" ");
        }

        const subject = extractSubjectSegment(text, formType);
        return sanitizeEntityTokens(subject.split(" ")).join(" ").trim();
    }

    function extractNumericField(text, keywords) {
        const segment = extractNumberSegmentAfterKeyword(text, keywords);
        return parseSpokenNumber(segment);
    }

    function hasExplicitAmountLabel(text) {
        const normalized = canonicalizeVoiceText(text);
        return /\b(mebleg|qiymet)\b/.test(normalized);
    }

    function extractAmountValue(text) {
        if (activeVoiceLanguage === "en") {
            const native = normalizeNativeVoiceText(text);
            const nativeMatch = native.match(/(\d+(?:[.,]\d+)?)\s+(manat|menat|monat|monod|monot|minute|minutes)\b/);
            if (nativeMatch) return Number(nativeMatch[1].replace(",", "."));
        }
        if (activeVoiceLanguage === "ru") {
            const native = normalizeNativeVoiceText(text);
            const nativeMatch = native.match(/(\d+(?:[.,]\d+)?)\s+(манат|манад|монат)\b/);
            if (nativeMatch) return Number(nativeMatch[1].replace(",", "."));
        }
        const explicit = extractNumericField(text, ["mebleg"]);
        if (explicit != null) return explicit;
        const numberSegment = extractNumberSegmentBeforeKeyword(text, ["manat"]);
        if (numberSegment) {
            const parsed = parseSpokenNumber(numberSegment);
            if (parsed != null) return parsed;
        }
        const normalized = canonicalizeVoiceText(text);
        const match = normalized.match(/(\d+(?:[.,]\d+)?)\s+manat\b/);
        return match ? Number(match[1].replace(",", ".")) : null;
    }

    function extractQuantityValue(text) {
        if (activeVoiceLanguage === "en") {
            const native = normalizeNativeVoiceText(text);
            const nativeMatch = native.match(/(\d+(?:[.,]\d+)?)\s+(piece|pieces|bundle|bundles|pack|packs|liter|liters|litre|litres|l|milliliter|milliliters|ml|gram|grams|g|kilogram|kilograms|kilo|kg|ton|tons)\b/);
            if (nativeMatch) return Number(nativeMatch[1].replace(",", "."));
        }
        if (activeVoiceLanguage === "ru") {
            const native = normalizeNativeVoiceText(text);
            const nativeMatch = native.match(/(\d+(?:[.,]\d+)?)\s+(штука|штук|упаковка|упаковки|пучок|литр|литра|литров|миллилитр|мл|грамм|грамма|граммов|г|килограмм|килограмма|килограммов|кило|кг|тонна|тонны|тонн)\b/);
            if (nativeMatch) return Number(nativeMatch[1].replace(",", "."));
        }
        const explicit = extractNumericField(text, ["miqdar", "say", "eded"]);
        if (explicit != null) return explicit;
        const numberSegment = extractNumberSegmentBeforeKeyword(text, ["ton", "qram", "g", "kiloqram", "kilogram", "kilo", "cilo", "kq", "kg", "litr", "l", "ml", "eded", "deste", "baglama"]);
        if (numberSegment) {
            const parsed = parseSpokenNumber(numberSegment);
            if (parsed != null) return parsed;
        }
        const normalized = canonicalizeVoiceText(text);
        const match = normalized.match(/(\d+(?:[.,]\d+)?)\s+(ton|qram|g|kiloqram|kilogram|kilo|kq|kg|litr|l|ml|eded|deste|baglama)\b/);
        return match ? Number(match[1].replace(",", ".")) : null;
    }

    function extractGender(text) {
        const normalized = canonicalizeVoiceText(text);
        if (/\bdisi\b/.test(normalized)) return "disi";
        if (/\berkek\b/.test(normalized)) return "erkek";
        return "";
    }

    function extractIdentificationNo(text) {
        const explicitIdMatch = text.match(/\b(?:id|identifikasiya(?:\s+no)?|identifikasiya\s+nomresi)\b[:\s-]*([A-Z]{1,3}\s*-?\s*\d{3,})\b/i);
        if (explicitIdMatch && explicitIdMatch[1]) {
            return explicitIdMatch[1].replace(/\s+/g, "").toUpperCase();
        }

        const normalized = canonicalizeVoiceText(text);
        if (!/\b(id|identifikasiya)\b/.test(normalized)) return "";

        const fallbackMatch = text.match(/\b[A-Z]{1,3}\s*-?\s*\d{3,}\b/i);
        if (fallbackMatch) return fallbackMatch[0].replace(/\s+/g, "").toUpperCase();
        return "";
    }

    function extractAdditionalInfo(text) {
        const segment = extractFieldSegment(text, ["elave melumat", "qeyd"], ["miqdar", "mebleg", "qiymet", "ceki", "tarix", "cinsiyyet", "id", "identifikasiya", "kateqoriya"]);
        if (segment) return segment;
        if (activeVoiceLanguage === "en") {
            const normalized = canonicalizeVoiceText(text);
            const fallbackMatch = normalized.match(/\bno\s+(.+)$/);
            if (fallbackMatch && fallbackMatch[1]) return fallbackMatch[1].trim();
        }
        return segment || "";
    }

    function extractDateDetails(text) {
        const raw = text;
        const normalized = normalizeMonthSpellings(canonicalizeVoiceText(text))
            .replace(/\bbu ilin\b/g, "")
            .replace(/\bcari ilin\b/g, "");

        if (/\bbu gun\b/.test(normalized)) return { value: todayIso, label: "Bu gün" };
        if (/\bdunen\b/.test(normalized)) return { value: shiftToday(-1), label: "Dünən" };
        if (/\bsabah\b/.test(normalized)) return { value: shiftToday(1), label: "Sabah" };
        if (/\bo biri gun\b/.test(normalized)) return { value: shiftToday(2), label: "2 gün sonra" };
        if (/\biki gun evvel\b/.test(normalized)) return { value: shiftToday(-2), label: "2 gün əvvəl" };
        if (/\buc gun evvel\b/.test(normalized)) return { value: shiftToday(-3), label: "3 gün əvvəl" };
        if (/\bdord gun evvel\b/.test(normalized)) return { value: shiftToday(-4), label: "4 gün əvvəl" };
        if (/\bbes gun evvel\b/.test(normalized)) return { value: shiftToday(-5), label: "5 gün əvvəl" };
        if (/\biki gun sonra\b/.test(normalized)) return { value: shiftToday(2), label: "2 gün sonra" };
        if (/\buc gun sonra\b/.test(normalized)) return { value: shiftToday(3), label: "3 gün sonra" };
        if (/\bdord gun sonra\b/.test(normalized)) return { value: shiftToday(4), label: "4 gün sonra" };
        if (/\bbes gun sonra\b/.test(normalized)) return { value: shiftToday(5), label: "5 gün sonra" };
        if (/\bbir hefte evvel\b/.test(normalized)) return { value: shiftToday(-7), label: "1 həftə əvvəl" };
        if (/\b1 hefte evvel\b/.test(normalized)) return { value: shiftToday(-7), label: "1 həftə əvvəl" };
        if (/\b1 hefte eve\b/.test(normalized)) return { value: shiftToday(-7), label: "1 həftə əvvəl" };
        if (/\b1 hefte evve\b/.test(normalized)) return { value: shiftToday(-7), label: "1 həftə əvvəl" };
        if (/\bbir hefte qabaq\b/.test(normalized)) return { value: shiftToday(-7), label: "1 həftə əvvəl" };
        if (/\bbir hefte sonra\b/.test(normalized)) return { value: shiftToday(7), label: "1 həftə sonra" };
        if (/\biki hefte evvel\b/.test(normalized)) return { value: shiftToday(-14), label: "2 həftə əvvəl" };
        if (/\b2 hefte evvel\b/.test(normalized)) return { value: shiftToday(-14), label: "2 həftə əvvəl" };
        if (/\b2 hefte eve\b/.test(normalized)) return { value: shiftToday(-14), label: "2 həftə əvvəl" };
        if (/\b2 hefte evve\b/.test(normalized)) return { value: shiftToday(-14), label: "2 həftə əvvəl" };
        if (/\biki hefte qabaq\b/.test(normalized)) return { value: shiftToday(-14), label: "2 həftə əvvəl" };
        if (/\biki hefte sonra\b/.test(normalized)) return { value: shiftToday(14), label: "2 həftə sonra" };
        if (/\b2 hefte sonra\b/.test(normalized)) return { value: shiftToday(14), label: "2 həftə sonra" };

        const relativeDayMatch = normalized.match(/\b(\d+)\s+gun\s+(evvel|qabaq|once|sonra)\b/);
        if (relativeDayMatch) {
            const parsedDays = normalizeRelativeDayCount(relativeDayMatch[1]);
            if (parsedDays != null) {
                const offset = parsedDays * (["sonra"].includes(relativeDayMatch[2]) ? 1 : -1);
                return { value: shiftToday(offset), label: `${parsedDays} gün ${offset < 0 ? "əvvəl" : "sonra"}` };
            }
        }

        const compressedRelativeDayMatch = normalized.match(/\b(\d{3,4})\s+(evvel|qabaq|once|sonra)\b/);
        if (compressedRelativeDayMatch) {
            const parsedDays = normalizeRelativeDayCount(compressedRelativeDayMatch[1]);
            if (parsedDays != null) {
                const offset = parsedDays * (["sonra"].includes(compressedRelativeDayMatch[2]) ? 1 : -1);
                return { value: shiftToday(offset), label: `${parsedDays} gün ${offset < 0 ? "əvvəl" : "sonra"}` };
            }
        }

        const looseRelativeNumberMatch = normalized.match(/\b(\d+)\s+(evvel|qabaq|once|sonra)\b/);
        if (looseRelativeNumberMatch) {
            const parsedDays = normalizeRelativeDayCount(looseRelativeNumberMatch[1]);
            if (parsedDays != null) {
                const offset = parsedDays * (["sonra"].includes(looseRelativeNumberMatch[2]) ? 1 : -1);
                return { value: shiftToday(offset), label: `${parsedDays} gün ${offset < 0 ? "əvvəl" : "sonra"}` };
            }
        }

        const looseRelativeDayMatch = normalized.match(/\b(\d+)\s+gun(?:\s+\w+)?\s+(evvel|qabaq|once|sonra)\b/);
        if (looseRelativeDayMatch) {
            const parsedDays = normalizeRelativeDayCount(looseRelativeDayMatch[1]);
            if (parsedDays != null) {
                const offset = parsedDays * (["sonra"].includes(looseRelativeDayMatch[2]) ? 1 : -1);
                return { value: shiftToday(offset), label: `${parsedDays} gün ${offset < 0 ? "əvvəl" : "sonra"}` };
            }
        }

        const wordRelativeDayMatch = normalized.match(/\b(bir|iki|uc|dord|bes|alti|yeddi|sekkiz|doqquz|on|iyirmi|otuz)\s+gun\s+(evvel|qabaq|once|sonra)\b/);
        if (wordRelativeDayMatch) {
            const parsedDays = parseSpokenNumber(wordRelativeDayMatch[1]);
            if (parsedDays != null) {
                const offset = parsedDays * (["sonra"].includes(wordRelativeDayMatch[2]) ? 1 : -1);
                return { value: shiftToday(offset), label: `${parsedDays} gün ${offset < 0 ? "əvvəl" : "sonra"}` };
            }
        }

        const isoMatch = raw.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
        if (isoMatch) return { value: `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`, label: `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}` };

        const dottedMatch = raw.match(/\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b/);
        if (dottedMatch) return { value: `${dottedMatch[3]}-${String(dottedMatch[2]).padStart(2, "0")}-${String(dottedMatch[1]).padStart(2, "0")}`, label: `${dottedMatch[3]}-${String(dottedMatch[2]).padStart(2, "0")}-${String(dottedMatch[1]).padStart(2, "0")}` };

        const dottedWithoutYear = raw.match(/\b(\d{1,2})[./](\d{1,2})\b/);
        if (dottedWithoutYear) {
            const guessed = createLocalDate(currentYear, Number(dottedWithoutYear[2]), Number(dottedWithoutYear[1]));
            if (guessed) return { value: formatDateIso(guessed), label: formatDateIso(guessed) };
        }

        const monthMap = { yanvar: "01", fevral: "02", mart: "03", aprel: "04", may: "05", iyun: "06", iyul: "07", avqust: "08", sentyabr: "09", oktyabr: "10", noyabr: "11", dekabr: "12" };
        const monthMatch = normalized.match(/\b(\d{1,2})(?:-?u|-?un|-?in|-?cu|-?ci)?\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)(?:\s+(\d{4}))?\b/);
        if (monthMatch) {
            const year = Number(monthMatch[3] || currentYear);
            const guessed = createLocalDate(year, Number(monthMap[monthMatch[2]]), Number(monthMatch[1]));
            if (guessed) return { value: formatDateIso(guessed), label: monthMatch[3] ? `${Number(monthMatch[1])} ${monthMatch[2]} ${monthMatch[3]}` : `${Number(monthMatch[1])} ${monthMatch[2]}` };
        }

        const reversedMonthMatch = normalized.match(/\b(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+(\d{1,2})(?:-?u|-?un|-?in|-?cu|-?ci)?(?:\s+(\d{4}))?\b/);
        if (reversedMonthMatch) {
            const year = Number(reversedMonthMatch[3] || currentYear);
            const guessed = createLocalDate(year, Number(monthMap[reversedMonthMatch[1]]), Number(reversedMonthMatch[2]));
            if (guessed) return { value: formatDateIso(guessed), label: reversedMonthMatch[3] ? `${Number(reversedMonthMatch[2])} ${reversedMonthMatch[1]} ${reversedMonthMatch[3]}` : `${Number(reversedMonthMatch[2])} ${reversedMonthMatch[1]}` };
        }

        const explicitDayMatch = normalized.match(/\b(\d{1,2})(?:-?u|-?un|-?in|-?cu|-?ci)\b/);
        if (explicitDayMatch) {
            const guessed = createLocalDate(currentYear, currentMonth, Number(explicitDayMatch[1]));
            if (guessed) return { value: formatDateIso(guessed), label: formatDateIso(guessed) };
        }
        return { value: "", label: "" };
    }

    function extractDate(text) {
        return extractDateDetails(text).value;
    }

    function bestMatchByLabel(rows, text, labelFn) {
        const normalized = canonicalizeVoiceText(text);
        const textTokens = sanitizeEntityTokens(normalized.split(" "));
        const mentionsMeatVariant = textTokens.includes("eti") || textTokens.includes("et");
        const mentionsDairyVariant = textTokens.includes("sud") || textTokens.includes("sudu");
        let best = null;
        let bestScore = 0;
        rows.forEach((row) => {
            const label = canonicalizeVoiceText(labelFn(row));
            if (!label) return;
            const labelTokens = label.split(" ").filter(Boolean);
            if (!labelTokens.length || !textTokens.length) return;
            const hasExactToken = labelTokens.every((labelToken) => textTokens.includes(labelToken));

            if (normalized.includes(label) && (label.length >= 4 || hasExactToken)) {
                let exactScore = 1.02 + (labelTokens.length * 0.22) + Math.min(0.12, label.length / 100);
                if (mentionsMeatVariant && labelTokens.includes("eti")) exactScore += 0.45;
                if (mentionsMeatVariant && !labelTokens.includes("eti")) exactScore -= 0.35;
                if (mentionsDairyVariant && (labelTokens.includes("sud") || labelTokens.includes("sudu"))) exactScore += 0.4;
                if (mentionsDairyVariant && !labelTokens.includes("sud") && !labelTokens.includes("sudu")) exactScore -= 0.3;
                if (exactScore > bestScore) {
                    best = row;
                    bestScore = exactScore;
                }
                return;
            }
            if (labelTokens.length === 1 && labelTokens[0].length <= 3) {
                if (!hasExactToken) return;
                const textStr = textTokens.join(" ");
                if (textStr.length > 5 && labelTokens[0].length <= 2) return;
            }

            let score = 0;
            if (labelTokens.length === 1) {
                textTokens.forEach((textToken) => {
                    const similarity = Math.max(
                        advancedSimilarityScore(textToken, labelTokens[0]),
                        orderedLetterScore(textToken, labelTokens[0]) * 0.94,
                        similarityScore(entitySoundKey(textToken), entitySoundKey(labelTokens[0])) * 0.96,
                    );
                    const distance = levenshteinDistance(textToken, labelTokens[0]);
                    const dynamicPenalty = distance / Math.max(textToken.length, labelTokens[0].length, 1);
                    let candidateScore = similarity - (dynamicPenalty * 0.18);
                    if (textTokens.length > 1) candidateScore -= 0.18;
                    if (mentionsMeatVariant) candidateScore -= 0.35;
                    if (mentionsDairyVariant) candidateScore -= 0.28;
                    score = Math.max(score, candidateScore);
                });
            } else {
                for (let index = 0; index <= textTokens.length - 1; index += 1) {
                    const window = textTokens.slice(index, index + labelTokens.length);
                    if (window.length !== labelTokens.length) continue;
                    let scoreTotal = 0;
                    let exactHits = 0;
                    let strongHits = 0;
                    for (let tokenIndex = 0; tokenIndex < labelTokens.length; tokenIndex += 1) {
                        const left = window[tokenIndex] || "";
                        const right = labelTokens[tokenIndex];
                        if (!left) continue;
                        if (left === right) exactHits += 1;
                        const tokenScore = Math.max(
                            advancedSimilarityScore(left, right),
                            orderedLetterScore(left, right) * 0.9,
                            similarityScore(entitySoundKey(left), entitySoundKey(right)) * 0.94,
                        );
                        if (tokenScore >= 0.74) strongHits += 1;
                        scoreTotal += tokenScore;
                    }
                    if ((strongHits / labelTokens.length) < 0.85) continue;
                    const coverageBonus = (exactHits / labelTokens.length) * 0.18;
                    let specificityBonus = Math.min(0.16, (labelTokens.length - 1) * 0.08);
                    if (mentionsMeatVariant && labelTokens.includes("eti")) specificityBonus += 0.32;
                    if (mentionsDairyVariant && (labelTokens.includes("sud") || labelTokens.includes("sudu"))) specificityBonus += 0.3;
                    score = Math.max(score, (scoreTotal / labelTokens.length) + coverageBonus + specificityBonus);
                }
            }

            if (score < 0.7) return;
            if (score > bestScore) {
                best = row;
                bestScore = score;
            }
        });
        return best;
    }

    function bestExactNormalizedLabelMatch(rows, text, labelFn) {
        const normalized = canonicalizeVoiceText(text);
        const collapsedNormalized = normalized.replace(/\s+/g, "");
        let best = null;
        let bestLength = 0;
        rows.forEach((row) => {
            const label = canonicalizeVoiceText(labelFn(row));
            if (!label) return;
            const collapsedLabel = label.replace(/\s+/g, "");
            if ((normalized.includes(label) || collapsedNormalized.includes(collapsedLabel)) && label.length > bestLength) {
                best = row;
                bestLength = label.length;
            }
        });
        return best;
    }

    function getIncomeItemRows() {
        return incomeCategories.flatMap((categoryName) => (incomeData[categoryName]?.items || []).map((item) => ({ ...item, categoryName })));
    }

    function resolveIncomePrefill(label, fallbackUnit = "") {
        const matchedItem = bestExactNormalizedLabelMatch(getIncomeItemRows(), label, (row) => row.name)
            || bestMatchByLabel(getIncomeItemRows(), label, (row) => row.name);
        return {
            categoryName: matchedItem?.categoryName || "Digər",
            itemName: matchedItem && matchedItem.name !== "Digər" ? matchedItem.name : "",
            manualName: matchedItem && matchedItem.name !== "Digər" ? "" : String(label || "").trim(),
            unit: matchedItem?.unit || fallbackUnit || "",
        };
    }

    function buildIncomeRecordFromSourceItem(item) {
        const label = item.metadata?.manual_name || item.metadata?.item_name || item.label || item.name || "";
        const prefill = resolveIncomePrefill(label, item.metadata?.unit || item.unit || "");
        return {
            label,
            form_type: "income",
            target_type: prefill.manualName ? "manual" : "catalog",
            metadata: {
                category_name: prefill.categoryName,
                item_name: prefill.itemName,
                manual_name: prefill.manualName,
                unit: prefill.unit || "ədəd",
                amount: item.metadata?.amount || item.default_price || "",
            },
        };
    }

    function coerceDraftForPageMode(draft) {
        if (addPageMode !== "income" || draft.formType === "income" || draft.formType === "expense") {
            return draft;
        }
        const entityLabel = draft.item?.name || draft.subcategory?.name || draft.category?.name || draft.categoryName || "";
        const prefill = resolveIncomePrefill(entityLabel, draft.unit || "");
        return {
            ...draft,
            formType: "income",
            categoryName: prefill.categoryName,
            item: prefill.itemName ? { name: prefill.itemName, unit: prefill.unit || draft.unit || "" } : null,
            manualName: prefill.manualName || entityLabel,
            unit: draft.unit || prefill.unit || "",
        };
    }

    function guessVoiceFormType(text) {
        const normalized = canonicalizeVoiceText(text);
        const tokens = normalized.split(" ").filter(Boolean);
        const leadingIntent = detectLeadingIntent(tokens);
        if (leadingIntent) return leadingIntent;
        if (/\bxerc\b/.test(normalized)) return "expense";
        if (/\bgelir\b|\bsatis\b/.test(normalized)) return "income";
        if (/\bheyvan\b|\binek\b|\bdana\b|\bqoyun\b|\bkeci\b|\btoyuq\b/.test(normalized)) return "animal";
        if (/\btoxum\b/.test(normalized)) return "seed";
        if (/\balet\b|\btraktor\b|\bkurek\b|\bbel\b/.test(normalized)) return "tool";
        if (/\bmehsul\b|\bsud\b|\byumurta\b|\bterevez\b|\bmeyve\b/.test(normalized)) return "farm";

        let bestType = "";
        let bestScore = 0;
        Object.entries(formTypeKeywordMap).forEach(([formType, keywords]) => {
            const familyScore = bestKeywordFamilyMatch(tokens, keywords);
            const leadingScore = bestKeywordFamilyMatch(tokens.slice(0, 3), keywords) * 1.12;
            const totalScore = Math.max(familyScore, leadingScore);
            if (totalScore > bestScore) {
                bestType = formType;
                bestScore = totalScore;
            }
        });
        if (bestScore >= 0.7) return bestType;
        return "";
    }

    function detectUnitDetails(text, formType) {
        const normalized = canonicalizeVoiceText(text);
        const entries = [
            { patterns: ["millilitr", "ml"], value: formType === "seed" ? "" : "ml", label: "ml" },
            { patterns: ["litr", " l "], value: "litr", label: "litr" },
            { patterns: ["qram", " g "], value: "qram", label: "qram" },
            { patterns: ["ton"], value: "ton", label: "ton" },
            { patterns: ["kiloqram", "kilogram"], value: formType === "seed" ? "kg" : "kq", label: "kiloqram" },
            { patterns: ["kilo", "cilo"], value: formType === "seed" ? "kg" : "kq", label: "kilo" },
            { patterns: ["kq", "kg"], value: formType === "seed" ? "kg" : "kq", label: formType === "seed" ? "kg" : "kq" },
            { patterns: ["eded"], value: "ədəd", label: "ədəd" },
            { patterns: ["deste"], value: "dəstə", label: "dəstə" },
            { patterns: ["baglama"], value: "bağlama", label: "bağlama" },
        ];
        for (const entry of entries) {
            if (entry.patterns.some((pattern) => normalized.includes(pattern)) && entry.value) return { value: entry.value, label: entry.label };
        }
        return { value: "", label: "" };
    }

    function detectUnit(text, formType) {
        return detectUnitDetails(text, formType).value;
    }

    function buildVoiceDraft(text) {
        const formType = guessVoiceFormTypeNative(text) || guessVoiceFormType(text);
        const normalized = canonicalizeVoiceText(text);
        const subjectSegment = extractSubjectSegment(text, formType);
        const nativeEntitySegment = extractNativeEntitySegment(text, formType);
        const leadEntitySegment = nativeEntitySegment || extractLeadEntitySegment(text, formType);
        const dateDetails = extractDateDetails(text);
        const unitDetails = detectUnitDetails(text, formType);
        const draft = {
            formType,
            quantity: extractQuantityValue(text),
            amount: extractAmountValue(text),
            amountExplicit: hasExplicitAmountLabel(text),
            price: extractNumericField(normalized, ["qiymet"]),
            priceExplicit: /\bqiymet\b/.test(normalized),
            weight: extractNumericField(normalized, ["ceki"]),
            date: dateDetails.value,
            dateLabel: dateDetails.label,
            gender: extractGender(text),
            identificationNo: extractIdentificationNo(text),
            additionalInfo: extractAdditionalInfo(text),
            unit: unitDetails.value,
            unitLabel: unitDetails.label,
        };

        if (formType === "expense") {
            draft.category = bestExactNormalizedLabelMatch(expenseData, leadEntitySegment || normalized, (row) => row.name)
                || bestMatchByLabel(expenseData, leadEntitySegment || normalized, (row) => row.name);
            const subRows = expenseData.flatMap((row) => (row.subcategories || []).map((sub) => ({ ...sub, categoryId: row.id })));
            draft.subcategory = bestExactNormalizedLabelMatch(subRows, leadEntitySegment || subjectSegment || normalized, (row) => row.name)
                || bestMatchByLabel(subRows, leadEntitySegment || subjectSegment || normalized, (row) => row.name);
            if (!draft.category && draft.subcategory) draft.category = expenseData.find((row) => String(row.id) === String(draft.subcategory.categoryId));
        } else if (formType === "animal") {
            draft.category = bestMatchByLabel(animalData, leadEntitySegment || normalized, (row) => row.name);
            const subRows = animalData.flatMap((row) => (row.subcategories || []).map((sub) => ({ ...sub, categoryId: row.id })));
            draft.subcategory = bestMatchByLabel(subRows, leadEntitySegment || subjectSegment || normalized, (row) => row.name);
            if (!draft.category && draft.subcategory) draft.category = animalData.find((row) => String(row.id) === String(draft.subcategory.categoryId));
        } else if (formType === "seed") {
            draft.category = bestMatchByLabel(seedData, leadEntitySegment || normalized, (row) => row.name);
            const itemRows = seedData.flatMap((row) => (row.items || []).map((item) => ({ ...item, categoryId: row.id })));
            draft.item = bestMatchByLabel(itemRows, leadEntitySegment || subjectSegment || normalized, (row) => row.name);
            if (!draft.category && draft.item) draft.category = seedData.find((row) => String(row.id) === String(draft.item.categoryId));
        } else if (formType === "tool") {
            draft.category = bestMatchByLabel(toolData, leadEntitySegment || normalized, (row) => row.name);
            const itemRows = toolData.flatMap((row) => (row.items || []).map((item) => ({ ...item, categoryId: row.id })));
            draft.item = bestMatchByLabel(itemRows, leadEntitySegment || subjectSegment || normalized, (row) => row.name);
            if (!draft.category && draft.item) draft.category = toolData.find((row) => String(row.id) === String(draft.item.categoryId));
        } else if (formType === "farm") {
            draft.category = bestMatchByLabel(farmData, leadEntitySegment || normalized, (row) => row.name);
            const itemRows = farmData.flatMap((row) => (row.items || []).map((item) => ({ ...item, categoryId: row.id })));
            draft.item = bestMatchByLabel(itemRows, leadEntitySegment || subjectSegment || normalized, (row) => row.name);
            if (!draft.category && draft.item) draft.category = farmData.find((row) => String(row.id) === String(draft.item.categoryId));
        } else if (formType === "income") {
            draft.categoryName = bestMatchByLabel(incomeCategories, leadEntitySegment || subjectSegment || normalized, (row) => row);
            const itemRows = incomeCategories.flatMap((categoryName) => (incomeData[categoryName]?.items || []).map((item) => ({ ...item, categoryName })));
            draft.item = bestExactNormalizedLabelMatch(itemRows, leadEntitySegment || subjectSegment || normalized, (row) => row.name)
                || bestMatchByLabel(itemRows, leadEntitySegment || subjectSegment || normalized, (row) => row.name);
            if (!draft.categoryName && draft.item) draft.categoryName = draft.item.categoryName;
        }

        return draft;
    }

    function syncRequiredStar(control) {
        const group = control ? control.closest(".input-group") : null;
        const label = group ? group.querySelector("label") : null;
        if (!label) return;
        const existing = label.querySelector(".required-star");
        if (control.required) {
            if (!existing) {
                const star = document.createElement("span");
                star.className = "required-star";
                star.textContent = "*";
                label.appendChild(star);
            }
            return;
        }
        if (existing) existing.remove();
    }

    function setControlRequired(control, isRequired) {
        if (!control) return;
        control.required = Boolean(isRequired);
        syncRequiredStar(control);
    }

    function syncAllRequiredStars() {
        document.querySelectorAll(".input-group input, .input-group select, .input-group textarea").forEach(syncRequiredStar);
    }

    function shouldShowZeroPriceSource(input) {
        if (!input) return false;
        const raw = String(input.value ?? "").trim();
        if (!raw) return true;
        const parsed = Number(raw.replace(",", "."));
        return Number.isFinite(parsed) && parsed === 0;
    }

    function syncZeroPriceSourceField(formType) {
        const config = zeroPriceSourceConfigs.find((entry) => entry.formType === formType);
        if (!config) return;
        const input = document.getElementById(config.priceInputId);
        const wrap = document.getElementById(config.wrapId);
        const select = document.getElementById(config.selectId);
        if (!input || !wrap || !select) return;
        const isVisible = shouldShowZeroPriceSource(input);
        wrap.hidden = !isVisible;
        setControlRequired(select, isVisible);
    }

    function syncAllZeroPriceSourceFields() {
        zeroPriceSourceConfigs.forEach((config) => syncZeroPriceSourceField(config.formType));
    }

    function showPanel(formType, subtitle) {
        formShell.hidden = false;
        document.querySelectorAll("[data-form-panel]").forEach((panel) => { panel.hidden = panel.dataset.formPanel !== formType; });
        activeFormTitle.textContent = panelTitles[formType] || "Form";
        activeFormSubtitle.textContent = subtitle || "{% trans 'Seçilən əməliyyata uyğun form açıldı.' %}";
        syncManualPanelSelection(formType);
        syncZeroPriceSourceField(formType);
        window.scrollTo({ top: formShell.offsetTop - 20, behavior: "smooth" });
    }

    function clearActiveForms() {
        document.querySelectorAll("[data-form-panel] form").forEach((form) => form.reset());
        formShell.hidden = true;
        document.querySelectorAll("[data-form-panel]").forEach((panel) => { panel.hidden = true; });
        manualCodeInput.value = "";
        setVoiceResult("");
        syncManualPanelSelection(null);
        initFormOptions();
        syncAllRequiredStars();
        updateExpenseSubcategories();
        updateAnimalSubcategories();
        updateSeedItems();
        updateToolItems();
        updateFarmItems();
        updateIncomeItems();
        syncAnimalIdentificationState();
        syncAllZeroPriceSourceFields();
    }

    function updateExpenseSubcategories(selectedSubcategoryId) {
        const categorySelect = document.getElementById("expense-category");
        const subcategorySelect = document.getElementById("expense-subcategory");
        const manualWrap = document.getElementById("expense-manual-wrap");
        const manualInput = document.getElementById("expense-manual-name");
        const selectedCategory = expenseData.find((row) => String(row.id) === categorySelect.value);
        const isOther = selectedCategory && selectedCategory.name.includes("Digər");
        if (!selectedCategory) {
            fillOptions(subcategorySelect, [], "Heyvan növünü seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(subcategorySelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        if (isOther) {
            manualWrap.hidden = false;
            fillOptions(subcategorySelect, [], "Heyvan növünü seçin", (row) => ({ value: row.id, label: row.name }));
            subcategorySelect.value = "";
            setControlRequired(subcategorySelect, false);
            setControlRequired(manualInput, true);
            return;
        }
        manualWrap.hidden = true;
        fillOptions(subcategorySelect, selectedCategory.subcategories || [], "Heyvan növünü seçin", (row) => ({ value: row.id, label: row.name }));
        if (selectedSubcategoryId) subcategorySelect.value = String(selectedSubcategoryId);
        setControlRequired(subcategorySelect, true);
        setControlRequired(manualInput, false);
    }

    function updateAnimalSubcategories(selectedSubcategoryId) {
        const categorySelect = document.getElementById("animal-category");
        const subcategorySelect = document.getElementById("animal-subcategory");
        const manualWrap = document.getElementById("animal-manual-wrap");
        const manualInput = document.getElementById("animal-manual-name");
        const selectedCategory = animalData.find((row) => String(row.id) === categorySelect.value);
        const isOther = selectedCategory && selectedCategory.name.includes("Digər");
        if (!selectedCategory) {
            fillOptions(subcategorySelect, [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(subcategorySelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        if (isOther) {
            manualWrap.hidden = false;
            fillOptions(subcategorySelect, [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
            subcategorySelect.value = "";
            setControlRequired(subcategorySelect, false);
            setControlRequired(manualInput, true);
            return;
        }
        manualWrap.hidden = true;
        fillOptions(subcategorySelect, selectedCategory.subcategories || [], "Alt kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        if (selectedSubcategoryId) subcategorySelect.value = String(selectedSubcategoryId);
        setControlRequired(subcategorySelect, true);
        setControlRequired(manualInput, false);
    }

    function updateSeedItems(selectedItemId) {
        const categorySelect = document.getElementById("seed-category");
        const itemSelect = document.getElementById("seed-item");
        const manualWrap = document.getElementById("seed-manual-wrap");
        const manualInput = document.getElementById("seed-manual-name");
        const selectedCategory = seedData.find((row) => String(row.id) === categorySelect.value);
        if (!selectedCategory) {
            fillOptions(itemSelect, [], "Toxum seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(itemSelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        fillOptions(itemSelect, selectedCategory.items || [], "Toxum seçin", (row) => ({ value: row.id, label: row.name }));
        if (selectedItemId) itemSelect.value = String(selectedItemId);
        const selectedText = itemSelect.options[itemSelect.selectedIndex]?.text || "";
        const isOther = selectedCategory.name.includes("Digər") || selectedText === "Digər";
        manualWrap.hidden = !isOther;
        setControlRequired(itemSelect, !isOther);
        setControlRequired(manualInput, isOther);
        setUnitSelectOptions("seed-unit", weightUnits, document.getElementById("seed-unit")?.value || weightUnits[0]);
    }

    function updateToolItems(selectedItemId) {
        const categorySelect = document.getElementById("tool-category");
        const itemSelect = document.getElementById("tool-item");
        const manualWrap = document.getElementById("tool-manual-wrap");
        const manualInput = document.getElementById("tool-manual-name");
        const selectedCategory = toolData.find((row) => String(row.id) === categorySelect.value);
        if (!selectedCategory) {
            fillOptions(itemSelect, [], "Alət seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(itemSelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        fillOptions(itemSelect, selectedCategory.items || [], "Alət seçin", (row) => ({ value: row.id, label: row.name }));
        if (selectedItemId) itemSelect.value = String(selectedItemId);
        const selectedText = itemSelect.options[itemSelect.selectedIndex]?.text || "";
        const isOther = selectedCategory.name.includes("Digər") || selectedText === "Digər";
        manualWrap.hidden = !isOther;
        setControlRequired(itemSelect, !isOther);
        setControlRequired(manualInput, isOther);
    }

    function updateFarmItems(selectedItemId) {
        const categorySelect = document.getElementById("farm-category");
        const itemSelect = document.getElementById("farm-item");
        const unitSelect = document.getElementById("farm-unit");
        const manualWrap = document.getElementById("farm-manual-wrap");
        const manualInput = document.getElementById("farm-manual-name");
        const selectedCategory = farmData.find((row) => String(row.id) === categorySelect.value);
        if (!selectedCategory) {
            fillOptions(itemSelect, [], "Məhsul seçin", (row) => ({ value: row.id, label: row.name }));
            manualWrap.hidden = true;
            setControlRequired(itemSelect, false);
            setControlRequired(manualInput, false);
            return;
        }
        fillOptions(itemSelect, selectedCategory.items || [], "Məhsul seçin", (row) => ({ value: row.id, label: row.name, dataset: { unit: row.unit || "" } }));
        if (selectedItemId) itemSelect.value = String(selectedItemId);
        const selectedOption = itemSelect.options[itemSelect.selectedIndex];
        const isOther = selectedCategory.name.includes("Digər") || selectedOption?.text === "Digər";
        manualWrap.hidden = !isOther;
        setControlRequired(itemSelect, !isOther);
        setControlRequired(manualInput, isOther);
        let units = allUnits.slice();
        const itemUnit = selectedOption?.dataset.unit || "";
        if (itemUnit === "kq") units = weightUnits.slice();
        else if (itemUnit === "litr") units = volumeUnits.slice();
        else if (itemUnit) units = [itemUnit];
        setUnitSelectOptions("farm-unit", units, itemUnit || unitSelect.value || units[0]);
    }

    function normalizeUnitChoices(units) {
        const seen = new Set();
        const ordered = [];
        const priority = ["kq", "kg", "qram", "ton", "litr", "ml", "ədəd", "dəstə", "bağlama"];

        priority.forEach((unit) => {
            if (units.includes(unit) && !seen.has(unit)) {
                seen.add(unit);
                ordered.push(unit);
            }
        });
        units.forEach((unit) => {
            if (!seen.has(unit)) {
                seen.add(unit);
                ordered.push(unit);
            }
        });
        return ordered;
    }

    function setUnitSelectOptions(selectId, units, preferred) {
        const unitSelect = document.getElementById(selectId);
        if (!unitSelect) return;
        const normalizedUnits = normalizeUnitChoices(units);
        fillOptions(unitSelect, normalizedUnits, "Vahid seçin", (value) => ({ value, label: displayUnitLabel(value) }));
        unitSelect.value = preferred && normalizedUnits.includes(preferred) ? preferred : (normalizedUnits[0] || "");
    }

    function displayUnitLabel(unit) {
        if (weightUnitSystem === "lb") {
            if (unit === "kg" || unit === "kq") return "pound";
            if (unit === "qram") return "ounce";
        }
        if (volumeUnitSystem === "gallon") {
            if (unit === "litr") return "gallon";
        }
        return unit === "kg" ? "kq" : (unit === "ml" ? "millilitr" : unit);
    }

    function setIncomeUnits(units, preferred) {
        const unitSelect = document.getElementById("income-unit");
        const normalizedUnits = normalizeUnitChoices(units);
        fillOptions(unitSelect, normalizedUnits, "Vahid seçin", (value) => ({ value, label: displayUnitLabel(value) }));
        unitSelect.value = preferred && normalizedUnits.includes(preferred) ? preferred : (normalizedUnits[0] || "");
    }

    function normalizeQuantityForSubmit(quantityInput, unitSelect) {
        if (!quantityInput || !unitSelect || unitSelect.disabled) return;
        const rawValue = parseFloat(quantityInput.value || "");
        if (!Number.isFinite(rawValue)) return;

        let normalizedValue = rawValue;
        if (weightUnitSystem === "lb") {
            if (unitSelect.value === "kq" || unitSelect.value === "kg") {
                normalizedValue = rawValue * KG_PER_POUND;
            } else if (unitSelect.value === "qram") {
                normalizedValue = rawValue * GRAMS_PER_OUNCE;
            }
        }
        if (volumeUnitSystem === "gallon" && unitSelect.value === "litr") {
            normalizedValue = normalizedValue * LITERS_PER_GALLON;
        }

        quantityInput.value = String(Number(normalizedValue.toFixed(4)));
    }

    function updateIncomeItems(selectedItemName) {
        const categorySelect = document.getElementById("income-category");
        const itemSelect = document.getElementById("income-item");
        const manualWrap = document.getElementById("income-manual-wrap");
        const manualInput = document.getElementById("income-manual-name");
        const genderWrap = document.getElementById("income-gender-wrap");
        const animalIdWrap = document.getElementById("income-animal-id-wrap");
        const genderSelect = document.getElementById("income-gender");
        const selectedCategory = categorySelect.value;
        const row = incomeData[selectedCategory];
        const type = row ? row.type : "other";
        genderWrap.hidden = type !== "animal";
        animalIdWrap.hidden = type !== "animal";
        if (!row) {
            fillOptions(itemSelect, [], "Məhsul seçin", (entry) => ({ value: entry.name, label: entry.name }));
            manualWrap.hidden = true;
            setControlRequired(itemSelect, false);
            setControlRequired(manualInput, false);
            setControlRequired(genderSelect, false);
            setIncomeUnits(allUnits, "kq");
            return;
        }
        fillOptions(itemSelect, row.items || [], "Məhsul seçin", (entry) => ({ value: entry.name, label: entry.name, dataset: { unit: entry.unit || "" } }));
        if (selectedItemName) itemSelect.value = selectedItemName;
        const selectedText = itemSelect.options[itemSelect.selectedIndex]?.text || "";
        const isOther = selectedCategory === "Digər" || selectedText === "Digər";
        manualWrap.hidden = !isOther;
        setControlRequired(itemSelect, !isOther);
        setControlRequired(manualInput, isOther);
        setControlRequired(genderSelect, type === "animal");
        let units = allUnits.slice();
        const itemUnit = itemSelect.options[itemSelect.selectedIndex]?.dataset.unit || "";
        if (type === "seed") units = weightUnits.slice();
        else if (itemUnit === "kq" || itemUnit === "kg" || itemUnit === "qram" || itemUnit === "ton") units = weightUnits.slice();
        else if (itemUnit === "litr") units = volumeUnits.slice();
        else if (type === "animal") units = ["ədəd"];
        else if (itemUnit) units = [itemUnit];
        setIncomeUnits(units, units[0]);
    }

    function initFormOptions() {
        fillOptions(document.getElementById("expense-category"), expenseData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("animal-category"), animalData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("seed-category"), seedData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("tool-category"), toolData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("farm-category"), farmData, "Kateqoriya seçin", (row) => ({ value: row.id, label: row.name }));
        fillOptions(document.getElementById("income-category"), incomeCategories, "Kateqoriya seçin", (row) => ({ value: row, label: row }));
        setIncomeUnits(allUnits, "kq");
        setUnitSelectOptions("seed-unit", weightUnits, document.getElementById("seed-unit")?.value || weightUnits[0]);
        setUnitSelectOptions("farm-unit", allUnits, document.getElementById("farm-unit")?.value || allUnits[0]);
    }

    function applyExpenseRecord(item) {
        showPanel("expense", `${item.label} üçün xərc formu açıldı.`);
        if (item.metadata?.category_id) {
            document.getElementById("expense-category").value = String(item.metadata.category_id);
            updateExpenseSubcategories(item.metadata.subcategory_id);
        }
        if (item.metadata?.subcategory_id) document.getElementById("expense-subcategory").value = String(item.metadata.subcategory_id);
        if (item.target_type === "manual" || item.metadata?.manual_name) {
            document.getElementById("expense-manual-wrap").hidden = false;
            document.getElementById("expense-manual-name").value = item.metadata?.manual_name || item.label || "";
        }
        document.getElementById("expense-amount").value = item.metadata?.amount || "";
        document.getElementById("expense-date").value = item.metadata?.date || "{{ today|date:'Y-m-d' }}";
        document.getElementById("expense-additional-info").value = item.metadata?.additional_info || "";
    }

    function applyAnimalRecord(item) {
        showPanel("animal", `${item.label} üçün heyvan formu açıldı.`);
        if (item.metadata?.category_id) {
            document.getElementById("animal-category").value = String(item.metadata.category_id);
            updateAnimalSubcategories(item.metadata.subcategory_id);
        }
        if (item.metadata?.subcategory_id) document.getElementById("animal-subcategory").value = String(item.metadata.subcategory_id);
        if (item.target_type === "manual" || item.metadata?.manual_name) {
            document.getElementById("animal-manual-wrap").hidden = false;
            document.getElementById("animal-manual-name").value = item.metadata?.manual_name || item.label || "";
        }
        document.getElementById("animal-quantity").value = item.metadata?.quantity || "1";
        document.getElementById("animal-id").value = item.metadata?.identification_no || "";
        syncAnimalIdentificationState();
        document.getElementById("animal-gender").value = item.metadata?.gender || "erkek";
        document.getElementById("animal-weight").value = item.metadata?.weight || "";
        document.getElementById("animal-price").value = item.metadata?.price || "";
        document.getElementById("animal-zero-price-source").value = item.metadata?.zero_price_source || "";
        document.getElementById("animal-date").value = item.metadata?.date || "{{ today|date:'Y-m-d' }}";
        document.getElementById("animal-additional-info").value = item.metadata?.additional_info || "";
        syncZeroPriceSourceField("animal");
    }

    function applySeedRecord(item) {
        showPanel("seed", `${item.label} üçün toxum formu açıldı.`);
        if (item.metadata?.category_id) {
            document.getElementById("seed-category").value = String(item.metadata.category_id);
            updateSeedItems(item.metadata.item_id);
        }
        if (item.metadata?.item_id) document.getElementById("seed-item").value = String(item.metadata.item_id);
        if (item.target_type === "manual" || item.metadata?.manual_name) {
            document.getElementById("seed-manual-wrap").hidden = false;
            document.getElementById("seed-manual-name").value = item.metadata?.manual_name || item.label || "";
        }
        document.getElementById("seed-quantity").value = item.metadata?.quantity || "";
        document.getElementById("seed-unit").value = item.metadata?.unit || "kg";
        document.getElementById("seed-price").value = item.metadata?.price || "";
        document.getElementById("seed-zero-price-source").value = item.metadata?.zero_price_source || "";
        document.getElementById("seed-date").value = item.metadata?.date || "{{ today|date:'Y-m-d' }}";
        document.getElementById("seed-additional-info").value = item.metadata?.additional_info || "";
        syncZeroPriceSourceField("seed");
    }

    function applyToolRecord(item) {
        showPanel("tool", `${item.label} üçün alət formu açıldı.`);
        if (item.metadata?.category_id) {
            document.getElementById("tool-category").value = String(item.metadata.category_id);
            updateToolItems(item.metadata.item_id);
        }
        if (item.metadata?.item_id) document.getElementById("tool-item").value = String(item.metadata.item_id);
        if (item.target_type === "manual" || item.metadata?.manual_name) {
            document.getElementById("tool-manual-wrap").hidden = false;
            document.getElementById("tool-manual-name").value = item.metadata?.manual_name || item.label || "";
        }
        document.getElementById("tool-quantity").value = item.metadata?.quantity || "";
        document.getElementById("tool-price").value = item.metadata?.price || "";
        document.getElementById("tool-zero-price-source").value = item.metadata?.zero_price_source || "";
        document.getElementById("tool-date").value = item.metadata?.date || "{{ today|date:'Y-m-d' }}";
        document.getElementById("tool-additional-info").value = item.metadata?.additional_info || "";
        syncZeroPriceSourceField("tool");
    }

    function applyFarmRecord(item) {
        showPanel("farm", `${item.label} üçün təsərrüfat formu açıldı.`);
        if (item.metadata?.category_id) {
            document.getElementById("farm-category").value = String(item.metadata.category_id);
            updateFarmItems(item.metadata.item_id);
        }
        if (item.metadata?.item_id) document.getElementById("farm-item").value = String(item.metadata.item_id);
        if (item.metadata?.unit) document.getElementById("farm-unit").value = item.metadata.unit;
        if (item.target_type === "manual" || item.metadata?.manual_name) {
            document.getElementById("farm-manual-wrap").hidden = false;
            document.getElementById("farm-manual-name").value = item.metadata?.manual_name || item.label || "";
        }
        document.getElementById("farm-quantity").value = item.metadata?.quantity || "";
        document.getElementById("farm-price").value = item.metadata?.price || "";
        document.getElementById("farm-zero-price-source").value = item.metadata?.zero_price_source || "";
        document.getElementById("farm-date").value = item.metadata?.date || "{{ today|date:'Y-m-d' }}";
        document.getElementById("farm-additional-info").value = item.metadata?.additional_info || "";
        syncZeroPriceSourceField("farm");
    }

    function applyIncomeRecord(item) {
        showPanel("income", `${item.label} üçün gəlir formu açıldı.`);
        const categoryName = item.metadata?.category_name || "";
        if (categoryName) {
            document.getElementById("income-category").value = categoryName;
            updateIncomeItems(item.metadata?.item_name || item.label);
        }
        if (item.metadata?.item_name) document.getElementById("income-item").value = item.metadata.item_name;
        if (item.metadata?.unit) document.getElementById("income-unit").value = item.metadata.unit;
        if (item.target_type === "manual" || item.metadata?.manual_name) {
            document.getElementById("income-manual-wrap").hidden = false;
            document.getElementById("income-manual-name").value = item.metadata?.manual_name || item.label || "";
        }
        document.getElementById("income-quantity").value = item.metadata?.quantity || "";
        document.getElementById("income-gender").value = item.metadata?.gender || "";
        document.getElementById("income-animal-id").value = item.metadata?.identification_no || "";
        document.getElementById("income-amount").value = item.metadata?.amount || "";
        document.getElementById("income-date").value = item.metadata?.date || "{{ today|date:'Y-m-d' }}";
        document.getElementById("income-additional-info").value = item.metadata?.additional_info || "";
    }

    function applyVoiceDraft(draft, transcript) {
        draft = coerceDraftForPageMode(draft);
        if (!draft.formType) {
            setResultMessage("Səsdən uyğun form seçmək alınmadı. Məsələn, “xərc əlavə et...” kimi deyin.", true);
            return;
        }
        if (handleBlockedForm(draft.formType)) {
            return;
        }

        const quantityValue = draft.quantity != null ? draft.quantity : "";
        const amountValue = draft.amount != null ? draft.amount : "";
        const priceValue = draft.price != null ? draft.price : "";
        const weightValue = draft.weight != null ? draft.weight : "";
        const dateValue = draft.date || "{{ today|date:'Y-m-d' }}";

        if (draft.formType === "expense") {
            showPanel("expense", voiceFormFilledSubtitles.expense);
            if (draft.category) {
                document.getElementById("expense-category").value = String(draft.category.id);
                updateExpenseSubcategories(draft.subcategory?.id);
            }
            if (draft.subcategory) document.getElementById("expense-subcategory").value = String(draft.subcategory.id);
            if (amountValue !== "") document.getElementById("expense-amount").value = amountValue;
            document.getElementById("expense-date").value = dateValue;
            if (draft.additionalInfo) document.getElementById("expense-additional-info").value = draft.additionalInfo;
        } else if (draft.formType === "income") {
            showPanel("income", voiceFormFilledSubtitles.income);
            if (draft.categoryName) {
                document.getElementById("income-category").value = draft.categoryName;
                updateIncomeItems(draft.item?.name || "");
            }
            if (draft.item) document.getElementById("income-item").value = draft.item.name;
            if (draft.manualName) {
                document.getElementById("income-manual-wrap").hidden = false;
                document.getElementById("income-manual-name").value = draft.manualName;
            }
            if (quantityValue !== "") document.getElementById("income-quantity").value = quantityValue;
            if (draft.unit) document.getElementById("income-unit").value = draft.unit;
            if (draft.gender) document.getElementById("income-gender").value = draft.gender;
            if (draft.identificationNo) document.getElementById("income-animal-id").value = draft.identificationNo;
            if (amountValue !== "" || priceValue !== "") document.getElementById("income-amount").value = amountValue || priceValue;
            document.getElementById("income-date").value = dateValue;
            if (draft.additionalInfo) document.getElementById("income-additional-info").value = draft.additionalInfo;
        } else if (draft.formType === "animal") {
            showPanel("animal", voiceFormFilledSubtitles.animal);
            if (draft.category) {
                document.getElementById("animal-category").value = String(draft.category.id);
                updateAnimalSubcategories(draft.subcategory?.id);
            }
            if (draft.subcategory) document.getElementById("animal-subcategory").value = String(draft.subcategory.id);
            document.getElementById("animal-quantity").value = quantityValue || "1";
            syncAnimalIdentificationState();
            if (draft.identificationNo) document.getElementById("animal-id").value = draft.identificationNo;
            if (draft.gender) document.getElementById("animal-gender").value = draft.gender;
            if (weightValue !== "") document.getElementById("animal-weight").value = weightValue;
            if (priceValue !== "" || amountValue !== "") document.getElementById("animal-price").value = priceValue || amountValue;
            syncZeroPriceSourceField("animal");
            document.getElementById("animal-date").value = dateValue;
            if (draft.additionalInfo) document.getElementById("animal-additional-info").value = draft.additionalInfo;
        } else if (draft.formType === "seed") {
            showPanel("seed", voiceFormFilledSubtitles.seed);
            if (draft.category) {
                document.getElementById("seed-category").value = String(draft.category.id);
                updateSeedItems(draft.item?.id);
            }
            if (draft.item) document.getElementById("seed-item").value = String(draft.item.id);
            if (quantityValue !== "") document.getElementById("seed-quantity").value = quantityValue;
            if (draft.unit) document.getElementById("seed-unit").value = draft.unit;
            if (priceValue !== "" || amountValue !== "") document.getElementById("seed-price").value = priceValue || amountValue;
            syncZeroPriceSourceField("seed");
            document.getElementById("seed-date").value = dateValue;
            if (draft.additionalInfo) document.getElementById("seed-additional-info").value = draft.additionalInfo;
        } else if (draft.formType === "tool") {
            showPanel("tool", voiceFormFilledSubtitles.tool);
            if (draft.category) {
                document.getElementById("tool-category").value = String(draft.category.id);
                updateToolItems(draft.item?.id);
            }
            if (draft.item) document.getElementById("tool-item").value = String(draft.item.id);
            if (quantityValue !== "") document.getElementById("tool-quantity").value = quantityValue;
            if (priceValue !== "" || amountValue !== "") document.getElementById("tool-price").value = priceValue || amountValue;
            syncZeroPriceSourceField("tool");
            document.getElementById("tool-date").value = dateValue;
            if (draft.additionalInfo) document.getElementById("tool-additional-info").value = draft.additionalInfo;
        } else if (draft.formType === "farm") {
            showPanel("farm", voiceFormFilledSubtitles.farm);
            if (draft.category) {
                document.getElementById("farm-category").value = String(draft.category.id);
                updateFarmItems(draft.item?.id);
            }
            if (draft.item) document.getElementById("farm-item").value = String(draft.item.id);
            if (quantityValue !== "") document.getElementById("farm-quantity").value = quantityValue;
            if (draft.unit) document.getElementById("farm-unit").value = draft.unit;
            if (priceValue !== "" || amountValue !== "") document.getElementById("farm-price").value = priceValue || amountValue;
            syncZeroPriceSourceField("farm");
            document.getElementById("farm-date").value = dateValue;
            if (draft.additionalInfo) document.getElementById("farm-additional-info").value = draft.additionalInfo;
        }

        const prettyGuess = buildPrettyVoiceSummary(draft, transcript);
        if (prettyGuess) {
            setVoiceResult(`Deyilən: ${transcript}\nTəxmin edilən: ${prettyGuess}`);
        } else {
            setVoiceResult(`Deyilən: ${transcript}`);
        }
        setResultMessage(voiceAcceptedMessages[draft.formType] || "{% trans 'Səs qəbul olundu və form dolduruldu.' %}");
    }

    function handleVoiceTranscript(transcript) {
        const cleaned = (transcript || "").trim();
        if (!cleaned) {
            setResultMessage("Səs başa düşülmədi. Bir az daha aydın danışın.", true);
            return;
        }
        applyVoiceDraft(buildVoiceDraft(cleaned), cleaned);
    }

    function cleanupVoiceStream() {
        stopVoiceLevelMeter();
        if (voiceStream) {
            voiceStream.getTracks().forEach((track) => track.stop());
            voiceStream = null;
        }
        mediaRecorder = null;
        voiceChunks = [];
        setVoiceRecorderVisible(false);
        syncVoiceButtonLabel();
    }

    async function sendVoiceForTranscription(audioBlob) {
        const formData = new FormData();
        formData.append("audio", audioBlob, "voice-input.webm");
        formData.append("language", activeVoiceLanguage || "az");

        const response = await fetch("{% url 'inventory:voice_transcribe' %}", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCsrfToken(),
                "Accept": "application/json",
            },
            body: formData,
            credentials: "same-origin",
        });
        const contentType = response.headers.get("content-type") || "";
        const rawBody = await response.text();
        let data = null;

        if (contentType.includes("application/json")) {
            try {
                data = JSON.parse(rawBody);
            } catch (error) {
                throw new Error("{% trans 'Səs servisi JSON cavabı pozaq qaytardı.' %}");
            }
        } else {
            const normalizedBody = (rawBody || "").toLowerCase();
            if (normalizedBody.includes("csrf")) {
                throw new Error("{% trans 'CSRF xətası var. Səhifəni yeniləyib yenə yoxlayın.' %}");
            }
            if (normalizedBody.includes("login") || normalizedBody.includes("daxil ol")) {
                throw new Error("{% trans 'Sessiya bitib. Yenidən daxil olun.' %}");
            }
            if (normalizedBody.includes("<html") || normalizedBody.includes("<!doctype") || normalizedBody.includes("<!--")) {
                throw new Error("{% trans 'Səs servisi HTML xəta səhifəsi qaytardı. Server logunu yoxlayın.' %}");
            }
            throw new Error("{% trans 'Səs servisindən gözlənilməyən cavab gəldi.' %}");
        }

        if (!response.ok || !data.success) {
            throw new Error(data.message || "{% trans 'Səs transkripsiyası alınmadı.' %}");
        }
        return data;
    }

    async function finalizeVoiceRecording() {
        if (!voiceChunks.length) {
            voiceTranscribing = false;
            setActionState(null);
            setResultMessage("{% trans 'Səs yazısı boş oldu.' %}", true);
            cleanupVoiceStream();
            return;
        }

        voiceTranscribing = true;
        listening = false;
        syncVoiceButtonLabel();
        setVoiceRecorderVisible(false);
        setVoiceResult("");
        setResultMessage("");

        try {
            const mimeType = mediaRecorder?.mimeType || "audio/webm";
            const audioBlob = new Blob(voiceChunks, { type: mimeType });
            const payload = await sendVoiceForTranscription(audioBlob);
            setVoiceResult(`Deyilən: ${payload.transcript}`);
            handleVoiceTranscript(payload.transcript);
        } catch (error) {
            setActionState(null);
            setResultMessage(error.message || "{% trans 'Səs emalı zamanı xəta oldu.' %}", true);
            setVoiceResult("");
        } finally {
            voiceTranscribing = false;
            setActionState(null);
            cleanupVoiceStream();
        }
    }

    function stopVoiceRecognition() {
        if (mediaRecorder && listening && mediaRecorder.state !== "inactive") {
            listening = false;
            voiceTranscribing = true;
            syncVoiceButtonLabel();
            setVoiceRecorderVisible(false);
            mediaRecorder.stop();
            return;
        }
        listening = false;
        voiceTranscribing = false;
        syncVoiceButtonLabel();
        cleanupVoiceStream();
    }

    async function startVoiceRecognition() {
        ensureVoiceVocabularyReady();
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === "undefined") {
            setResultMessage("{% trans 'Bu cihazda səs yazısı dəstəklənmir.' %}", true);
            return;
        }
        if (voiceTranscribing) {
            setResultMessage("{% trans 'Əvvəlki səs hələ emal olunur.' %}", true);
            return;
        }
        if (listening) {
            stopVoiceRecognition();
            return;
        }

        try {
            stopScanner(false);
            clearActiveForms();
            manualCodeWrapper.hidden = true;
            setActionState("voice");
            setVoiceResult("");
            setVoiceRecorderVisible(true, "Danışın, sistem səsi dinləyir.");

            voiceStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            startVoiceLevelMeter(voiceStream);
            mediaRecorder = new MediaRecorder(voiceStream);
            voiceChunks = [];

            mediaRecorder.addEventListener("dataavailable", function (event) {
                if (event.data && event.data.size > 0) voiceChunks.push(event.data);
            });

            mediaRecorder.addEventListener("stop", function () {
                finalizeVoiceRecording();
            });

            mediaRecorder.start();
            listening = true;
            syncVoiceButtonLabel();
            setResultMessage("{% trans 'Dinlənilir... Bitirmək üçün “Yazını Bitir” düyməsinə basın.' %}");
            setVoiceResult("Mikrofon aktivdir.");
        } catch (error) {
            listening = false;
            setActionState(null);
            cleanupVoiceStream();
            if (error && error.name === "NotAllowedError") {
                setResultMessage("{% trans 'Mikrofona icazə verin.' %}", true);
                return;
            }
            setResultMessage("{% trans 'Səs yazısını başlatmaq olmadı.' %}", true);
        }
    }

    function applyScanItem(item) {
        const manualItem = { label: item.label, metadata: { manual_name: item.name, unit: item.unit || "", category: item.category }, target_type: "manual", form_type: item.form_type };
        if (item.default_price) {
            if (item.form_type === "expense") document.getElementById("expense-amount").value = item.default_price;
            else if (item.form_type === "animal") document.getElementById("animal-price").value = item.default_price;
            else if (item.form_type === "seed") document.getElementById("seed-price").value = item.default_price;
            else if (item.form_type === "tool") document.getElementById("tool-price").value = item.default_price;
            else if (item.form_type === "farm") document.getElementById("farm-price").value = item.default_price;
            else if (item.form_type === "income") document.getElementById("income-amount").value = item.default_price;
        }
        if (item.form_type === "expense") applyExpenseRecord(manualItem);
        if (item.form_type === "animal") applyAnimalRecord(manualItem);
        if (item.form_type === "seed") applySeedRecord(manualItem);
        if (item.form_type === "tool") applyToolRecord(manualItem);
        if (item.form_type === "farm") applyFarmRecord(manualItem);
        if (item.form_type === "income") applyIncomeRecord({ label: item.label, metadata: { category_name: "Digər", manual_name: item.name, unit: item.unit || "ədəd" }, target_type: "manual", form_type: "income" });
    }

    async function fillProductData(scannedCode) {
        setResultMessage(`{% trans 'Kod oxundu:' %} ${scannedCode}`);
        const response = await fetch("{% url 'inventory:scan_lookup' %}?code=" + encodeURIComponent(scannedCode));
        const data = await response.json();
        if (!data.success) {
            const warningMessage = data.message || "Kod tapılmadı.";
            setResultMessage(warningMessage, true);
            window.alert(warningMessage);
            return;
        }
        const item = data.item;
        if (addPageMode === "income") {
            if (item.form_type !== "income" && handleBlockedBarcode(item.form_type)) {
                return;
            }
            applyIncomeRecord(item);
            setResultMessage(`Tapıldı: ${item.label} (${item.code})`);
            return;
        }
        if (addPageMode === "expense") {
            if (item.form_type !== "expense" && handleBlockedBarcode(item.form_type)) {
                return;
            }
            applyExpenseRecord(item);
            setResultMessage(`Tapıldı: ${item.label} (${item.code})`);
            return;
        }
        if (handleBlockedForm(item.form_type)) {
            return;
        }
        if (data.source === "scan_item") applyScanItem(item);
        else if (item.form_type === "expense") applyExpenseRecord(item);
        else if (item.form_type === "animal") applyAnimalRecord(item);
        else if (item.form_type === "seed") applySeedRecord(item);
        else if (item.form_type === "tool") applyToolRecord(item);
        else if (item.form_type === "farm") applyFarmRecord(item);
        else if (item.form_type === "income") applyIncomeRecord(item);
        setResultMessage(`Tapıldı: ${item.label} (${item.code})`);
    }

    async function submitManualCode() {
        const code = manualCodeInput.value.trim();
        if (!code) {
            setResultMessage("{% trans 'Kodu yazın.' %}", true);
            window.alert("{% trans 'Kodu yazın.' %}");
            return;
        }
        await fillProductData(code);
    }

    async function stopScanner(showMessage = true) {
        scanning = false;
        if (controls) { controls.stop(); controls = null; }
        if (videoEl.srcObject) {
            videoEl.srcObject.getTracks().forEach((track) => track.stop());
            videoEl.srcObject = null;
        }
        scannerWrapper.hidden = true;
        syncBarcodeButtonLabel();
        setActionState(manualCodeWrapper.hidden ? null : "manual");
        if (showMessage) setResultMessage("{% trans 'Skan dayandırıldı.' %}");
    }

    async function startScanner() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { setResultMessage("{% trans 'Bu cihazda kamera dəstəklənmir.' %}", true); return; }
        if (scanning) { await stopScanner(true); return; }
        try {
            stopVoiceRecognition();
            clearActiveForms();
            manualCodeWrapper.hidden = true;
            scannerWrapper.hidden = false;
            setActionState("scan");
            setResultMessage("{% trans 'Kamera açılır...' %}");
            await ensureBarcodeLibraryLoaded();
            codeReader = new ZXingBrowser.BrowserMultiFormatReader();
            scanning = true;
            syncBarcodeButtonLabel();
            const devices = await ZXingBrowser.BrowserCodeReader.listVideoInputDevices();
            if (!devices.length) { setResultMessage("{% trans 'Kamera tapılmadı.' %}", true); scanning = false; syncBarcodeButtonLabel(); return; }
            const backCamera = devices.find((device) => /back|rear|environment/i.test(device.label));
            const selectedDeviceId = backCamera ? backCamera.deviceId : devices[0].deviceId;
            controls = await codeReader.decodeFromVideoDevice(selectedDeviceId, videoEl, async (result, error, localControls) => {
                if (result) {
                    if (localControls) localControls.stop();
                    controls = null;
                    await stopScanner(false);
                    await fillProductData(result.getText());
                    return;
                }
                if (error && !(error instanceof ZXingBrowser.NotFoundException)) console.error("Scan error:", error);
            });
            setResultMessage("{% trans 'Barkodu kameraya yaxınlaşdırın.' %}");
        } catch (error) {
            scannerWrapper.hidden = true;
            scanning = false;
            syncBarcodeButtonLabel();
            setResultMessage("{% trans 'Scanner başlatmaq olmadı.' %}", true);
            console.error(error);
        }
    }

    document.getElementById("expense-category").addEventListener("change", () => updateExpenseSubcategories());
    document.getElementById("animal-category").addEventListener("change", () => updateAnimalSubcategories());
    document.getElementById("seed-category").addEventListener("change", () => updateSeedItems());
    document.getElementById("seed-item").addEventListener("change", () => updateSeedItems(document.getElementById("seed-item").value));
    document.getElementById("tool-category").addEventListener("change", () => updateToolItems());
    document.getElementById("tool-item").addEventListener("change", () => updateToolItems(document.getElementById("tool-item").value));
    document.getElementById("farm-category").addEventListener("change", () => updateFarmItems());
    document.getElementById("farm-item").addEventListener("change", () => updateFarmItems(document.getElementById("farm-item").value));
    document.getElementById("income-category").addEventListener("change", () => updateIncomeItems());
    document.getElementById("income-item").addEventListener("change", () => updateIncomeItems(document.getElementById("income-item").value));
    document.getElementById("income-form").addEventListener("submit", () => normalizeQuantityForSubmit(document.getElementById("income-quantity"), document.getElementById("income-unit")));
    document.getElementById("seed-form").addEventListener("submit", () => normalizeQuantityForSubmit(document.getElementById("seed-quantity"), document.getElementById("seed-unit")));
    document.getElementById("farm-form").addEventListener("submit", () => normalizeQuantityForSubmit(document.getElementById("farm-quantity"), document.getElementById("farm-unit")));
    zeroPriceSourceConfigs.forEach((config) => {
        const input = document.getElementById(config.priceInputId);
        if (!input) return;
        input.addEventListener("input", () => syncZeroPriceSourceField(config.formType));
        input.addEventListener("change", () => syncZeroPriceSourceField(config.formType));
    });

    document.getElementById("animal-quantity").addEventListener("input", syncAnimalIdentificationState);

    manualPanelButtons.forEach((button) => {
        button.addEventListener("click", () => {
            stopVoiceRecognition();
            stopScanner(false);
            manualCodeWrapper.hidden = true;
            clearActiveForms();
            setActionState(null);
            showPanel(button.dataset.manualPanel, button.dataset.manualSubtitle || "{% trans 'Seçilən əməliyyata uyğun form açıldı.' %}");
            setResultMessage(button.dataset.manualMessage || "{% trans 'Form açıldı. Məlumatları doldurun.' %}");
        });
    });

    syncBarcodeButtonLabel();
    syncVoiceButtonLabel();
    syncAllZeroPriceSourceFields();
    barcodeBtn.addEventListener("click", startScanner);
    voiceBtn.addEventListener("click", startVoiceRecognition);
    manualCodeToggleBtn.addEventListener("click", function () {
        stopVoiceRecognition();
        stopScanner(false);
        clearActiveForms();
        manualCodeWrapper.hidden = !manualCodeWrapper.hidden;
        setActionState(manualCodeWrapper.hidden ? null : "manual");
        if (!manualCodeWrapper.hidden) {
            setResultMessage("{% trans 'Kodu və ya ID-ni əl ilə yazın.' %}");
            manualCodeInput.focus();
        } else if (!formShell.hidden) {
            setResultMessage("{% trans 'Form açıqdır.' %}");
        } else {
            setResultMessage("");
        }
    });
    manualCodeSubmitBtn.addEventListener("click", submitManualCode);
    manualCodeInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            submitManualCode();
        }
    });
    window.addEventListener("beforeunload", () => {
        stopScanner(false);
        stopVoiceRecognition();
    });

    initFormOptions();
    syncAllRequiredStars();
    updateExpenseSubcategories();
    updateAnimalSubcategories();
    updateSeedItems();
    updateToolItems();
    updateFarmItems();
    updateIncomeItems();
    syncAnimalIdentificationState();

    const initialForm = "{{ initial_form|escapejs }}" || urlParams.get("form");
    const initialManualButton = manualPanelButtons.find((button) => button.dataset.manualPanel === initialForm);
    if (initialManualButton) {
        initialManualButton.click();
    } else if (initialForm && addPageFormTypes.has(initialForm)) {
        const initialSubtitles = {
            income: "{% trans 'Satış formu açıldı.' %}",
            expense: "{% trans 'Xərc formu açıldı.' %}",
            animal: "{% trans 'Heyvan formu açıldı.' %}",
            seed: "{% trans 'Toxum formu açıldı.' %}",
            tool: "{% trans 'Alət formu açıldı.' %}",
            farm: "{% trans 'Məhsul formu açıldı.' %}",
        };
        showPanel(initialForm, initialSubtitles[initialForm] || "{% trans 'Seçilən əməliyyata uyğun form açıldı.' %}");
    }
});

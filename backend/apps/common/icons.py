from __future__ import annotations

from typing import Optional


def _emoji(value: str) -> str:
    return f"emoji:{value}"


def get_animal_icon_by_name(name: Optional[str]) -> str:
    """
    Return a Font Awesome class for a given animal subcategory name.
    """
    mapping = {
        "İnək": _emoji("🐄"),
        "Dana": _emoji("🐮"),
        "Camış": _emoji("🐃"),
        "Qoyun": _emoji("🐑"),
        "Keçi": _emoji("🐐"),
        "Toyuq": _emoji("🐔"),
        "Hinduşka": _emoji("🦃"),
        "Qaz": _emoji("🪿"),
        "Ördək": _emoji("🦆"),
        "Bildircin": _emoji("🐦"),
        "At": _emoji("🐴"),
        "Eşşək": _emoji("🫏"),
        "Qatır": _emoji("🐴"),
    }
    return mapping.get((name or "").strip(), _emoji("🐾"))


def get_animal_icon_for_animal(animal) -> str:
    sub = getattr(getattr(animal, "subcategory", None), "name", None)
    return get_animal_icon_by_name(sub)


def get_tool_icon_by_category(name: Optional[str]) -> str:
    """
    Return a Font Awesome class for a given tool category name.
    """
    mapping = {
        "Elektrikli Alətlər": _emoji("🔌"),
        "Mexaniki Avadanlıqlar": _emoji("⚙️"),
        "Əl Alətləri": _emoji("🛠️"),
        "Suvarma Alətləri": _emoji("💧"),
        "Kənd Texnikası": _emoji("🚜"),
        "Baxım və Təmir": _emoji("🛠️"),
    }
    return mapping.get((name or "").strip(), _emoji("🧰"))


def get_tool_icon_by_name(name: Optional[str]) -> str:
    raw = (name or "").strip().lower()
    if not raw:
        return _emoji("🧰")

    mapping = {
        "bel": _emoji("🛠️"),
        "kürək": _emoji("🪏"),
        "kurek": _emoji("🪏"),
        "dırmıq": _emoji("🪏"),
        "dirmiq": _emoji("🪏"),
        "balta": _emoji("🪓"),
        "bıçaq": _emoji("🔪"),
        "bicag": _emoji("🔪"),
        "mala": _emoji("🛠️"),
        "şlanq": _emoji("💦"),
        "slanq": _emoji("💦"),
        "püskürdücü": _emoji("💦"),
        "puskurdücü": _emoji("💦"),
        "puskurdücu": _emoji("💦"),
        "puskurducu": _emoji("💦"),
        "nasos": _emoji("💧"),
        "vedrə": _emoji("🪣"),
        "vedra": _emoji("🪣"),
        "traktor": _emoji("🚜"),
        "kultivator": _emoji("🚜"),
        "kotan": _emoji("🪏"),
        "səpən": _emoji("🌾"),
        "sepen": _emoji("🌾"),
        "açar dəsti": _emoji("🔧"),
        "acar desti": _emoji("🔧"),
        "drel": _emoji("🪛"),
        "çekic": _emoji("🔨"),
        "çəkic": _emoji("🔨"),
        "lir": _emoji("🧰"),
    }

    for key, icon in mapping.items():
        if key in raw:
            return icon

    return _emoji("🧰")


def get_tool_icon_for_tool(tool) -> str:
    item_name = getattr(getattr(tool, "item", None), "name", None) or getattr(tool, "manual_name", None)
    if item_name:
        return get_tool_icon_by_name(item_name)
    category_name = getattr(getattr(getattr(tool, "item", None), "category", None), "name", None)
    return get_tool_icon_by_category(category_name)


def get_seed_icon() -> str:
    return _emoji("🌱")


def get_seed_icon_by_name(name: Optional[str]) -> str:
    raw = (name or "").strip().lower()
    if not raw:
        return get_seed_icon()

    mapping = {
        "alma": _emoji("🍎"),
        "armud": _emoji("🍐"),
        "ərik": _emoji("🍑"),
        "erik": _emoji("🍑"),
        "şaftalı": _emoji("🍑"),
        "safteri": _emoji("🍑"),
        "gilas": _emoji("🍒"),
        "albalı": _emoji("🍒"),
        "albali": _emoji("🍒"),
        "alça": _emoji("🍒"),
        "gavalı": _emoji("🍒"),
        "nar": _emoji("🍎"),
        "heyva": _emoji("🍐"),
        "üzüm": _emoji("🍇"),
        "uzum": _emoji("🍇"),
        "limon": _emoji("🍋"),
        "portağal": _emoji("🍊"),
        "portagal": _emoji("🍊"),
        "mandarin": _emoji("🍊"),
        "xiyar": _emoji("🥒"),
        "pomidor": _emoji("🍅"),
        "kartof": _emoji("🥔"),
        "soğan": _emoji("🧅"),
        "sogan": _emoji("🧅"),
        "sarımsaq": _emoji("🧄"),
        "sarismaq": _emoji("🧄"),
        "badımcan": _emoji("🍆"),
        "badimcan": _emoji("🍆"),
        "bibər": _emoji("🌶️"),
        "biber": _emoji("🌶️"),
        "kök": _emoji("🥕"),
        "kok": _emoji("🥕"),
        "çuğundur": _emoji("🥕"),
        "cugundur": _emoji("🥕"),
        "kələm": _emoji("🥬"),
        "kelem": _emoji("🥬"),
        "kahı": _emoji("🥬"),
        "kahi": _emoji("🥬"),
        "ispanaq": _emoji("🥬"),
        "noxud": _emoji("🫘"),
        "lobya": _emoji("🫘"),
        "paxla": _emoji("🫘"),
        "paxlalı": _emoji("🫘"),
        "paxlali": _emoji("🫘"),
        "paxlalılar": _emoji("🫘"),
        "paxlalilar": _emoji("🫘"),
        "mərcimək": _emoji("🫘"),
        "mercimek": _emoji("🫘"),
        "soya": _emoji("🫘"),
        "qarğıdalı": _emoji("🌽"),
        "qargidali": _emoji("🌽"),
        "buğda": _emoji("🌾"),
        "bugda": _emoji("🌾"),
        "arpa": _emoji("🌾"),
        "çovdar": _emoji("🌾"),
        "covdar": _emoji("🌾"),
        "vələmir": _emoji("🌾"),
        "velemir": _emoji("🌾"),
        "çəltik": _emoji("🌾"),
        "celtik": _emoji("🌾"),
        "günəbaxan": _emoji("🌻"),
        "gunebaxan": _emoji("🌻"),
        "pambıq": _emoji("🧵"),
        "pambiq": _emoji("🧵"),
        "şəkər çuğunduru": _emoji("🥕"),
        "seker cugunduru": _emoji("🥕"),
        "şəkər cügenduru": _emoji("🥕"),
        "seker cugendur": _emoji("🥕"),
        "çuğundur": _emoji("🥕"),
        "cugundur": _emoji("🥕"),
        "yonca": _emoji("🍀"),
        "koronilla": _emoji("🍀"),
        "seradella": _emoji("🍀"),
        "qarpız": _emoji("🍉"),
        "qarpiz": _emoji("🍉"),
        "qovun": _emoji("🍈"),
        "yemiş": _emoji("🍈"),
        "yemis": _emoji("🍈"),
        "balqabaq": _emoji("🎃"),
        "bostan": _emoji("🍉"),
        "kabaq": _emoji("🎃"),
        "kabak": _emoji("🎃"),
        "boranı": _emoji("🎃"),
        "borani": _emoji("🎃"),
        "zucchini": _emoji("🥒"),
    }

    for key, icon in mapping.items():
        if key in raw:
            return icon

    return get_seed_icon()


def get_seed_icon_for_seed(seed) -> str:
    name = getattr(getattr(seed, "item", None), "name", None) or getattr(seed, "manual_name", None)
    return get_seed_icon_by_name(name)


def get_expense_icon(expense) -> str:
    """
    Determine the icon for an Expense.

    Priority:
    1. If linked to Seed / Tool / Animal, reuse that entity's icon.
    2. Otherwise fall back to expense subcategory name mapping.
    """
    obj = getattr(expense, "content_object", None)
    if obj is not None:
        app_label = getattr(getattr(obj, "_meta", None), "app_label", "")
        model_name = getattr(getattr(obj, "_meta", None), "model_name", "")

        if app_label == "animals" and model_name == "animal":
            return get_animal_icon_for_animal(obj)
        if app_label == "tools" and model_name == "tool":
            return get_tool_icon_for_tool(obj)
        if app_label == "seeds" and model_name == "seed":
            return get_seed_icon_for_seed(obj)

    name = getattr(getattr(expense, "subcategory", None), "name", None)
    if not name:
        name = getattr(expense, "title", None) or getattr(expense, "manual_name", None)
    mapping = {
        "Yem": _emoji("🌾"),
        "Baytarlıq": _emoji("🩺"),
        "Baytar": _emoji("🩺"),
        "Peyvəndləmə": _emoji("💉"),
        "Heyvan alışı": _emoji("🐄"),
        "Toxumlar": get_seed_icon(),
        "Gübrə": _emoji("🪴"),
        "Gubre": _emoji("🪴"),
        "Gübre": _emoji("🪴"),
        "Pesticidlər": _emoji("🪲"),
        "Suvarma": _emoji("💧"),
        "Maaşlar": _emoji("💵"),
        "Sığorta": _emoji("🛡️"),
        "Yanacaq": _emoji("⛽"),
        "Təmir və Baxım": _emoji("🛠️"),
        "Texnika alışı": _emoji("🚜"),
        "Elektrik": _emoji("⚡"),
        "Su": _emoji("🚰"),
        "Tikinti": _emoji("🧱"),
        "Nəqliyyat": _emoji("🚚"),
        "Qablaşdırma": _emoji("📦"),
        "Vergilər": _emoji("🧾"),
        "Kredit faizləri": _emoji("📈"),
        "Xüsusi xərc": _emoji("📝"),
        "Xüsusi xerc": _emoji("📝"),
        "Xususi xerc": _emoji("📝"),
        "Xususi xərç": _emoji("📝"),
        "Xüsusi məbləğ": _emoji("📝"),
        "Xüsusi mebleg": _emoji("📝"),
        "Digər": _emoji("🧩"),
    }
    key = (name or "").strip()
    if key:
        for k, v in mapping.items():
            if k.lower() in key.lower():
                return v
    return mapping.get(key, _emoji("💰"))

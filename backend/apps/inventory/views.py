import hashlib
import json
import os
import tempfile
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Case, DecimalField, F, IntegerField, Q, Sum, Value, When
from django.shortcuts import redirect, render, resolve_url
from django.utils import timezone
from django.utils.translation import get_language, gettext as _T, gettext_lazy as _, override
from django.views.decorators.http import require_POST

from expenses.models import Expense, ExpenseCategory
from incomes.models import Income
from incomes.views import _build_category_payload, _get_income_icon

from common.formatting import format_currency
from common.icons import (
    get_animal_icon_by_name,
    get_animal_icon_for_animal,
    get_expense_icon,
    get_farm_product_icon_by_name,
    get_farm_product_icon_for_product,
    get_seed_icon_by_name,
    get_seed_icon_for_seed,
    get_tool_icon_by_name,
    get_tool_icon_for_tool,
)
from common.messages import add_crud_success_message
from common.zero_price_source import ZERO_PRICE_SOURCE_CHOICES, get_zero_price_source_label
from common.expense_titles import translate_expense_title
from animals.models import Animal, AnimalCategory, AnimalSubCategory
from common.category_order import (
    ANIMAL_CATEGORY_ORDER,
    ANIMAL_SUBCATEGORY_ORDER,
    FARM_PRODUCT_CATEGORY_ORDER,
    FARM_PRODUCT_ITEM_ORDER,
    SEED_CATEGORY_ORDER,
    SEED_ITEM_ORDER,
    TOOL_CATEGORY_ORDER,
    TOOL_ITEM_ORDER,
    order_queryset_by_name_list,
)
from farm_products.models import FarmProduct, FarmProductCategory, FarmProductItem
from seeds.models import Seed, SeedCategory, SeedItem
from tools.models import Tool, ToolCategory, ToolItem

from .models import ScanItem, UserBarcode

ADD_PAGE_CATALOG_CACHE_KEY = "inventory:add-page-catalog:v1"
ADD_PAGE_CATALOG_CACHE_TTL = 300
STOCKS_PAGE_CACHE_TTL = 20
ADD_PRODUCT_SIDE_LIST_LIMIT = 40

FARM_PRODUCT_NAME_TRANSLATIONS = {
    "en": {
        "İnək südü": "Cow milk",
        "Camış südü": "Buffalo milk",
        "Keçi südü": "Goat milk",
        "İnək pendiri": "Cow cheese",
        "Camış pendiri": "Buffalo cheese",
        "Keçi pendiri": "Goat cheese",
        "Qatıq": "Yogurt",
        "Ayran": "Ayran",
        "Kərə yağı": "Butter",
        "Qaymaq": "Cream",
        "Toyuq yumurtası": "Chicken egg",
        "Hinduşka yumurtası": "Turkey egg",
        "Qaz yumurtası": "Goose egg",
        "Ördək yumurtası": "Duck egg",
        "Bildircin yumurtası": "Quail egg",
        "Mal əti": "Beef",
        "Camış əti": "Buffalo meat",
        "Qoyun əti": "Sheep meat",
        "Keçi əti": "Goat meat",
        "Toyuq əti": "Chicken meat",
        "Hinduşka əti": "Turkey meat",
        "Qaz əti": "Goose meat",
        "Ördək əti": "Duck meat",
        "Bildircin əti": "Quail meat",
        "Alma": "Apple",
        "Armud": "Pear",
        "Şaftalı": "Peach",
        "Ərik": "Apricot",
        "Albalı": "Cherry",
        "Gilas": "Sweet cherry",
        "Nar": "Pomegranate",
        "Üzüm": "Grape",
        "Gavalı": "Plum",
        "Heyva": "Quince",
        "Bibər": "Pepper",
        "Badımcan": "Eggplant",
        "Kahı": "Lettuce",
        "İspanaq": "Spinach",
        "Soğan": "Onion",
        "Sarımsaq": "Garlic",
        "Keşniş": "Coriander",
        "Şüyüt": "Dill",
        "Cəfəri": "Parsley",
        "Yaşıl soğan": "Green onion",
        "Reyhan": "Basil",
        "Tərxun": "Tarragon",
        "Çovdar": "Rye",
        "Vələmir": "Oats",
        "Çəltik": "Rice",
        "Qarpız": "Watermelon",
        "Yemiş": "Melon",
        "Boranı": "Pumpkin",
        "Bal": "Honey",
        "Arı mumu": "Beeswax",
        "Arı südü": "Royal jelly",
        "Mal peyini": "Cow manure",
        "Qoyun peyini": "Sheep manure",
        "Keçi peyini": "Goat manure",
        "Quş peyini": "Bird manure",
        "Kompost": "Compost",
        "Mineral gübrə": "Mineral fertilizer",
    },
    "ru": {
        "İnək südü": "Коровье молоко",
        "Camış südü": "Буйволиное молоко",
        "Keçi südü": "Козье молоко",
        "İnək pendiri": "Коровий сыр",
        "Camış pendiri": "Буйволиный сыр",
        "Keçi pendiri": "Козий сыр",
        "Qatıq": "Йогурт",
        "Ayran": "Айран",
        "Kərə yağı": "Сливочное масло",
        "Qaymaq": "Сливки",
        "Toyuq yumurtası": "Куриное яйцо",
        "Hinduşka yumurtası": "Яйцо индейки",
        "Qaz yumurtası": "Гусиное яйцо",
        "Ördək yumurtası": "Утиное яйцо",
        "Bildircin yumurtası": "Перепелиное яйцо",
        "Mal əti": "Говядина",
        "Camış əti": "Мясо буйвола",
        "Qoyun əti": "Баранина",
        "Keçi əti": "Козлятина",
        "Toyuq əti": "Куриное мясо",
        "Hinduşka əti": "Мясо индейки",
        "Qaz əti": "Гусиное мясо",
        "Ördək əti": "Утиное мясо",
        "Bildircin əti": "Мясо перепела",
        "Alma": "Яблоко",
        "Armud": "Груша",
        "Şaftalı": "Персик",
        "Ərik": "Абрикос",
        "Albalı": "Вишня",
        "Gilas": "Черешня",
        "Nar": "Гранат",
        "Üzüm": "Виноград",
        "Gavalı": "Слива",
        "Heyva": "Айва",
        "Bibər": "Перец",
        "Badımcan": "Баклажан",
        "Kahı": "Латук",
        "İspanaq": "Шпинат",
        "Soğan": "Лук",
        "Sarımsaq": "Чеснок",
        "Keşniş": "Кинза",
        "Şüyüt": "Укроп",
        "Cəfəri": "Петрушка",
        "Yaşıl soğan": "Зеленый лук",
        "Reyhan": "Базилик",
        "Tərxun": "Тархун",
        "Çovdar": "Рожь",
        "Vələmir": "Овес",
        "Çəltik": "Рис",
        "Qarpız": "Арбуз",
        "Yemiş": "Дыня",
        "Boranı": "Тыква",
        "Bal": "Мед",
        "Arı mumu": "Пчелиный воск",
        "Arı südü": "Маточное молочко",
        "Mal peyini": "Коровий навоз",
        "Qoyun peyini": "Овечий навоз",
        "Keçi peyini": "Козий навоз",
        "Quş peyini": "Птичий помет",
        "Kompost": "Компост",
        "Mineral gübrə": "Минеральное удобрение",
    },
}

GENERIC_OPTION_TRANSLATIONS = {
    "en": {
        "Taxıl və Paxlalı Toxumları": "Grain and legume seeds",
        "Yem və Yağlı Bitki Toxumları": "Forage and oil crop seeds",
        "Tərəvəz və Bostan Toxumları": "Vegetable and melon seeds",
        "Meyvə Toxumları": "Fruit seeds",
        "Taxıl toxumları": "Grain seeds",
        "Paxlalı toxumları": "Legume seeds",
        "Yem bitki toxumları": "Forage crop seeds",
        "Yağlı bitki toxumları": "Oil crop seeds",
        "Tərəvəz toxumları": "Vegetable seeds",
        "Bostan toxumları": "Melon seeds",
        "Meyvə toxumları": "Fruit seeds",
    },
    "ru": {
        "Taxıl və Paxlalı Toxumları": "Зерновые и бобовые семена",
        "Yem və Yağlı Bitki Toxumları": "Кормовые и масличные семена",
        "Tərəvəz və Bostan Toxumları": "Семена овощей и бахчевых",
        "Meyvə Toxumları": "Семена фруктов",
        "Taxıl toxumları": "Семена зерновых",
        "Paxlalı toxumları": "Семена бобовых",
        "Yem bitki toxumları": "Семена кормовых культур",
        "Yağlı bitki toxumları": "Семена масличных культур",
        "Tərəvəz toxumları": "Семена овощей",
        "Bostan toxumları": "Семена бахчевых",
        "Meyvə toxumları": "Семена фруктов",
    },
}

_whisper_model = None

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _whisper_model


def _is_forage_item(name: str) -> bool:
    return (name or "").strip().lower() in {"yonca", "koronilla", "seradella"}


def _normalized_text(value):
    return " ".join(str(value or "").split()).strip()


def _normalized_metadata(value):
    if isinstance(value, dict):
        return {
            str(key): _normalized_metadata(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
            if str(key) not in {"date", "additional_info"}
            if _normalized_metadata(val) not in ("", None, [], {})
        }
    if isinstance(value, list):
        return [
            _normalized_metadata(item)
            for item in value
            if _normalized_metadata(item) not in ("", None, [], {})
        ]
    if isinstance(value, str):
        return _normalized_text(value)
    return value


def _barcode_signature_payload(form_type, target_type, label, metadata):
    return {
        "form_type": form_type,
        "target_type": target_type,
        "label": _normalized_text(label).lower(),
        "metadata": _normalized_metadata(metadata or {}),
    }


def _build_user_barcode(form_type, target_type, label, metadata):
    normalized = _barcode_signature_payload(form_type, target_type, label, metadata)
    raw_signature = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()
    barcode = UserBarcode.objects.filter(signature=digest).first()
    if barcode:
        return barcode

    normalized_label = _normalized_text(label)
    normalized_metadata = _normalized_metadata(metadata or {})

    code = None
    for index in range(0, len(digest) - 15, 3):
        chunk = digest[index:index + 15]
        numeric_code = str(int(chunk, 16) % 10**12).zfill(12)
        existing = UserBarcode.objects.filter(code=numeric_code).first()
        if existing and existing.signature != digest:
            continue
        code = numeric_code
        break

    if code is None:
        raise ValueError("Unikal 12 rəqəmli barkod yaratmaq olmadı.")

    barcode = UserBarcode.objects.create(
        code=code,
        form_type=form_type,
        target_type=target_type,
        label=normalized_label,
        metadata=normalized_metadata,
        signature=digest,
    )
    return barcode


def _unique_rows(rows, key_name="name"):
    seen = set()
    result = []
    for row in rows:
        key = _normalized_text(row.get(key_name)).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _build_add_page_catalog(lang_code="az"):
    cache_key = f"{ADD_PAGE_CATALOG_CACHE_KEY}:{lang_code}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    expense_categories = []
    for category in ExpenseCategory.objects.exclude(name="Maliyyə və Digər").prefetch_related("subcategories"):
        expense_categories.append(
            {
                "id": category.id,
                "name": _translate_panel_label(category.name, lang_code),
                "subcategories": _unique_rows([
                    {"id": sub.id, "name": _translate_panel_label(sub.name, lang_code)}
                    for sub in category.subcategories.all()
                ]),
            }
        )
    expense_categories = _unique_rows(expense_categories)

    animal_categories = []
    for category in order_queryset_by_name_list(
        AnimalCategory.objects.all(), ANIMAL_CATEGORY_ORDER
    ).prefetch_related("subcategories"):
        ordered_subcategories = order_queryset_by_name_list(
            category.subcategories.all(),
            ANIMAL_SUBCATEGORY_ORDER.get(category.name, []),
        )
        animal_categories.append(
            {
                "id": category.id,
                "name": _translate_panel_label(category.name, lang_code),
                "subcategories": _unique_rows([
                    {"id": sub.id, "name": _translate_panel_label(sub.name, lang_code)}
                    for sub in ordered_subcategories
                ]),
            }
        )
    animal_categories = _unique_rows(animal_categories)

    seed_categories = []
    for category in order_queryset_by_name_list(
        SeedCategory.objects.all(), SEED_CATEGORY_ORDER
    ).prefetch_related("items"):
        ordered_items = order_queryset_by_name_list(
            category.items.all(),
            SEED_ITEM_ORDER.get(category.name, []),
        )
        seed_categories.append(
            {
                "id": category.id,
                "name": _translate_panel_label(category.name, lang_code),
                "items": _unique_rows([
                    {"id": item.id, "name": _translate_panel_label(item.name, lang_code)}
                    for item in ordered_items
                ]),
            }
        )
    seed_categories = _unique_rows(seed_categories)

    tool_categories = []
    for category in order_queryset_by_name_list(
        ToolCategory.objects.all(), TOOL_CATEGORY_ORDER
    ).prefetch_related("items"):
        ordered_items = order_queryset_by_name_list(
            category.items.all(),
            TOOL_ITEM_ORDER.get(category.name, []),
        )
        tool_categories.append(
            {
                "id": category.id,
                "name": _translate_panel_label(category.name, lang_code),
                "items": _unique_rows([
                    {"id": item.id, "name": _translate_panel_label(item.name, lang_code)}
                    for item in ordered_items
                ]),
            }
        )
    tool_categories = _unique_rows(tool_categories)

    farm_categories = []
    for category in order_queryset_by_name_list(
        FarmProductCategory.objects.all(), FARM_PRODUCT_CATEGORY_ORDER
    ).prefetch_related("items"):
        ordered_items = order_queryset_by_name_list(
            category.items.all(),
            FARM_PRODUCT_ITEM_ORDER.get(category.name, []),
        )
        farm_categories.append(
            {
                "id": category.id,
                "name": _translate_panel_label(category.name, lang_code),
                "items": _unique_rows([
                    {"id": item.id, "name": _translate_panel_label(item.name, lang_code), "unit": item.unit or ""}
                    for item in ordered_items
                ]),
            }
        )
    farm_categories = _unique_rows(farm_categories)

    income_categories, income_category_data = _build_category_payload(lang_code)
    income_categories = _unique_rows([{"name": name} for name in income_categories])
    income_categories = [row["name"] for row in income_categories]

    form_types = [
        {"key": "seed", "label": _translate_panel_label("Toxum", lang_code)},
        {"key": "animal", "label": _translate_panel_label("Heyvan", lang_code)},
        {"key": "tool", "label": _translate_panel_label("Alət", lang_code)},
        {"key": "farm", "label": _translate_panel_label("Hazır məhsul", lang_code)},
        {"key": "expense", "label": _translate_panel_label("Xərclər", lang_code)},
        {"key": "income", "label": _translate_panel_label("Gəlirlər", lang_code)},
    ]
    payload = {
        "form_types": form_types,
        "expense_categories": expense_categories,
        "animal_categories": animal_categories,
        "seed_categories": seed_categories,
        "tool_categories": tool_categories,
        "farm_categories": farm_categories,
        "income_categories": income_categories,
        "income_category_data": income_category_data,
    }
    cache.set(cache_key, payload, ADD_PAGE_CATALOG_CACHE_TTL)
    return payload


def _build_add_page_context(request=None):
    voice_input_language = "system"
    add_page_mode = "stock"
    initial_form = ""
    add_page_weekly_total = Decimal("0")
    if request is not None:
        voice_input_language = (request.session.get("voice_input_language") or request.COOKIES.get("voice_input_language") or "system").strip().lower()
        requested_form = (request.GET.get("form") or "").strip().lower()
        if requested_form in {"income", "expense"}:
            add_page_mode = requested_form
            initial_form = requested_form
        elif requested_form in {"animal", "seed", "tool", "farm"}:
            initial_form = requested_form
        if getattr(request, "user", None) and request.user.is_authenticated and add_page_mode in {"income", "expense"}:
            week_start = timezone.localdate() - timedelta(days=7)
            if add_page_mode == "income":
                add_page_weekly_total = (
                    Income.objects.filter(created_by=request.user, date__gte=week_start)
                    .aggregate(total=Sum("amount"))
                    .get("total")
                    or Decimal("0")
                )
            else:
                add_page_weekly_total = (
                    Expense.objects.filter(created_by=request.user, date__gte=week_start)
                    .aggregate(total=Sum("amount"))
                    .get("total")
                    or Decimal("0")
                )
    enabled_form_types = ["seed", "animal", "tool", "farm"]
    if add_page_mode == "income":
        enabled_form_types = ["income"]
    elif add_page_mode == "expense":
        enabled_form_types = ["expense"]

    catalog = _build_add_page_catalog(request.LANGUAGE_CODE if request else "az")
    filtered_catalog = {
        "form_types": [row for row in catalog.get("form_types", []) if row.get("key") in enabled_form_types],
        "expense_categories": catalog.get("expense_categories", []) if "expense" in enabled_form_types else [],
        "animal_categories": catalog.get("animal_categories", []) if "animal" in enabled_form_types else [],
        "seed_categories": catalog.get("seed_categories", []) if "seed" in enabled_form_types else [],
        "tool_categories": catalog.get("tool_categories", []) if "tool" in enabled_form_types else [],
        "farm_categories": catalog.get("farm_categories", []) if "farm" in enabled_form_types else [],
        "income_categories": catalog.get("income_categories", []) if "income" in enabled_form_types else [],
        "income_category_data": catalog.get("income_category_data", {}) if "income" in enabled_form_types else {},
    }
    return {
        "today": timezone.localdate(),
        "voice_input_language": voice_input_language,
        "add_page_mode": add_page_mode,
        "initial_form": initial_form,
        "add_page_weekly_total": add_page_weekly_total,
        "enabled_form_types": enabled_form_types,
        "zero_price_source_choices": ZERO_PRICE_SOURCE_CHOICES,
        **filtered_catalog,
    }


def _set_panel_display_time(item):
    deferred_fields = set()
    if hasattr(item, "get_deferred_fields"):
        deferred_fields = item.get_deferred_fields()

    raw_time = None
    if "time" not in deferred_fields:
        raw_time = getattr(item, "time", None)
    if raw_time:
        item.display_time = raw_time.strftime("%I:%M %p").lstrip("0")
        return

    created_at = getattr(item, "created_at", None)
    if created_at:
        local_created_at = timezone.localtime(created_at) if timezone.is_aware(created_at) else created_at
        item.display_time = local_created_at.strftime("%I:%M %p").lstrip("0")
        return

    item.display_time = ""


def _panel_option_sort_key(value: str) -> tuple[int, str]:
    normalized = _normalized_text(value)
    return (1 if normalized.lower() == str(_("Digər")).lower() else 0, normalized.lower())


def _translate_panel_label(value, lang_code: str):
    text = _normalized_text(value)
    if not text:
        return ""
    with override(lang_code or "az"):
        translated = _T(text)
    lang = (lang_code or "az").split("-")[0]
    if translated == text:
        return (
            FARM_PRODUCT_NAME_TRANSLATIONS.get(lang, {}).get(text)
            or GENERIC_OPTION_TRANSLATIONS.get(lang, {}).get(text)
            or translated
        )
    return translated


def _panel_option_value(value: str) -> str:
    return _normalized_text(value).lower()


def _build_add_page_list_panel_context(user, form_type: str, include_time: bool = True, lang_code: str = "az"):
    side_list_ordering = ["-date", "-updated_at", "-id"]
    if include_time:
        side_list_ordering = ["-date", "-time", "-updated_at", "-id"]

    panel_title_map = {
        "expense": "Xərc Siyahısı",
        "income": "Satış Siyahısı",
        "animal": "Heyvan Siyahısı",
        "seed": "Toxum Siyahısı",
        "tool": "Alət Siyahısı",
        "farm": "Məhsul Siyahısı",
    }
    empty_message_map = {
        "expense": _("Hələ heç bir xərc yoxdur."),
        "income": _("Hələ heç bir satış yoxdur."),
        "animal": _("Hələ heyvan yoxdur."),
        "seed": _("Hələ toxum yoxdur."),
        "tool": _("Hələ alət yoxdur."),
        "farm": _("Hələ məhsul yoxdur."),
    }
    context = {
        "panel_form_type": form_type,
        "panel_title": panel_title_map.get(form_type, ""),
        "panel_items": [],
        "panel_category_options": [],
        "panel_item_options": [],
        "panel_items_by_category": {},
        "panel_empty_message": empty_message_map.get(form_type, _("Məlumat tapılmadı.")),
        "panel_return_path": f"{resolve_url('inventory:add_placeholder')}?{urlencode({'form': form_type})}" if form_type else "",
    }

    def finalize(items):
        context["panel_items"] = items
        catalog = _build_add_page_catalog(lang_code)
        category_options = []
        item_options = []
        catalog_categories = []
        child_key = ""

        if form_type == "expense":
            catalog_categories = catalog.get("expense_categories", [])
            child_key = "subcategories"
            category_options = [row.get("name", "") for row in catalog_categories]
            item_options = [
                row.get("name", "")
                for category in catalog_categories
                for row in category.get(child_key, [])
            ]
        elif form_type == "animal":
            catalog_categories = catalog.get("animal_categories", [])
            child_key = "subcategories"
            category_options = [row.get("name", "") for row in catalog_categories]
            item_options = [
                row.get("name", "")
                for category in catalog_categories
                for row in category.get(child_key, [])
            ]
        elif form_type == "seed":
            catalog_categories = catalog.get("seed_categories", [])
            child_key = "items"
            category_options = [row.get("name", "") for row in catalog_categories]
            item_options = [
                row.get("name", "")
                for category in catalog_categories
                for row in category.get(child_key, [])
            ]
        elif form_type == "tool":
            catalog_categories = catalog.get("tool_categories", [])
            child_key = "items"
            category_options = [row.get("name", "") for row in catalog_categories]
            item_options = [
                row.get("name", "")
                for category in catalog_categories
                for row in category.get(child_key, [])
            ]
        elif form_type == "farm":
            catalog_categories = catalog.get("farm_categories", [])
            child_key = "items"
            category_options = [row.get("name", "") for row in catalog_categories]
            item_options = [
                row.get("name", "")
                for category in catalog_categories
                for row in category.get(child_key, [])
            ]
        elif form_type == "income":
            income_categories = catalog.get("income_categories", [])
            income_category_data = catalog.get("income_category_data", {})
            category_options = list(income_categories)
            item_options = [
                item["name"]
                for category in income_categories
                for item in income_category_data.get(category, {}).get("items", [])
            ]

        unique_categories = []
        seen_categories = set()
        for label in category_options:
            normalized = _normalized_text(label)
            if not normalized or normalized.lower() in seen_categories:
                continue
            seen_categories.add(normalized.lower())
            unique_categories.append(normalized)

        unique_items = []
        seen_items = set()
        for label in item_options:
            normalized = _normalized_text(label)
            if not normalized or normalized.lower() in seen_items:
                continue
            seen_items.add(normalized.lower())
            unique_items.append(normalized)

        context["panel_category_options"] = [
            {"value": _panel_option_value(label), "label": label}
            for label in sorted(unique_categories, key=_panel_option_sort_key)
        ]
        context["panel_item_options"] = [
            {"value": _panel_option_value(label), "label": label}
            for label in sorted(unique_items, key=_panel_option_sort_key)
        ]
        panel_items_by_category = {}
        if form_type in {"expense", "animal", "seed", "tool", "farm"}:
            for category in catalog_categories:
                translated_category = _normalized_text(category.get("name"))
                category_key = _panel_option_value(translated_category)
                panel_items_by_category[category_key] = [
                    {
                        "value": _panel_option_value(_normalized_text(obj.get("name"))),
                        "label": _normalized_text(obj.get("name")),
                    }
                    for obj in category.get(child_key, [])
                ]
        elif form_type == "income":
            for category in income_categories:
                translated_category = _translate_panel_label(category, lang_code)
                category_key = _panel_option_value(translated_category)
                panel_items_by_category[category_key] = [
                    {
                        "value": _panel_option_value(_translate_panel_label(obj["name"], lang_code)),
                        "label": _translate_panel_label(obj["name"], lang_code),
                    }
                    for obj in income_category_data.get(category, {}).get("items", [])
                ]
        context["panel_items_by_category"] = panel_items_by_category
        return context

    if form_type == "expense":
        expense_fields = [
            "id", "title", "amount", "manual_name", "additional_info", "date", "updated_at", "created_at",
            "content_type_id", "object_id", "subcategory__name", "subcategory__category__name",
        ]
        if include_time:
            expense_fields.append("time")
        queryset = (
            Expense.objects.filter(created_by=user)
            .select_related("subcategory", "subcategory__category")
            .only(*expense_fields)
            .order_by(*side_list_ordering)
        )
        items = list(queryset[:ADD_PRODUCT_SIDE_LIST_LIMIT])
        if items:
            from expenses.views import _attach_prefetched_expense_objects

            _attach_prefetched_expense_objects(items)
        for item in items:
            item.icon_class = get_expense_icon(item)
            if item.subcategory:
                item.display_title = _translate_panel_label(item.subcategory.name, lang_code)
            else:
                item.display_title = _translate_panel_label(
                    translate_expense_title(item.manual_name or item.title or ""),
                    lang_code,
                )
            item.filter_item_key = _panel_option_value(item.display_title)
            linked_object = getattr(item, "prefetched_content_object", None)
            if (
                linked_object is not None
                and getattr(getattr(linked_object, "_meta", None), "app_label", "") == "farm_products"
            ):
                farm_name = getattr(getattr(linked_object, "item", None), "name", None) or getattr(linked_object, "manual_name", None)
                if farm_name:
                    item.display_title = f"{_translate_panel_label('Hazır məhsul alışı', lang_code)}: {_translate_panel_label(farm_name, lang_code)}"
            item.display_category_name = (
                _translate_panel_label(item.subcategory.category.name, lang_code) if item.subcategory and item.subcategory.category else _translate_panel_label("Digər", lang_code)
            )
            item.filter_category_key = _panel_option_value(item.display_category_name)
            item.amount_display = format_currency(item.amount, 2)
            _set_panel_display_time(item)
        return finalize(items)

    if form_type == "income":
        income_fields = [
            "id", "category", "item_name", "quantity", "unit", "amount", "gender",
            "date", "additional_info", "updated_at", "created_at",
        ]
        if include_time:
            income_fields.append("time")
        queryset = (
            Income.objects.filter(created_by=user)
            .only(*income_fields)
            .order_by(*side_list_ordering)
        )
        items = list(queryset[:ADD_PRODUCT_SIDE_LIST_LIMIT])
        for item in items:
            item.icon_class = _get_income_icon(item.category, item.item_name)
            item.display_title = _translate_panel_label(item.item_name or "", lang_code)
            item.display_category_name = _translate_panel_label(item.category or "Digər", lang_code)
            item.filter_item_key = _panel_option_value(item.display_title)
            item.filter_category_key = _panel_option_value(item.display_category_name)
            item.amount_display = format_currency(item.amount, 2)
            _set_panel_display_time(item)
        return finalize(items)

    if form_type == "animal":
        animal_fields = [
            "id", "quantity", "date", "weight", "gender", "identification_no", "manual_name",
            "additional_info", "price", "updated_at", "zero_price_source", "created_at",
            "subcategory__name", "subcategory__category__name",
        ]
        if include_time:
            animal_fields.append("time")
        queryset = (
            Animal.objects.filter(created_by=user)
            .exclude(quantity=0)
            .exclude(additional_info__icontains="Gəlir stoku | income:")
            .select_related("subcategory", "subcategory__category")
            .only(*animal_fields)
            .order_by(*side_list_ordering)
        )
        items = list(queryset[:ADD_PRODUCT_SIDE_LIST_LIMIT])
        for item in items:
            item.icon_class = get_animal_icon_for_animal(item)
            item.display_title = _translate_panel_label(item.subcategory.name if item.subcategory else (item.manual_name or ""), lang_code)
            item.display_category_name = (
                _translate_panel_label(item.subcategory.category.name, lang_code) if item.subcategory and item.subcategory.category else _translate_panel_label("Digər", lang_code)
            )
            item.filter_item_key = _panel_option_value(item.display_title)
            item.filter_category_key = _panel_option_value(item.display_category_name)
            item.display_additional_info = str(item.additional_info or "").strip()
            item.zero_price_source_label = get_zero_price_source_label(item)
            _set_panel_display_time(item)
        return finalize(items)

    if form_type == "seed":
        seed_fields = [
            "id", "quantity", "unit", "price", "date", "manual_name", "additional_info",
            "updated_at", "zero_price_source", "item__name", "item__category__name", "created_at",
        ]
        if include_time:
            seed_fields.append("time")
        queryset = (
            Seed.objects.filter(created_by=user)
            .select_related("item", "item__category")
            .only(*seed_fields)
            .order_by(*side_list_ordering)
        )
        items = list(queryset[:ADD_PRODUCT_SIDE_LIST_LIMIT])
        for item in items:
            item.icon_class = get_seed_icon_for_seed(item)
            item.display_title = _translate_panel_label(item.item.name if item.item else (item.manual_name or ""), lang_code)
            item.display_category_name = _translate_panel_label(item.item.category.name if item.item and item.item.category else "Digər", lang_code)
            item.filter_item_key = _panel_option_value(item.display_title)
            item.filter_category_key = _panel_option_value(item.display_category_name)
            item.price_display = format_currency(abs(Decimal(item.price or 0)), 2)
            item.zero_price_source_label = get_zero_price_source_label(item)
            _set_panel_display_time(item)
        return finalize(items)

    if form_type == "tool":
        tool_fields = [
            "id", "quantity", "price", "date", "manual_name", "additional_info",
            "updated_at", "zero_price_source", "item__name", "item__category__name", "created_at",
        ]
        if include_time:
            tool_fields.append("time")
        queryset = (
            Tool.objects.filter(created_by=user)
            .select_related("item", "item__category")
            .only(*tool_fields)
            .order_by(*side_list_ordering)
        )
        items = list(queryset[:ADD_PRODUCT_SIDE_LIST_LIMIT])
        for item in items:
            item.icon_class = get_tool_icon_for_tool(item)
            item.display_title = _translate_panel_label(item.item.name if item.item else (item.manual_name or ""), lang_code)
            item.display_category_name = _translate_panel_label(item.item.category.name if item.item and item.item.category else "Digər", lang_code)
            item.filter_item_key = _panel_option_value(item.display_title)
            item.filter_category_key = _panel_option_value(item.display_category_name)
            item.price_display = format_currency(abs(Decimal(item.price or 0)), 2)
            item.zero_price_source_label = get_zero_price_source_label(item)
            _set_panel_display_time(item)
        return finalize(items)

    if form_type == "farm":
        farm_fields = [
            "id", "quantity", "unit", "price", "date", "manual_name", "additional_info",
            "updated_at", "zero_price_source", "item__name", "item__category__name", "created_at",
        ]
        if include_time:
            farm_fields.append("time")
        queryset = (
            FarmProduct.objects.filter(created_by=user)
            .select_related("item", "item__category")
            .only(*farm_fields)
            .order_by(*side_list_ordering)
        )
        items = list(queryset[:ADD_PRODUCT_SIDE_LIST_LIMIT])
        for item in items:
            item.icon_class = get_farm_product_icon_for_product(item)
            item.display_title = _translate_panel_label(item.item.name if item.item else (item.manual_name or ""), lang_code)
            item.display_category_name = _translate_panel_label(item.item.category.name if item.item and item.item.category else "Digər", lang_code)
            item.filter_item_key = _panel_option_value(item.display_title)
            item.filter_category_key = _panel_option_value(item.display_category_name)
            item.price_display = format_currency(abs(Decimal(item.price or 0)), 2)
            item.zero_price_source_label = get_zero_price_source_label(item)
            _set_panel_display_time(item)
        return finalize(items)

    return context


def _resolve_voice_language(request, explicit_language: str | None = None):
    allowed = {"az", "en", "ru"}
    candidate = (explicit_language or "").strip().lower()
    if candidate == "system":
        candidate = ""
    if not candidate:
        candidate = (
            request.session.get("voice_input_language")
            or request.COOKIES.get("voice_input_language")
            or ""
        ).strip().lower()
    if candidate == "system":
        candidate = ""
    if not candidate:
        candidate = (getattr(request, "LANGUAGE_CODE", "") or "").split("-")[0].lower()
    return candidate if candidate in allowed else "az"


def home(request):
    return HttpResponse("Home page")


def _convert_farm_qty(value: Decimal, unit: str, base_unit: str) -> Decimal:
    if base_unit == "kq":
        if unit == "ton":
            return value * Decimal("1000")
        if unit == "qram":
            return value / Decimal("1000")
        return value
    if base_unit == "litr":
        if unit == "ml":
            return value / Decimal("1000")
        return value
    return value


@login_required
def dashboard(request):
    return HttpResponse("Dashboard ✅ You are logged in.")


@login_required
def stocks_placeholder(request):
    user = request.user
    lang_code = get_language() or "az"
    cache_key = f"inventory:stocks-page:v4:user:{user.id}:lang:{lang_code}"
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return render(request, "inventory/stocks.html", cached_context)

    seed_categories = list(order_queryset_by_name_list(SeedCategory.objects.all(), SEED_CATEGORY_ORDER))
    tool_categories = list(order_queryset_by_name_list(ToolCategory.objects.all(), TOOL_CATEGORY_ORDER))
    animal_categories = list(order_queryset_by_name_list(AnimalCategory.objects.all(), ANIMAL_CATEGORY_ORDER))
    farm_product_categories = list(
        order_queryset_by_name_list(FarmProductCategory.objects.all(), FARM_PRODUCT_CATEGORY_ORDER)
    )
    farm_diger_category_id = next((cat.id for cat in farm_product_categories if cat.name == "Digər"), None)

    items = []

    seed_total_expr = Sum(
        Case(
            When(unit__in=["kg", "kq"], then=F("quantity")),
            When(unit="ton", then=F("quantity") * Value(Decimal("1000"))),
            When(unit="qram", then=F("quantity") / Value(Decimal("1000"))),
            default=F("quantity"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    seed_totals = {
        row["item_id"]: {
            "name": row["item__name"],
            "category_id": row["item__category_id"],
            "category_name": row["item__category__name"] or "",
            "total_kg": row["total_kg"] or Decimal("0"),
        }
        for row in (
            Seed.objects.filter(created_by=user, item__isnull=False)
            .exclude(item__name__iexact="Digər")
            .values("item_id", "item__name", "item__category_id", "item__category__name")
            .annotate(total_kg=seed_total_expr)
        )
    }
    seed_items = SeedItem.objects.select_related("category").only(
        "id", "name", "category_id", "category__name"
    ).exclude(name__iexact="Digər")
    for item in seed_items:
        if item.id not in seed_totals:
            seed_totals[item.id] = {
                "name": item.name,
                "category_id": item.category_id,
                "category_name": item.category.name if item.category else "",
                "total_kg": Decimal("0"),
            }

    for item_id, payload in seed_totals.items():
        qty_display = f"{payload['total_kg']:.2f}"
        items.append(
            {
                "main": "toxumlar",
                "sub_key": f"seedcat-{payload['category_id']}",
                "title": payload["name"],
                "subtitle": payload["category_name"],
                "quantity": payload["total_kg"],
                "quantity_display": qty_display,
                "unit": "kq",
                "icon": get_seed_icon_by_name(payload["name"]),
                "update_type": "seed",
                "update_id": item_id,
                "input_step": "0.01",
            }
        )

    tool_totals = {
        row["item_id"]: {
            "name": row["item__name"],
            "category_id": row["item__category_id"],
            "category_name": row["item__category__name"] or "",
            "total_qty": row["total_qty"] or 0,
        }
        for row in (
            Tool.objects.filter(created_by=user, item__isnull=False)
            .exclude(item__name__iexact="Digər")
            .values("item_id", "item__name", "item__category_id", "item__category__name")
            .annotate(total_qty=Sum("quantity"))
        )
    }

    tool_items = ToolItem.objects.select_related("category").only(
        "id", "name", "category_id", "category__name"
    ).exclude(name__iexact="Digər")
    for item in tool_items:
        if item.id not in tool_totals:
            tool_totals[item.id] = {
                "name": item.name,
                "category_id": item.category_id,
                "category_name": item.category.name if item.category else "",
                "total_qty": 0,
            }

    for item_id, payload in tool_totals.items():
        qty_display = str(payload["total_qty"])
        items.append(
            {
                "main": "aletler",
                "sub_key": f"toolcat-{payload['category_id']}",
                "title": payload["name"],
                "subtitle": payload["category_name"],
                "quantity": payload["total_qty"],
                "quantity_display": qty_display,
                "unit": "ədəd",
                "icon": get_tool_icon_by_name(payload["name"]),
                "update_type": "tool",
                "update_id": item_id,
                "input_step": "1",
            }
        )

    animal_totals = {
        row["subcategory_id"]: {
            "name": row["subcategory__name"],
            "category_id": row["subcategory__category_id"],
            "category_name": row["subcategory__category__name"] or "",
            "total_qty": row["total_qty"] or 0,
            "male_qty": row["male_qty"] or 0,
            "female_qty": row["female_qty"] or 0,
        }
        for row in (
            Animal.objects.filter(created_by=user, subcategory__isnull=False)
            .exclude(quantity=0)
            .exclude(subcategory__name__iexact="Digər")
            .values("subcategory_id", "subcategory__name", "subcategory__category_id", "subcategory__category__name")
            .annotate(
                total_qty=Sum("quantity"),
                male_qty=Sum(
                    Case(
                        When(gender="erkek", then=F("quantity")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ),
                female_qty=Sum(
                    Case(
                        When(gender="disi", then=F("quantity")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ),
            )
        )
    }

    animal_subs = AnimalSubCategory.objects.select_related("category").only(
        "id", "name", "category_id", "category__name"
    ).exclude(name__iexact="Digər")
    for sub in animal_subs:
        if sub.id not in animal_totals:
            animal_totals[sub.id] = {
                "name": sub.name,
                "category_id": sub.category_id,
                "category_name": sub.category.name if sub.category else "",
                "total_qty": 0,
            }

    for sub_id, payload in animal_totals.items():
        qty_display = str(payload["total_qty"])
        male_qty = payload.get("male_qty", 0)
        female_qty = payload.get("female_qty", 0)
        items.append(
            {
                "main": "heyvanlar",
                "sub_key": f"animalcat-{payload['category_id']}",
                "title": payload["name"],
                "subtitle": payload["category_name"],
                "quantity": payload["total_qty"],
                "quantity_display": qty_display,
                "male_display": str(male_qty),
                "female_display": str(female_qty),
                "unit": "ədəd",
                "icon": get_animal_icon_by_name(payload["name"]),
                "update_type": "animal_sub",
                "update_id": sub_id,
                "input_step": "1",
            }
        )

    seed_other_totals = {
        (row["manual_name"] or "").strip(): {
            "name": (row["manual_name"] or "").strip(),
            "total_kg": row["total_kg"] or Decimal("0"),
        }
        for row in (
            Seed.objects.filter(created_by=user)
            .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
            .exclude(manual_name__isnull=True)
            .exclude(manual_name="")
            .exclude(manual_name__iexact="Digər")
            .values("manual_name")
            .annotate(total_kg=seed_total_expr)
        )
    }

    for name, payload in seed_other_totals.items():
        qty_display = f"{payload['total_kg']:.2f}"
        items.append(
            {
                "main": "diger",
                "sub_key": "diger-toxumlar",
                "title": payload["name"],
                "subtitle": "Toxumlar (Digər)",
                "quantity": payload["total_kg"],
                "quantity_display": qty_display,
                "unit": "kq",
                "icon": get_seed_icon_by_name(payload["name"]),
                "update_type": "seed_other",
                "update_id": name,
                "input_step": "0.01",
            }
        )

    tool_other_totals = {
        (row["manual_name"] or "").strip(): {
            "name": (row["manual_name"] or "").strip(),
            "total_qty": row["total_qty"] or 0,
        }
        for row in (
            Tool.objects.filter(created_by=user)
            .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
            .exclude(manual_name__isnull=True)
            .exclude(manual_name="")
            .exclude(manual_name__iexact="Digər")
            .values("manual_name")
            .annotate(total_qty=Sum("quantity"))
        )
    }

    for name, payload in tool_other_totals.items():
        qty_display = str(payload["total_qty"])
        items.append(
            {
                "main": "diger",
                "sub_key": "diger-aletler",
                "title": payload["name"],
                "subtitle": "Alətlər (Digər)",
                "quantity": payload["total_qty"],
                "quantity_display": qty_display,
                "unit": "ədəd",
                "icon": get_tool_icon_by_name(payload["name"]),
                "update_type": "tool_other",
                "update_id": name,
                "input_step": "1",
            }
        )

    animal_other_totals = {
        (row["manual_name"] or "").strip(): {
            "name": (row["manual_name"] or "").strip(),
            "total_qty": row["total_qty"] or 0,
            "male_qty": row["male_qty"] or 0,
            "female_qty": row["female_qty"] or 0,
        }
        for row in (
            Animal.objects.filter(created_by=user)
            .exclude(quantity=0)
            .filter(Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər"))
            .exclude(manual_name__isnull=True)
            .exclude(manual_name="")
            .exclude(manual_name__iexact="Digər")
            .values("manual_name")
            .annotate(
                total_qty=Sum("quantity"),
                male_qty=Sum(
                    Case(
                        When(gender="erkek", then=F("quantity")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ),
                female_qty=Sum(
                    Case(
                        When(gender="disi", then=F("quantity")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ),
            )
        )
    }

    for name, payload in animal_other_totals.items():
        qty_display = str(payload["total_qty"])
        male_qty = payload.get("male_qty", 0)
        female_qty = payload.get("female_qty", 0)
        items.append(
            {
                "main": "diger",
                "sub_key": "diger-heyvanlar",
                "title": payload["name"],
                "subtitle": "Heyvanlar (Digər)",
                "quantity": payload["total_qty"],
                "quantity_display": qty_display,
                "male_display": str(male_qty),
                "female_display": str(female_qty),
                "unit": "ədəd",
                "icon": get_animal_icon_by_name(payload["name"]),
                "update_type": "animal_other",
                "update_id": name,
                "input_step": "1",
            }
        )

    farm_totals = {}
    farm_rows = (
        FarmProduct.objects.filter(created_by=user, item__isnull=False)
        .exclude(item__name__iexact="Digər")
        .values(
            "item_id",
            "item__name",
            "item__unit",
            "item__category_id",
            "item__category__name",
            "unit",
        )
        .annotate(total_qty=Sum("quantity"))
    )
    for row in farm_rows:
        item_name = row["item__name"] or ""
        item_unit = row["item__unit"] or row["unit"] or ""
        stock_unit = row["unit"] or ""
        is_forage = _is_forage_item(item_name)
        if is_forage and stock_unit == "bağlama":
            base_unit = "bağlama"
        elif stock_unit in {"kq", "ton", "qram"}:
            base_unit = "kq"
        elif stock_unit in {"litr", "ml"}:
            base_unit = "litr"
        else:
            base_unit = stock_unit

        key = (row["item_id"], stock_unit) if base_unit == "bağlama" else (row["item_id"], "base")
        payload = farm_totals.setdefault(
            key,
            {
                "name": item_name,
                "category_id": row["item__category_id"],
                "category_name": row["item__category__name"] or "",
                "total_qty": Decimal("0"),
                "unit": stock_unit if base_unit == "bağlama" else item_unit,
                "base_unit": base_unit,
            },
        )
        payload["total_qty"] += _convert_farm_qty(
            Decimal(row["total_qty"] or 0), stock_unit, payload["base_unit"]
        )

    farm_items = FarmProductItem.objects.select_related("category").only(
        "id", "name", "unit", "category_id", "category__name"
    ).exclude(name__iexact="Digər")
    for item in farm_items:
        key = (item.id, "base")
        if key not in farm_totals:
            farm_totals[key] = {
                "name": item.name,
                "category_id": item.category_id,
                "category_name": item.category.name if item.category else "",
                "total_qty": Decimal("0"),
                "unit": item.unit,
                "base_unit": item.unit,
            }

    for item_id, payload in farm_totals.items():
        qty_display = f"{payload['total_qty']:.2f}"
        update_id = f"{item_id[0]}||{payload['unit']}" if payload["base_unit"] == "bağlama" else str(item_id[0])
        items.append(
            {
                "main": "teserrufat",
                "sub_key": f"farmcat-{payload['category_id']}",
                "title": payload["name"],
                "subtitle": payload["category_name"],
                "quantity": payload["total_qty"],
                "quantity_display": qty_display,
                "unit": payload["unit"] or "",
                "icon": get_farm_product_icon_by_name(payload["name"]),
                "update_type": "farm_product",
                "update_id": update_id,
                "input_step": "0.01",
            }
        )

    farm_other_totals = {
        f"{(row['manual_name'] or '').strip()}||{row['unit'] or ''}": {
            "name": (row["manual_name"] or "").strip(),
            "unit": row["unit"] or "",
            "total_qty": Decimal(row["total_qty"] or 0),
        }
        for row in (
            FarmProduct.objects.filter(created_by=user)
            .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
            .exclude(manual_name__isnull=True)
            .exclude(manual_name="")
            .exclude(manual_name__iexact="Digər")
            .values("manual_name", "unit")
            .annotate(total_qty=Sum("quantity"))
        )
    }

    for key, payload in farm_other_totals.items():
        qty_display = f"{payload['total_qty']:.2f}"
        sub_key = f"farmcat-{farm_diger_category_id}" if farm_diger_category_id else "farmcat-diger"
        items.append(
            {
                "main": "teserrufat",
                "sub_key": sub_key,
                "title": payload["name"],
                "subtitle": "Təsərrüfat Məhsulları (Digər)",
                "quantity": payload["total_qty"],
                "quantity_display": qty_display,
                "unit": payload["unit"],
                "icon": get_farm_product_icon_by_name(payload["name"]),
                "update_type": "farm_product_other",
                "update_id": key,
                "input_step": "0.01",
            }
        )

    sorted_items = sorted(
        items,
        key=lambda item: (
            1 if Decimal(str(item["quantity"])) == 0 else 0,
            {"toxumlar": 0, "aletler": 1, "heyvanlar": 2, "teserrufat": 3, "diger": 4}.get(item["main"], 9),
            (item.get("subtitle") or "").lower(),
            (item.get("title") or "").lower(),
        ),
    )

    for item in sorted_items:
        item["title"] = _translate_panel_label(item.get("title") or "", lang_code)
        item["subtitle"] = _translate_panel_label(item.get("subtitle") or "", lang_code)

    context = {
        "seed_categories": seed_categories,
        "tool_categories": tool_categories,
        "animal_categories": animal_categories,
        "farm_product_categories": farm_product_categories,
        "items": sorted_items,
    }
    cache.set(cache_key, context, STOCKS_PAGE_CACHE_TTL)
    return render(request, "inventory/stocks.html", context)


@login_required
def update_stock_quantity(request):
    if request.method != "POST":
        return redirect("inventory:stocks")

    update_type = request.POST.get("update_type")
    update_id = request.POST.get("update_id")
    target_raw = request.POST.get("target_quantity")
    cache.delete(f"inventory:stocks-page:v3:user:{request.user.id}")

    if not update_type or not update_id or target_raw is None:
        messages.error(request, _("Məlumatlar natamamdır."))
        return redirect("inventory:stocks")

    try:
        target_value = Decimal(str(target_raw))
    except Exception:
        messages.error(request, _("Miqdar düzgün deyil."))
        return redirect("inventory:stocks")

    note = "Stok səhifəsindən düzəliş"

    if update_type == "seed":
        seed_qs = Seed.objects.filter(created_by=request.user, item_id=update_id)
        current_total = Decimal("0")
        for seed in seed_qs:
            if seed.unit in {"kg", "kq"}:
                current_total += Decimal(seed.quantity)
            elif seed.unit == "ton":
                current_total += Decimal(seed.quantity) * Decimal("1000")
            elif seed.unit == "qram":
                current_total += Decimal(seed.quantity) / Decimal("1000")
            else:
                current_total += Decimal(seed.quantity)

        delta = target_value - current_total
        if delta != 0:
            Seed.objects.create(
                item_id=update_id,
                quantity=delta,
                unit="kg",
                price=0,
                additional_info=note,
                created_by=request.user,
            )
            add_crud_success_message(request, "Seed", "update")
        return redirect("inventory:stocks")

    if update_type == "seed_other":
        seed_qs = Seed.objects.filter(
            created_by=request.user,
            manual_name=update_id,
        ).filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        current_total = Decimal("0")
        for seed in seed_qs:
            if seed.unit in {"kg", "kq"}:
                current_total += Decimal(seed.quantity)
            elif seed.unit == "ton":
                current_total += Decimal(seed.quantity) * Decimal("1000")
            elif seed.unit == "qram":
                current_total += Decimal(seed.quantity) / Decimal("1000")
            else:
                current_total += Decimal(seed.quantity)

        delta = target_value - current_total
        if delta != 0:
            Seed.objects.create(
                item=None,
                manual_name=update_id,
                quantity=delta,
                unit="kg",
                price=0,
                additional_info=note,
                created_by=request.user,
            )
            add_crud_success_message(request, "Seed", "update")
        return redirect("inventory:stocks")

    if update_type == "tool":
        tool_qs = Tool.objects.filter(created_by=request.user, item_id=update_id)
        if target_value % 1 != 0:
            messages.error(request, _("Alətlər üçün miqdar tam ədəd olmalıdır."))
            return redirect("inventory:stocks")
        current_total = sum(int(t.quantity) for t in tool_qs)
        delta = int(target_value) - current_total
        if delta != 0:
            Tool.objects.create(
                item_id=update_id,
                quantity=delta,
                price=0,
                additional_info=note,
                created_by=request.user,
            )
            add_crud_success_message(request, "Tool", "update")
        return redirect("inventory:stocks")

    if update_type == "tool_other":
        tool_qs = Tool.objects.filter(
            created_by=request.user,
            manual_name=update_id,
        ).filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        if target_value % 1 != 0:
            messages.error(request, _("Alətlər üçün miqdar tam ədəd olmalıdır."))
            return redirect("inventory:stocks")
        current_total = sum(int(t.quantity) for t in tool_qs)
        delta = int(target_value) - current_total
        if delta != 0:
            Tool.objects.create(
                item=None,
                manual_name=update_id,
                quantity=delta,
                price=0,
                additional_info=note,
                created_by=request.user,
            )
            add_crud_success_message(request, "Tool", "update")
        return redirect("inventory:stocks")

    if update_type == "farm_product":
        unit_key = None
        if "||" in str(update_id):
            raw_id, unit_key = str(update_id).rsplit("||", 1)
            update_id = raw_id

        product_qs = FarmProduct.objects.filter(created_by=request.user, item_id=update_id)
        current_total = Decimal("0")
        try:
            item = FarmProductItem.objects.get(id=update_id)
        except FarmProductItem.DoesNotExist:
            messages.error(request, _("Məhsul tapılmadı."))
            return redirect("inventory:stocks")

        base_unit = item.unit or "kq"
        if unit_key:
            product_qs = product_qs.filter(unit=unit_key)
            if unit_key == "bağlama":
                base_unit = "bağlama"
        for product in product_qs:
            current_total += _convert_farm_qty(Decimal(product.quantity), product.unit, base_unit)
        unit_value = unit_key or base_unit

        delta = target_value - current_total
        if delta != 0:
            FarmProduct.objects.create(
                item_id=update_id,
                quantity=delta,
                unit=unit_value,
                price=0,
                additional_info=note,
                created_by=request.user,
            )
            add_crud_success_message(request, "FarmProduct", "update")
        return redirect("inventory:stocks")

    if update_type == "farm_product_other":
        if "||" not in update_id:
            messages.error(request, _("Məlumatlar natamamdır."))
            return redirect("inventory:stocks")
        name_key, unit_key = update_id.rsplit("||", 1)
        product_qs = FarmProduct.objects.filter(
            created_by=request.user,
        ).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=name_key,
            unit=unit_key,
        )
        current_total = Decimal("0")
        for product in product_qs:
            current_total += Decimal(product.quantity)

        delta = target_value - current_total
        if delta != 0:
            FarmProduct.objects.create(
                item=None,
                manual_name=name_key,
                quantity=delta,
                unit=unit_key,
                price=0,
                additional_info=note,
                created_by=request.user,
            )
            add_crud_success_message(request, "FarmProduct", "update")
        return redirect("inventory:stocks")

    if update_type in {"animal_sub", "animal_other"}:
        male_raw = request.POST.get("male_target")
        female_raw = request.POST.get("female_target")
        if male_raw is None or female_raw is None:
            messages.error(request, _("Məlumatlar natamamdır."))
            return redirect("inventory:stocks")

        try:
            male_target = int(male_raw)
            female_target = int(female_raw)
        except Exception:
            messages.error(request, _("Heyvanlar üçün miqdar tam ədəd olmalıdır."))
            return redirect("inventory:stocks")

        if update_type == "animal_sub":
            animals_qs = Animal.objects.filter(
                created_by=request.user,
                subcategory_id=update_id,
            ).exclude(quantity=0)
        else:
            animals_qs = Animal.objects.filter(
                created_by=request.user,
                manual_name=update_id,
            ).exclude(quantity=0).filter(Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər"))

        current_male = sum(int(getattr(a, "quantity", 1) or 1) for a in animals_qs.filter(gender="erkek"))
        current_female = sum(int(getattr(a, "quantity", 1) or 1) for a in animals_qs.filter(gender="disi"))

        male_delta = male_target - current_male
        female_delta = female_target - current_female

        def create_animals(count, gender_value):
            if count <= 0:
                return
            payload = {
                "gender": gender_value,
                "additional_info": note,
                "created_by": request.user,
                "quantity": count,
            }
            if update_type == "animal_sub":
                payload["subcategory_id"] = update_id
            else:
                payload["subcategory"] = None
                payload["manual_name"] = update_id
            Animal.objects.create(**payload)

        def disable_animals(count, gender_value):
            if count <= 0:
                return
            remaining = count
            for animal in animals_qs.filter(gender=gender_value).order_by("-created_at"):
                qty_val = int(getattr(animal, "quantity", 1) or 1)
                if qty_val <= remaining:
                    remaining -= qty_val
                    animal.quantity = 0
                    animal.additional_info = note
                    animal.save(update_fields=["quantity", "additional_info"])
                else:
                    animal.quantity = qty_val - remaining
                    animal.additional_info = note
                    animal.save(update_fields=["quantity", "additional_info"])
                    remaining = 0
                if remaining <= 0:
                    break

        if male_delta > 0:
            create_animals(male_delta, "erkek")
        elif male_delta < 0:
            disable_animals(abs(male_delta), "erkek")

        if female_delta > 0:
            create_animals(female_delta, "disi")
        elif female_delta < 0:
            disable_animals(abs(female_delta), "disi")

        if male_delta != 0 or female_delta != 0:
            add_crud_success_message(request, "Animal", "update")
        return redirect("inventory:stocks")

    messages.error(request, _("Bu kateqoriya üçün yeniləmə dəstəklənmir."))
    return redirect("inventory:stocks")


@login_required
def add_product(request):
    context = _build_add_page_context(request)
    mode = (request.GET.get("mode") or "").strip().lower()
    context["combined_mode"] = mode == "combined"
    return render(request, "inventory/add_product.html", context)


@login_required
def add_product_list_panel(request):
    form_type = (request.GET.get("form") or "").strip().lower()
    lang_code = (getattr(request, "LANGUAGE_CODE", "") or get_language() or "az").split("-")[0]
    try:
        context = _build_add_page_list_panel_context(request.user, form_type, include_time=True, lang_code=lang_code)
    except (OperationalError, ProgrammingError) as exc:
        if "time" not in str(exc).lower():
            raise
        context = _build_add_page_list_panel_context(request.user, form_type, include_time=False, lang_code=lang_code)
    return render(request, "inventory/partials/add_product_list_panel.html", context)


@login_required
def barcode_builder(request):
    return render(request, "inventory/barcode_builder.html", _build_add_page_context(request))


@login_required
def lookup_scan_code(request):
    code = request.GET.get("code", "").strip()

    if not code:
        return JsonResponse({"success": False, "message": "Kod göndərilməyib."}, status=400)

    barcode = UserBarcode.objects.filter(code=code).first()
    if barcode:
        return JsonResponse(
            {
                "success": True,
                "source": "user_barcode",
                "item": {
                    "code": barcode.code,
                    "label": barcode.label,
                    "form_type": barcode.form_type,
                    "target_type": barcode.target_type,
                    "metadata": barcode.metadata,
                },
            }
        )

    try:
        item = ScanItem.objects.get(code=code, is_active=True)
    except ScanItem.DoesNotExist:
        return JsonResponse({"success": False, "message": "Kod tapılmadı."}, status=404)

    category_to_form_type = {
        "toxumlar": "seed",
        "aletler": "tool",
        "heyvanlar": "animal",
        "teserrufat": "farm",
        "xercler": "expense",
        "diger": "income",
    }
    return JsonResponse({
        "success": True,
        "source": "scan_item",
        "item": {
            "code": item.code,
            "label": item.name,
            "name": item.name,
            "category": item.category,
            "form_type": category_to_form_type.get(item.category, "income"),
            "target_type": "manual",
            "unit": item.unit or "",
            "default_price": str(item.default_price),
            "metadata": {
                "manual_name": item.name,
                "category": item.category,
                "unit": item.unit or "",
            },
        }
    })


@login_required
@require_POST
def transcribe_voice_input(request):
    audio_file = request.FILES.get("audio")

    if not audio_file:
        return JsonResponse({"success": False, "message": "Audio göndərilməyib."}, status=400)

    temp_path = None
    try:
        suffix = os.path.splitext(audio_file.name or "")[1] or ".webm"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            for chunk in audio_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name

        lang = _resolve_voice_language(request, request.POST.get("language"))
        if lang not in {"az", "en", "ru"}:
            lang = None

        model = _get_whisper_model()
        segments, info = model.transcribe(temp_path, language=lang, beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()

        if not text:
            return JsonResponse({"success": False, "message": "Səs tanınmadı"}, status=422)

        return JsonResponse({
            "success": True,
            "transcript": text,
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e),
        }, status=500)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@login_required
@require_POST
def get_or_create_barcode(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "message": "Sorğu formatı yanlışdır."}, status=400)

    form_type = _normalized_text(payload.get("form_type"))
    target_type = _normalized_text(payload.get("target_type"))
    label = _normalized_text(payload.get("label"))
    metadata = payload.get("metadata") or {}

    if form_type not in dict(UserBarcode.FORM_TYPE_CHOICES):
        return JsonResponse({"success": False, "message": "Form tipi yanlışdır."}, status=400)
    if target_type not in dict(UserBarcode.TARGET_TYPE_CHOICES):
        return JsonResponse({"success": False, "message": "Barkod tipi yanlışdır."}, status=400)
    if not label:
        return JsonResponse({"success": False, "message": "Barkod üçün info seçin."}, status=400)

    barcode = _build_user_barcode(form_type, target_type, label, metadata)
    return JsonResponse(
        {
            "success": True,
            "barcode": {
                "code": barcode.code,
                "label": barcode.label,
                "form_type": barcode.form_type,
                "target_type": barcode.target_type,
                "metadata": barcode.metadata,
            },
        }
    )

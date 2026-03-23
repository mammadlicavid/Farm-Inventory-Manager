from __future__ import annotations

from datetime import timedelta, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from common.formatting import format_currency
from common.category_order import ensure_diger_last
from common.text import normalize_manual_label
from common.icons import (
    get_animal_icon_by_name,
    get_farm_product_icon_by_name,
    get_seed_icon_by_name,
)
from farm_products.models import FarmProduct, FarmProductItem
from seeds.models import Seed, SeedItem
from animals.models import Animal, AnimalSubCategory
from tools.models import Tool

from .models import Income

FARM_PRODUCT_CATEGORIES: List[Tuple[str, List[str]]] = [
    (
        "Süd və Süd Məhsulları",
        [
            "İnək südü",
            "Camış südü",
            "Keçi südü",
            "İnək pendiri",
            "Camış pendiri",
            "Keçi pendiri",
            "Qatıq",
            "Ayran",
            "Kərə yağı",
            "Qaymaq",
            "Digər",
        ],
    ),
    (
        "Yumurta",
        [
            "Toyuq yumurtası",
            "Hinduşka yumurtası",
            "Qaz yumurtası",
            "Ördək yumurtası",
            "Bildircin yumurtası",
            "Digər",
        ],
    ),
    (
        "Ət Məhsulları",
        [
            "Mal əti",
            "Dana əti",
            "Camış əti",
            "Qoyun əti",
            "Keçi əti",
            "Toyuq əti",
            "Hinduşka əti",
            "Qaz əti",
            "Ördək əti",
            "Bildircin əti",
            "Digər",
        ],
    ),
    (
        "Meyvə",
        [
            "Alma",
            "Armud",
            "Şaftalı",
            "Ərik",
            "Albalı",
            "Gilas",
            "Nar",
            "Üzüm",
            "Gavalı",
            "Heyva",
            "Digər",
        ],
    ),
    (
        "Tərəvəz",
        [
            "Pomidor",
            "Xiyar",
            "Bibər",
            "Badımcan",
            "Kahı",
            "İspanaq",
            "Soğan",
            "Sarımsaq",
            "Kartof",
            "Digər",
        ],
    ),
    (
        "Göyərti",
        [
            "Keşniş",
            "Şüyüt",
            "Cəfəri",
            "Yaşıl soğan",
            "Reyhan",
            "Tərxun",
            "Digər",
        ],
    ),
    (
        "Taxıl Məhsulları",
        [
            "Buğda",
            "Arpa",
            "Çovdar",
            "Vələmir",
            "Qarğıdalı",
            "Çəltik",
            "Digər",
        ],
    ),
    (
        "Yem Bitkiləri",
        [
            "Yonca",
            "Koronilla",
            "Seradella",
            "Digər",
        ],
    ),
    (
        "Bostan Məhsulları",
        [
            "Qarpız",
            "Yemiş",
            "Boranı",
            "Digər",
        ],
    ),
    (
        "Bal və Arıçılıq",
        [
            "Bal",
            "Arı mumu",
            "Arı südü",
            "Digər",
        ],
    ),
    (
        "Gübrələr",
        [
            "Mal peyini",
            "Qoyun peyini",
            "Keçi peyini",
            "Quş peyini",
            "Kompost",
            "Mineral gübrə",
            "Digər",
        ],
    ),
]

ANIMAL_CATEGORY = (
    "Heyvanlar",
    [
        "İnək",
        "Dana",
        "Camış",
        "Qoyun",
        "Keçi",
        "Toyuq",
        "Hinduşka",
        "Qaz",
        "Ördək",
        "Bildircin",
        "At",
        "Eşşək",
        "Qatır",
        "Digər",
    ],
)

SEED_CATEGORIES: List[Tuple[str, List[str]]] = [
    (
        "Taxıl və Paxlalı Toxumları",
        [
            "Buğda toxumu",
            "Arpa toxumu",
            "Çovdar toxumu",
            "Vələmir toxumu",
            "Qarğıdalı toxumu",
            "Çəltik toxumu",
            "Lobya toxumu",
            "Noxud toxumu",
            "Mərcimək toxumu",
            "Digər",
        ],
    ),
    (
        "Yem və Yağlı Bitki Toxumları",
        [
            "Yonca toxumu",
            "Koronilla toxumu",
            "Seradella toxumu",
            "Günəbaxan toxumu",
            "Pambıq toxumu",
            "Soya toxumu",
            "Şəkər çuğunduru toxumu",
            "Digər",
        ],
    ),
    (
        "Tərəvəz və Bostan Toxumları",
        [
            "Pomidor toxumu",
            "Xiyar toxumu",
            "Bibər toxumu",
            "Badımcan toxumu",
            "Kahı toxumu",
            "İspanaq toxumu",
            "Qarpız toxumu",
            "Yemiş toxumu",
            "Boranı toxumu",
            "Digər",
        ],
    ),
    (
        "Meyvə Toxumları",
        [
            "Alma toxumu",
            "Armud toxumu",
            "Şaftalı toxumu",
            "Ərik toxumu",
            "Albalı toxumu",
            "Gilas toxumu",
            "Nar toxumu",
            "Üzüm toxumu",
            "Gavalı toxumu",
            "Heyva toxumu",
            "Digər",
        ],
    ),
]

OTHER_CATEGORY = ("Digər", ["Digər"])

FORAGE_ITEMS = {"yonca", "koronilla", "seradella"}


def _sorted_items(items: List[str]) -> List[str]:
    return ensure_diger_last(items)


def _category_type_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for name, _ in FARM_PRODUCT_CATEGORIES:
        mapping[name] = "farm"
    mapping[ANIMAL_CATEGORY[0]] = "animal"
    for name, _ in SEED_CATEGORIES:
        mapping[name] = "seed"
    mapping[OTHER_CATEGORY[0]] = "other"
    return mapping


def _farm_unit_lookup() -> Dict[str, str | None]:
    lookup: Dict[str, str | None] = {}
    for item in FarmProductItem.objects.select_related("category").all():
        key = (item.name or "").strip().lower()
        if key and key not in lookup:
            lookup[key] = item.unit
    return lookup


def _allowed_units_for_farm(item_name: str, unit_lookup: Dict[str, str | None]) -> List[str]:
    key = (item_name or "").strip().lower()
    if not key:
        return ["kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"]

    if key in FORAGE_ITEMS:
        return ["kq", "bağlama"]

    base_unit = unit_lookup.get(key)
    if not base_unit:
        return ["kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"]

    if base_unit == "kq":
        return ["kq", "ton", "qram"]
    if base_unit == "litr":
        return ["litr", "ml"]

    return [base_unit]


def _build_category_payload() -> Tuple[List[str], Dict[str, dict]]:
    categories: List[str] = []
    payload: Dict[str, dict] = {}

    unit_lookup = _farm_unit_lookup()
    type_map = _category_type_map()

    def add_category(name: str, items: List[str]):
        categories.append(name)
        sorted_items = _sorted_items(items)
        ctype = type_map.get(name, "other")
        item_rows = []
        for item in sorted_items:
            unit = None
            if ctype == "farm":
                unit = unit_lookup.get(item.strip().lower())
            elif ctype == "animal":
                unit = "ədəd"
            elif ctype == "seed":
                unit = "kq"
            item_rows.append({"name": item, "unit": unit})
        payload[name] = {"type": ctype, "items": item_rows}

    for name, items in FARM_PRODUCT_CATEGORIES:
        add_category(name, items)
    add_category(ANIMAL_CATEGORY[0], ANIMAL_CATEGORY[1])
    for name, items in SEED_CATEGORIES:
        add_category(name, items)
    add_category(OTHER_CATEGORY[0], OTHER_CATEGORY[1])

    return categories, payload


def _get_income_icon(category: str, item_name: str) -> str:
    ctype = _category_type_map().get(category, "other")
    if ctype == "animal":
        return get_animal_icon_by_name(item_name)
    if ctype == "seed":
        return get_seed_icon_by_name(item_name)
    return get_farm_product_icon_by_name(item_name)


def _parse_date(value: str | None) -> date:
    if not value:
        return timezone.now().date()
    try:
        return date.fromisoformat(value)
    except Exception:
        return timezone.now().date()


def _category_type(category: str) -> str:
    return _category_type_map().get(category, "other")


def _parse_positive_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _seed_unit_for_income(unit: str) -> str:
    return "kg" if unit == "kq" else unit


def _append_note(existing: str | None, note: str) -> str:
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing} • {note}"


def _delete_income_animals(user, income_id: int) -> None:
    tag = f"income:{income_id}"
    Animal.objects.filter(created_by=user, additional_info__icontains=tag).delete()


def _get_animal_by_id(user, identification_no: str | None) -> Animal | None:
    if not identification_no:
        return None
    return Animal.objects.filter(created_by=user, identification_no=identification_no).first()


def _seed_to_kg(quantity: Decimal, unit: str) -> Decimal:
    if unit == "ton":
        return quantity * Decimal("1000")
    if unit == "qram":
        return quantity / Decimal("1000")
    return quantity


def _farm_to_base(quantity: Decimal, unit: str, base_unit: str) -> Decimal:
    if base_unit == "kq":
        if unit == "ton":
            return quantity * Decimal("1000")
        if unit == "qram":
            return quantity / Decimal("1000")
        return quantity
    if base_unit == "litr":
        if unit == "ml":
            return quantity / Decimal("1000")
        return quantity
    return quantity


def _farm_base_unit(unit: str) -> str:
    if unit in {"kq", "ton", "qram"}:
        return "kq"
    if unit in {"litr", "ml"}:
        return "litr"
    return unit


def _seed_stock_kg(user, item_name: str) -> Decimal:
    item = SeedItem.objects.filter(name=item_name).first()
    if item:
        qs = Seed.objects.filter(created_by=user, item=item)
    else:
        qs = Seed.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=item_name,
        )
    total = Decimal("0")
    for seed in qs:
        total += _seed_to_kg(Decimal(seed.quantity), seed.unit)
    return total


def _farm_stock_base(user, item_name: str, base_unit: str) -> Decimal:
    item = FarmProductItem.objects.filter(name=item_name).first()
    if item:
        qs = FarmProduct.objects.filter(created_by=user, item=item)
    else:
        qs = FarmProduct.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=item_name,
        )
    total = Decimal("0")
    for product in qs:
        if base_unit == "bağlama":
            if product.unit != "bağlama":
                continue
            total += Decimal(product.quantity)
        elif base_unit == "kq":
            if product.unit not in {"kq", "ton", "qram"}:
                continue
            total += _farm_to_base(Decimal(product.quantity), product.unit, "kq")
        elif base_unit == "litr":
            if product.unit not in {"litr", "ml"}:
                continue
            total += _farm_to_base(Decimal(product.quantity), product.unit, "litr")
        else:
            if product.unit != base_unit:
                continue
            total += Decimal(product.quantity)
    return total


def _adjust_seed_stock(user, item_name: str, quantity: Decimal, unit: str, note: str, price: Decimal | None = None):
    if quantity == 0:
        return None
    item = SeedItem.objects.filter(name=item_name).first()
    qty = Decimal(str(quantity))
    price_value = price if price is not None else 0
    return Seed.objects.create(
        item=item,
        manual_name=None if item else item_name,
        quantity=qty,
        unit=_seed_unit_for_income(unit),
        price=price_value,
        additional_info=note,
        created_by=user,
    )


def _adjust_farm_stock(user, item_name: str, quantity: Decimal, unit: str, note: str, price: Decimal | None = None):
    if quantity == 0:
        return None
    item = FarmProductItem.objects.filter(name=item_name).first()
    qty = Decimal(str(quantity))
    price_value = price if price is not None else 0
    return FarmProduct.objects.create(
        item=item,
        manual_name=None if item else item_name,
        quantity=qty,
        unit=unit,
        price=price_value,
        additional_info=note,
        created_by=user,
    )


def _adjust_other_stock(user, item_name: str, quantity: Decimal, unit: str, note: str, price: Decimal | None = None, gender: str | None = None):
    normalized_name = (item_name or "").strip()
    if not normalized_name or quantity == 0:
        return None

    if unit in {"kq", "ton", "qram"} and Seed.objects.filter(created_by=user).filter(
        Q(item__isnull=True) | Q(item__name__iexact="Digər"),
        manual_name__iexact=normalized_name,
    ).exists():
        return _adjust_seed_stock(user, normalized_name, quantity, unit, note, price)

    if FarmProduct.objects.filter(created_by=user).filter(
        Q(item__isnull=True) | Q(item__name__iexact="Digər"),
        manual_name__iexact=normalized_name,
        unit=unit,
    ).exists():
        return _adjust_farm_stock(user, normalized_name, quantity, unit, note, price)

    if unit == "ədəd" and Tool.objects.filter(created_by=user).filter(
        Q(item__isnull=True) | Q(item__name__iexact="Digər"),
        manual_name__iexact=normalized_name,
    ).exists():
        return Tool.objects.create(
            item=None,
            manual_name=normalized_name,
            quantity=int(quantity),
            price=price if price is not None else 0,
            additional_info=note,
            created_by=user,
        )

    if unit == "ədəd" and gender and Animal.objects.filter(created_by=user, gender=gender).filter(
        Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər"),
        manual_name__iexact=normalized_name,
    ).exists():
        return Animal.objects.create(
            subcategory=None,
            manual_name=normalized_name,
            gender=gender,
            quantity=int(quantity),
            price=price if price is not None else 0,
            additional_info=note,
            created_by=user,
        )

    return FarmProduct.objects.create(
        item=None,
        manual_name=normalized_name,
        quantity=Decimal(str(quantity)),
        unit=unit,
        price=price if price is not None else 0,
        additional_info=note,
        created_by=user,
    )


def _decrease_animal_stock(user, item_name: str, gender: str, quantity: int, note: str) -> bool:
    if quantity <= 0:
        return True
    subcat = AnimalSubCategory.objects.filter(name=item_name).first()
    if subcat:
        animals_qs = Animal.objects.filter(
            created_by=user,
            subcategory=subcat,
            gender=gender,
            quantity__gt=0,
        )
    else:
        animals_qs = Animal.objects.filter(
            created_by=user,
            gender=gender,
            quantity__gt=0,
        ).filter(
            (Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər")),
            manual_name=item_name,
        )

    available = sum(int(getattr(a, "quantity", 1) or 1) for a in animals_qs)
    if available < quantity:
        return False

    remaining = quantity
    for animal in animals_qs.order_by("-created_at"):
        qty_val = int(getattr(animal, "quantity", 1) or 1)
        if qty_val <= remaining:
            remaining -= qty_val
            animal.quantity = 0
            animal.additional_info = _append_note(animal.additional_info, note)
            animal.save(update_fields=["quantity", "additional_info"])
        else:
            animal.quantity = qty_val - remaining
            animal.additional_info = _append_note(animal.additional_info, note)
            animal.save(update_fields=["quantity", "additional_info"])
            remaining = 0
        if remaining <= 0:
            break
    return True


def _increase_animal_stock(user, item_name: str, gender: str, quantity: int, note: str) -> Animal | None:
    if quantity <= 0:
        return None
    subcat = AnimalSubCategory.objects.filter(name=item_name).first()
    payload = {
        "gender": gender,
        "additional_info": note,
        "created_by": user,
        "quantity": quantity,
    }
    if subcat:
        payload["subcategory"] = subcat
    else:
        payload["subcategory"] = None
        payload["manual_name"] = item_name
    return Animal.objects.create(**payload)


def _animal_available_count(user, item_name: str, gender: str) -> int:
    subcat = AnimalSubCategory.objects.filter(name=item_name).first()
    if subcat:
        qs = Animal.objects.filter(
            created_by=user,
            subcategory=subcat,
            gender=gender,
            quantity__gt=0,
        )
    else:
        qs = Animal.objects.filter(
            created_by=user,
            gender=gender,
            quantity__gt=0,
        ).filter(
            (Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər")),
            manual_name=item_name,
        )
    return sum(int(getattr(a, "quantity", 1) or 1) for a in qs)


@login_required
def income_list(request):
    query = (request.GET.get("q") or "").strip()
    incomes_qs = Income.objects.filter(created_by=request.user)

    if query:
        incomes_qs = incomes_qs.filter(
            Q(item_name__icontains=query)
            | Q(category__icontains=query)
            | Q(additional_info__icontains=query)
        )

    total_amount = incomes_qs.aggregate(total=Sum("amount"))["total"] or 0
    last_week = timezone.now().date() - timedelta(days=7)
    weekly_total = incomes_qs.filter(date__gte=last_week).aggregate(total=Sum("amount"))["total"] or 0

    incomes = list(incomes_qs)
    for income in incomes:
        income.icon_class = _get_income_icon(income.category, income.item_name)
        income.amount_display = format_currency(income.amount, 2)

    categories, category_data = _build_category_payload()

    context = {
        "incomes": incomes,
        "total_amount": total_amount,
        "total_amount_display": format_currency(total_amount, 2),
        "weekly_total": weekly_total,
        "weekly_total_display": format_currency(weekly_total, 2),
        "categories": categories,
        "category_data": category_data,
        "today": timezone.now().date(),
        "yesterday": timezone.now().date() - timedelta(days=1),
    }
    return render(request, "incomes/income_list.html", context)


@login_required
def add_income(request):
    if request.method != "POST":
        return redirect("incomes:income_list")

    category = (request.POST.get("category") or "").strip()
    item_name = (request.POST.get("item_name") or "").strip()
    manual_name = normalize_manual_label(request.POST.get("manual_name"))
    quantity_raw = request.POST.get("quantity")
    unit = (request.POST.get("unit") or "").strip()
    amount = request.POST.get("amount")
    gender = (request.POST.get("gender") or "").strip()
    identification_no = (request.POST.get("identification_no") or "").strip()
    additional_info = request.POST.get("additional_info")
    date_value = _parse_date(request.POST.get("date"))

    if not category or not quantity_raw or not unit or not amount:
        messages.error(request, "Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")
        return redirect("incomes:income_list")

    quantity = _parse_positive_decimal(quantity_raw)
    if quantity is None:
        messages.error(request, "Miqdar düzgün deyil.")
        return redirect("incomes:income_list")

    amount_val = _parse_positive_decimal(amount)
    if amount_val is None:
        messages.error(request, "Məbləğ düzgün deyil.")
        return redirect("incomes:income_list")

    ctype = _category_type(category)

    if category.lower() == "digər" or item_name.lower() == "digər" or not item_name:
        if not manual_name:
            messages.error(request, "Zəhmət olmasa, Digər üçün ad daxil edin.")
            return redirect("incomes:income_list")
        item_name = manual_name

    if ctype == "animal" and not gender:
        messages.error(request, "Zəhmət olmasa, heyvanlar üçün cinsiyyət seçin.")
        return redirect("incomes:income_list")

    if ctype == "animal":
        try:
            qty_int = int(quantity)
        except (TypeError, ValueError):
            qty_int = 0
        if Decimal(qty_int) != quantity:
            messages.error(request, "Heyvanlar üçün miqdar tam ədəd olmalıdır.")
            return redirect("incomes:income_list")
        if identification_no and abs(qty_int) != 1:
            messages.error(request, "İdentifikasiya nömrəsi yalnız miqdar ±1 olduqda verilə bilər.")
            return redirect("incomes:income_list")

    unit_lookup = _farm_unit_lookup()
    if ctype == "animal":
        allowed_units = ["ədəd"]
    elif ctype == "seed":
        allowed_units = ["kq", "ton", "qram"]
    elif ctype == "farm":
        allowed_units = _allowed_units_for_farm(item_name, unit_lookup)
    else:
        allowed_units = ["kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"]

    if unit not in allowed_units:
        messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
        return redirect("incomes:income_list")

    # Stock availability check (no negatives)
    if ctype == "seed":
        available_kg = _seed_stock_kg(request.user, item_name)
        needed_kg = _seed_to_kg(quantity, unit)
        if available_kg < needed_kg:
            messages.error(request, "Stokda kifayət qədər toxum yoxdur.")
            return redirect("incomes:income_list")
    elif ctype == "farm":
        base_unit = _farm_base_unit(unit)
        available_base = _farm_stock_base(request.user, item_name, base_unit)
        needed_base = _farm_to_base(quantity, unit, base_unit)
        if available_base < needed_base:
            messages.error(request, "Stokda kifayət qədər məhsul yoxdur.")
            return redirect("incomes:income_list")
    income = Income.objects.create(
        category=category,
        item_name=item_name,
        quantity=quantity,
        unit=unit,
        amount=amount_val,
        gender=gender if ctype == "animal" else None,
        additional_info=additional_info,
        date=date_value,
        created_by=request.user,
    )

    note = "Gəlir satışı"
    if ctype == "seed":
        stock_item = _adjust_seed_stock(request.user, item_name, -abs(quantity), unit, note, amount_val)
        if stock_item:
            income.content_object = stock_item
            income.save(update_fields=["content_type", "object_id"])
    elif ctype == "farm":
        stock_item = _adjust_farm_stock(request.user, item_name, -abs(quantity), unit, note, amount_val)
        if stock_item:
            income.content_object = stock_item
            income.save(update_fields=["content_type", "object_id"])
    elif ctype == "animal":
        qty_int = int(quantity)
        target_animal = _get_animal_by_id(request.user, identification_no)
        if identification_no:
            if not target_animal:
                messages.error(request, "Bu identifikasiya nömrəsinə uyğun heyvan tapılmadı.")
                income.delete()
                return redirect("incomes:income_list")
            if target_animal.subcategory:
                if target_animal.subcategory.name != item_name:
                    messages.error(request, "Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
                    income.delete()
                    return redirect("incomes:income_list")
            else:
                if (target_animal.manual_name or "").strip() != item_name:
                    messages.error(request, "Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
                    income.delete()
                    return redirect("incomes:income_list")
            subcat = target_animal.subcategory
        else:
            subcat = AnimalSubCategory.objects.filter(name=item_name).first()

        income_tag = f"income:{income.id}"
        display_animal = Animal.objects.create(
            subcategory=subcat,
            manual_name=None if subcat else item_name,
            gender=gender,
            quantity=-abs(qty_int),
            price=amount_val,
            additional_info=f"Gəlir satışı | {income_tag}",
            created_by=request.user,
        )
        if identification_no:
            target_animal.delete()
        income.content_object = display_animal
        income.save(update_fields=["content_type", "object_id"])
    elif category.lower() == "digər" or (request.POST.get("item_name") or "").strip().lower() == "digər":
        stock_item = _adjust_other_stock(request.user, item_name, -abs(quantity), unit, note, amount_val, gender or None)
        if stock_item:
            income.content_object = stock_item
            income.save(update_fields=["content_type", "object_id"])

    messages.success(request, "Gəlir əlavə edildi.")
    return redirect("incomes:income_list")


@login_required
def edit_income(request, pk: int):
    income = get_object_or_404(Income, pk=pk, created_by=request.user)

    if request.method == "POST":
        prev_category = income.category
        prev_item = income.item_name
        prev_quantity = Decimal(str(income.quantity))
        prev_unit = income.unit
        prev_gender = income.gender or ""
        prev_amount = Decimal(str(income.amount))

        category = (request.POST.get("category") or "").strip()
        item_name = (request.POST.get("item_name") or "").strip()
        manual_name = normalize_manual_label(request.POST.get("manual_name"))
        quantity_raw = request.POST.get("quantity")
        unit = (request.POST.get("unit") or "").strip()
        amount = request.POST.get("amount")
        gender = (request.POST.get("gender") or "").strip()
        identification_no = (request.POST.get("identification_no") or "").strip()
        additional_info = request.POST.get("additional_info")
        date_value = _parse_date(request.POST.get("date"))

        if not category or not quantity_raw or not unit or not amount:
            messages.error(request, "Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")
            return redirect("incomes:edit_income", pk=income.pk)

        quantity = _parse_positive_decimal(quantity_raw)
        if quantity is None:
            messages.error(request, "Miqdar düzgün deyil.")
            return redirect("incomes:edit_income", pk=income.pk)

        amount_val = _parse_positive_decimal(amount)
        if amount_val is None:
            messages.error(request, "Məbləğ düzgün deyil.")
            return redirect("incomes:edit_income", pk=income.pk)

        ctype = _category_type(category)

        if category.lower() == "digər" or item_name.lower() == "digər" or not item_name:
            if not manual_name:
                messages.error(request, "Zəhmət olmasa, Digər üçün ad daxil edin.")
                return redirect("incomes:edit_income", pk=income.pk)
            item_name = manual_name

        if ctype == "animal" and not gender:
            messages.error(request, "Zəhmət olmasa, heyvanlar üçün cinsiyyət seçin.")
            return redirect("incomes:edit_income", pk=income.pk)

        if ctype == "animal":
            try:
                qty_int = int(quantity)
            except (TypeError, ValueError):
                qty_int = 0
            if Decimal(qty_int) != quantity:
                messages.error(request, "Heyvanlar üçün miqdar tam ədəd olmalıdır.")
                return redirect("incomes:edit_income", pk=income.pk)
            if identification_no and abs(qty_int) != 1:
                messages.error(request, "İdentifikasiya nömrəsi yalnız miqdar ±1 olduqda verilə bilər.")
                return redirect("incomes:edit_income", pk=income.pk)

        unit_lookup = _farm_unit_lookup()
        if ctype == "animal":
            allowed_units = ["ədəd"]
        elif ctype == "seed":
            allowed_units = ["kq", "ton", "qram"]
        elif ctype == "farm":
            allowed_units = _allowed_units_for_farm(item_name, unit_lookup)
        else:
            allowed_units = ["kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"]

        if unit not in allowed_units:
            messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
            return redirect("incomes:edit_income", pk=income.pk)

        # Stock availability check with rollback of previous income
        prev_type = _category_type(prev_category)
        new_type = ctype
        if new_type == "seed":
            available_kg = _seed_stock_kg(request.user, item_name)
            if prev_type == "seed" and prev_item == item_name:
                available_kg += _seed_to_kg(prev_quantity, prev_unit)
            needed_kg = _seed_to_kg(quantity, unit)
            if available_kg < needed_kg:
                messages.error(request, "Stokda kifayət qədər toxum yoxdur.")
                return redirect("incomes:edit_income", pk=income.pk)
        elif new_type == "farm":
            base_unit = _farm_base_unit(unit)
            available_base = _farm_stock_base(request.user, item_name, base_unit)
            if prev_type == "farm" and prev_item == item_name and _farm_base_unit(prev_unit) == base_unit:
                available_base += _farm_to_base(prev_quantity, prev_unit, base_unit)
            needed_base = _farm_to_base(quantity, unit, base_unit)
            if available_base < needed_base:
                messages.error(request, "Stokda kifayət qədər məhsul yoxdur.")
                return redirect("incomes:edit_income", pk=income.pk)
        income.category = category
        income.item_name = item_name
        income.quantity = quantity
        income.unit = unit
        income.amount = amount_val
        income.gender = gender if ctype == "animal" else None
        income.additional_info = additional_info
        income.date = date_value
        income.save()

        prev_type = _category_type(prev_category)
        new_type = ctype
        note = "Gəlir düzəlişi"
        if prev_type == "seed":
            _adjust_seed_stock(request.user, prev_item, abs(prev_quantity), prev_unit, note, prev_amount)
        elif prev_type == "farm":
            _adjust_farm_stock(request.user, prev_item, abs(prev_quantity), prev_unit, note, prev_amount)
        elif prev_type == "animal":
            _delete_income_animals(request.user, income.id)

        if new_type == "seed":
            stock_item = _adjust_seed_stock(request.user, item_name, -abs(quantity), unit, note, amount_val)
            if stock_item:
                income.content_object = stock_item
                income.save(update_fields=["content_type", "object_id"])
        elif new_type == "farm":
            stock_item = _adjust_farm_stock(request.user, item_name, -abs(quantity), unit, note, amount_val)
            if stock_item:
                income.content_object = stock_item
                income.save(update_fields=["content_type", "object_id"])
        elif new_type == "animal":
            qty_int = int(quantity)
            target_animal = _get_animal_by_id(request.user, identification_no)
            if identification_no:
                if not target_animal:
                    messages.error(request, "Bu identifikasiya nömrəsinə uyğun heyvan tapılmadı.")
                    return redirect("incomes:edit_income", pk=income.pk)
                if target_animal.subcategory:
                    if target_animal.subcategory.name != item_name:
                        messages.error(request, "Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
                        return redirect("incomes:edit_income", pk=income.pk)
                else:
                    if (target_animal.manual_name or "").strip() != item_name:
                        messages.error(request, "Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
                        return redirect("incomes:edit_income", pk=income.pk)
                subcat = target_animal.subcategory
            else:
                subcat = AnimalSubCategory.objects.filter(name=item_name).first()

            income_tag = f"income:{income.id}"
            display_animal = Animal.objects.create(
                subcategory=subcat,
                manual_name=None if subcat else item_name,
                gender=gender,
                quantity=-abs(qty_int),
                price=amount_val,
                additional_info=f"Gəlir satışı | {income_tag}",
                created_by=request.user,
            )
            if identification_no:
                target_animal.delete()
            income.content_object = display_animal
            income.save(update_fields=["content_type", "object_id"])
        else:
            if income.content_object:
                income.content_object = None
                income.save(update_fields=["content_type", "object_id"])

        messages.success(request, "Gəlir yeniləndi.")
        return redirect("incomes:income_list")

    categories, category_data = _build_category_payload()
    context = {
        "income": income,
        "categories": categories,
        "category_data": category_data,
    }
    return render(request, "incomes/income_form.html", context)


@login_required
def delete_income(request, pk: int):
    income = get_object_or_404(Income, pk=pk, created_by=request.user)
    if request.method == "POST":
        note = "Gəlir silindi"
        ctype = _category_type(income.category)
        if ctype == "seed":
            _adjust_seed_stock(request.user, income.item_name, abs(Decimal(str(income.quantity))), income.unit, note, Decimal(str(income.amount)))
        elif ctype == "farm":
            _adjust_farm_stock(request.user, income.item_name, abs(Decimal(str(income.quantity))), income.unit, note, Decimal(str(income.amount)))
        elif ctype == "animal":
            _delete_income_animals(request.user, income.id)
        income.delete()
        messages.success(request, "Gəlir silindi.")
    return redirect("incomes:income_list")

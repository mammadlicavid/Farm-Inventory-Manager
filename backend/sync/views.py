import json
import traceback
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from animals.models import Animal, AnimalSubCategory
from expenses.models import Expense, ExpenseCategory, ExpenseSubCategory
from farm_products.models import FarmProduct, FarmProductItem
from incomes.models import Income
from seeds.models import Seed, SeedItem
from suppliers.models import Supplier
from tools.models import Tool, ToolItem
from common.text import normalize_manual_label

from .models import DeviceSyncState, SyncOperation


SYNC_MODELS = {
    "seed": Seed,
    "tool": Tool,
    "animal": Animal,
    "expense": Expense,
    "income": Income,
    "farm_product": FarmProduct,
    "supplier": Supplier,
}


def _blank_to_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
    return value or None


def _parse_date(value):
    value = _blank_to_none(value)
    if not value:
        return timezone.now().date()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Tarix düzgün deyil.") from exc


def _parse_datetime(value):
    value = _blank_to_none(value)
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("Tarix düzgün deyil.") from exc
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    return dt


def _parse_decimal(value, field_name):
    value = _blank_to_none(value)
    if value is None:
        raise ValueError(f"{field_name} tələb olunur.")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} düzgün deyil.") from exc


def _parse_int(value, field_name, default=None):
    value = _blank_to_none(value)
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"{field_name} tələb olunur.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} düzgün deyil.") from exc


def _seed_to_kg(value: Decimal, unit: str) -> Decimal:
    if unit == "ton":
        return value * Decimal("1000")
    if unit == "qram":
        return value / Decimal("1000")
    return value


def _seed_stock_kg(user, item, manual_name):
    if item:
        queryset = Seed.objects.filter(created_by=user, item=item)
    else:
        queryset = Seed.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=manual_name,
        )

    total = Decimal("0")
    for seed in queryset:
        total += _seed_to_kg(Decimal(seed.quantity), seed.unit)
    return total


def _tool_stock_total(user, item, manual_name):
    if item:
        queryset = Tool.objects.filter(created_by=user, item=item)
    else:
        queryset = Tool.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=manual_name,
        )

    total = 0
    for tool in queryset:
        total += int(tool.quantity)
    return total


def _is_forage_item(name: str) -> bool:
    return (name or "").strip().lower() in {"yonca", "koronilla", "seradella"}


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


def _set_expense_date(expense, entry_date):
    if expense.date != entry_date:
        expense.date = entry_date
        expense.save(update_fields=["date"])


def _merge_manual_seed_record(user, manual_name, quantity, unit, price, additional_info, entry_date):
    existing = (
        Seed.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"), manual_name__iexact=manual_name)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None

    total_kg = _seed_to_kg(Decimal(str(existing.quantity)), existing.unit) + _seed_to_kg(Decimal(str(quantity)), unit)
    if total_kg == 0:
        seed_type = ContentType.objects.get_for_model(Seed)
        Expense.objects.filter(content_type=seed_type, object_id=existing.id).delete()
        Income.objects.filter(content_type=seed_type, object_id=existing.id).delete()
        existing.delete()
        return "deleted"

    existing.item = None
    existing.manual_name = manual_name
    existing.quantity = total_kg
    existing.unit = "kg"
    existing.price = price
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.save()
    return existing


def _merge_manual_tool_record(user, manual_name, quantity, price, additional_info, entry_date):
    existing = (
        Tool.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"), manual_name__iexact=manual_name)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None
    total_qty = int(existing.quantity) + int(quantity)
    if total_qty == 0:
        tool_type = ContentType.objects.get_for_model(Tool)
        Expense.objects.filter(content_type=tool_type, object_id=existing.id).delete()
        Income.objects.filter(content_type=tool_type, object_id=existing.id).delete()
        existing.delete()
        return "deleted"
    existing.item = None
    existing.manual_name = manual_name
    existing.quantity = total_qty
    existing.price = price
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.save()
    return existing


def _merge_manual_farm_record(user, manual_name, quantity, unit, price, additional_info, entry_date):
    existing = (
        FarmProduct.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"), manual_name__iexact=manual_name, unit=unit)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None
    total_qty = Decimal(str(existing.quantity)) + Decimal(str(quantity))
    if total_qty == 0:
        model_type = ContentType.objects.get_for_model(FarmProduct)
        Expense.objects.filter(content_type=model_type, object_id=existing.id).delete()
        Income.objects.filter(content_type=model_type, object_id=existing.id).delete()
        existing.delete()
        return "deleted"
    existing.item = None
    existing.manual_name = manual_name
    existing.quantity = total_qty
    existing.unit = unit
    existing.price = price
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.save()
    return existing


def _merge_manual_animal_record(user, manual_name, gender, quantity, weight, price, additional_info, entry_date):
    existing = (
        Animal.objects.filter(created_by=user, gender=gender, identification_no__isnull=True)
        .filter((Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər")), manual_name__iexact=manual_name)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None
    total_qty = int(existing.quantity) + int(quantity)
    if total_qty == 0:
        model_type = ContentType.objects.get_for_model(Animal)
        Expense.objects.filter(content_type=model_type, object_id=existing.id).delete()
        existing.delete()
        return "deleted"
    existing.subcategory = None
    existing.manual_name = manual_name
    existing.quantity = total_qty
    existing.weight = weight
    existing.price = price
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.save()
    return existing


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


def _create_seed(user, data):
    item_id = _blank_to_none(data.get("item"))
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    quantity = _parse_decimal(data.get("quantity"), "Miqdar")
    unit = _blank_to_none(data.get("unit"))
    price = _blank_to_none(data.get("price")) or "0"
    additional_info = _blank_to_none(data.get("additional_info"))
    entry_date = _parse_date(data.get("date"))

    if not (item_id or manual_name):
        raise ValueError("Toxum və ya xüsusi ad tələb olunur.")
    if unit not in {"kg", "ton", "qram"}:
        raise ValueError("Ölçü vahidi düzgün deyil.")

    item = None
    if item_id:
        item = SeedItem.objects.select_related("category").filter(id=item_id).first()
        if not item:
            raise ValueError("Seçilmiş toxum növü tapılmadı.")
        if item.name == "Digər" and not manual_name:
            raise ValueError("Digər üçün ad daxil edin.")

    manual_value = manual_name if (not item or item.name == "Digər") else None

    if quantity < 0:
        available_kg = _seed_stock_kg(user, item, manual_value)
        needed_kg = _seed_to_kg(abs(quantity), unit)
        if available_kg < needed_kg:
            raise ValueError("Stokda kifayət qədər toxum yoxdur.")

    merged = _merge_manual_seed_record(user, manual_value, quantity, unit, price, additional_info, entry_date) if manual_value else None
    if merged:
        return merged if merged != "deleted" else None

    seed = Seed.objects.create(
        item=item,
        manual_name=manual_value,
        quantity=quantity,
        unit=unit,
        price=price,
        additional_info=additional_info,
        date=entry_date,
        created_by=user,
    )

    if quantity < 0:
        amount_val = abs(float(price))
        if amount_val <= 0:
            seed.delete()
            raise ValueError("Gəlir üçün məbləğ daxil edin.")

        category_name = item.category.name if item and item.category else "Digər"
        income_category_map = {
            "Taxıl toxumları": "Taxıl və Paxlalı Toxumları",
            "Paxlalı toxumları": "Taxıl və Paxlalı Toxumları",
            "Yem bitki toxumları": "Yem və Yağlı Bitki Toxumları",
            "Yağlı bitki toxumları": "Yem və Yağlı Bitki Toxumları",
            "Tərəvəz toxumları": "Tərəvəz və Bostan Toxumları",
            "Bostan toxumları": "Tərəvəz və Bostan Toxumları",
            "Meyvə toxumları": "Meyvə Toxumları",
        }
        Income.objects.create(
            category=income_category_map.get(category_name, "Digər"),
            item_name=item.name if item else manual_name,
            quantity=abs(quantity),
            unit="kq" if unit == "kg" else unit,
            amount=amount_val,
            additional_info=additional_info,
            date=entry_date,
            created_by=user,
            content_object=seed,
        )

    if quantity > 0 and float(price) > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name__icontains="Toxum").first()
        expense = Expense.objects.create(
            title=f"Toxum alışı: {item.name if item else manual_name}",
            amount=price,
            subcategory=expense_sub,
            manual_name="" if expense_sub else "Toxum alışı",
            additional_info=additional_info,
            created_by=user,
            content_object=seed,
        )
        _set_expense_date(expense, entry_date)

    return seed


def _create_tool(user, data):
    item_id = _blank_to_none(data.get("item"))
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    quantity = _parse_int(data.get("quantity"), "Miqdar")
    price = _blank_to_none(data.get("price")) or "0"
    additional_info = _blank_to_none(data.get("additional_info"))
    entry_date = _parse_date(data.get("date"))

    if not (item_id or manual_name):
        raise ValueError("Alət və ya xüsusi ad tələb olunur.")

    item = None
    if item_id:
        item = ToolItem.objects.select_related("category").filter(id=item_id).first()
        if not item:
            raise ValueError("Seçilmiş alət növü tapılmadı.")
        if item.name == "Digər" and not manual_name:
            raise ValueError("Digər üçün ad daxil edin.")

    manual_value = manual_name if (not item or item.name == "Digər") else None

    if quantity < 0:
        available = _tool_stock_total(user, item, manual_value)
        if available < abs(quantity):
            raise ValueError("Stokda kifayət qədər alət yoxdur.")

    merged = _merge_manual_tool_record(user, manual_value, quantity, price, additional_info, entry_date) if manual_value else None
    if merged:
        return merged if merged != "deleted" else None

    tool = Tool.objects.create(
        item=item,
        manual_name=manual_value,
        quantity=quantity,
        price=price,
        additional_info=additional_info,
        date=entry_date,
        created_by=user,
    )

    if quantity < 0:
        amount_val = abs(float(price))
        if amount_val <= 0:
            tool.delete()
            raise ValueError("Gəlir üçün məbləğ daxil edin.")

        Income.objects.create(
            category="Digər",
            item_name=item.name if item else manual_name,
            quantity=abs(quantity),
            unit="ədəd",
            amount=amount_val,
            additional_info=additional_info,
            date=entry_date,
            created_by=user,
            content_object=tool,
        )

    if quantity > 0 and float(price) > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name="Texnika alışı").first()
        expense = Expense.objects.create(
            title=f"Alət alışı: {item.name if item else manual_name}",
            amount=price,
            subcategory=expense_sub,
            manual_name="" if expense_sub else "Alət alışı (Digər)",
            additional_info=additional_info,
            created_by=user,
            content_object=tool,
        )
        _set_expense_date(expense, entry_date)

    return tool


def _create_animal(user, data):
    subcategory_id = _blank_to_none(data.get("subcategory"))
    identification_no = _blank_to_none(data.get("identification_no"))
    quantity = _parse_int(data.get("quantity"), "Miqdar", default=1)
    additional_info = _blank_to_none(data.get("additional_info"))
    gender = _blank_to_none(data.get("gender")) or "erkek"
    weight = _blank_to_none(data.get("weight"))
    price = _blank_to_none(data.get("price")) or "0"
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    entry_date = _parse_date(data.get("date"))

    if not (subcategory_id or manual_name):
        raise ValueError("Alt kateqoriya və ya xüsusi ad tələb olunur.")
    if not gender:
        raise ValueError("Cinsiyyət tələb olunur.")
    if quantity == 0:
        raise ValueError("Miqdar 0 ola bilməz.")

    subcategory = None
    if subcategory_id:
        subcategory = AnimalSubCategory.objects.select_related("category").filter(id=subcategory_id).first()
        if not subcategory:
            raise ValueError("Seçilmiş alt kateqoriya tapılmadı.")
        if subcategory.name == "Digər" and not manual_name:
            raise ValueError("Digər üçün ad daxil edin.")

    if abs(quantity) != 1:
        identification_no = None
    elif identification_no and Animal.objects.filter(identification_no=identification_no).exists():
        raise ValueError("Bu identifikasiya nömrəsi artıq mövcuddur.")

    manual_value = manual_name if (not subcategory or subcategory.name == "Digər") else None

    merged = _merge_manual_animal_record(user, manual_value, gender, quantity, weight, price, additional_info, entry_date) if manual_value and not identification_no else None
    if merged:
        return merged if merged != "deleted" else None

    animal = Animal.objects.create(
        subcategory=subcategory,
        manual_name=manual_value,
        identification_no=identification_no,
        additional_info=additional_info,
        gender=gender,
        weight=weight,
        price=price,
        quantity=quantity,
        date=entry_date,
        created_by=user,
    )

    if float(price) > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name="Heyvan alışı").first()
        expense = Expense.objects.create(
            title=f"Heyvan alışı: {subcategory.name if subcategory else manual_name}",
            amount=price,
            subcategory=expense_sub,
            manual_name="" if expense_sub else "Heyvan alışı (Digər)",
            additional_info=additional_info,
            created_by=user,
            content_object=animal,
        )
        _set_expense_date(expense, entry_date)

    return animal


def _create_expense(user, data):
    title = _blank_to_none(data.get("title"))
    amount = _parse_decimal(data.get("amount"), "Məbləğ")
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    subcategory_id = _blank_to_none(data.get("subcategory"))
    additional_info = _blank_to_none(data.get("additional_info"))
    entry_date = _parse_date(data.get("date"))

    if amount <= 0:
        raise ValueError("Məbləğ düzgün deyil.")

    subcategory = None
    if subcategory_id:
        subcategory = ExpenseSubCategory.objects.select_related("category").filter(id=subcategory_id).first()
        if not subcategory:
            raise ValueError("Seçilmiş alt kateqoriya tapılmadı.")

    if not (subcategory or manual_name):
        raise ValueError("Alt kateqoriya və ya xüsusi ad tələb olunur.")

    final_title = normalize_manual_label(title or (subcategory.name if subcategory else manual_name))
    if not subcategory:
        existing = (
            Expense.objects.filter(created_by=user, subcategory__isnull=True, manual_name__iexact=final_title)
            .order_by("-updated_at", "-created_at")
            .first()
        )
        if existing:
            new_amount = Decimal(str(existing.amount)) + amount
            if new_amount <= 0:
                existing.delete()
                return None
            existing.title = final_title
            existing.amount = new_amount
            existing.manual_name = final_title
            existing.additional_info = additional_info
            existing.save()
            _set_expense_date(existing, entry_date)
            return existing

    expense = Expense.objects.create(
        title=final_title,
        amount=amount,
        subcategory=subcategory,
        manual_name=None if subcategory else final_title,
        additional_info=additional_info,
        created_by=user,
    )
    _set_expense_date(expense, entry_date)
    return expense


def _create_supplier(user, data):
    name = (_blank_to_none(data.get("name")) or "").strip()
    category = (_blank_to_none(data.get("category")) or "").strip()
    manual_category = (_blank_to_none(data.get("manual_category")) or "").strip()
    location = (_blank_to_none(data.get("location")) or "").strip()
    phone = Supplier.normalize_phone((_blank_to_none(data.get("phone")) or "").strip())
    additional_info = (_blank_to_none(data.get("additional_info")) or "").strip()

    if not name:
        raise ValueError("Ad tələb olunur.")
    if not category:
        raise ValueError("Kateqoriya tələb olunur.")
    if category == "Digər" and not manual_category:
        raise ValueError("Digər üçün kateqoriya adı tələb olunur.")

    return Supplier.objects.create(
        name=name,
        category=category,
        manual_category=manual_category,
        location=location,
        rating=_parse_int(data.get("rating"), "Reytinq", default=5),
        phone=phone,
        additional_info=additional_info,
        last_order_date=_parse_date(data.get("last_order_date")) if _blank_to_none(data.get("last_order_date")) else None,
        created_by=user,
    )


def _get_record_id(data):
    record_id = _blank_to_none(data.get("record_id"))
    if not record_id:
        raise ValueError("record_id tələb olunur.")
    try:
        return int(record_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("record_id düzgün deyil.") from exc


def _version_for_record(record):
    updated_at = getattr(record, "updated_at", None) or getattr(record, "created_at", None)
    return updated_at.isoformat() if updated_at else None


def _assert_record_version(record, data):
    expected = _blank_to_none(data.get("record_version"))
    if not expected:
        raise ValueError("record_version tələb olunur.")

    current_dt = getattr(record, "updated_at", None) or getattr(record, "created_at", None)
    if current_dt is None:
        return

    normalized_expected = expected
    if normalized_expected.endswith("Z"):
        normalized_expected = normalized_expected[:-1] + "+00:00"

    try:
        expected_dt = datetime.fromisoformat(normalized_expected)
    except ValueError as exc:
        raise ValueError("record_version düzgün deyil.") from exc

    if expected_dt.tzinfo is None and current_dt.tzinfo is not None:
        expected_dt = expected_dt.replace(tzinfo=current_dt.tzinfo)

    if expected_dt != current_dt:
        raise ValueError("Conflict: bu qeyd başqa cihazda dəyişib. Səhifəni yeniləyin.")


FARM_PRODUCT_CATEGORIES = [
    "Süd və Süd Məhsulları",
    "Yumurta",
    "Ət Məhsulları",
    "Meyvə",
    "Tərəvəz",
    "Göyərti",
    "Taxıl Məhsulları",
    "Yem Bitkiləri",
    "Bostan Məhsulları",
    "Bal və Arıçılıq",
    "Gübrələr",
]
SEED_INCOME_CATEGORIES = [
    "Taxıl və Paxlalı Toxumları",
    "Yem və Yağlı Bitki Toxumları",
    "Tərəvəz və Bostan Toxumları",
    "Meyvə Toxumları",
]


def _category_type(category: str) -> str:
    if category == "Heyvanlar":
        return "animal"
    if category in SEED_INCOME_CATEGORIES:
        return "seed"
    if category in FARM_PRODUCT_CATEGORIES:
        return "farm"
    return "other"


def _farm_unit_lookup():
    lookup = {}
    for item in FarmProductItem.objects.select_related("category").all():
        key = (item.name or "").strip().lower()
        if key and key not in lookup:
            lookup[key] = item.unit
    return lookup


def _allowed_units_for_farm(item_name: str, unit_lookup):
    key = (item_name or "").strip().lower()
    if not key:
        return ["kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"]
    if key in {"yonca", "koronilla", "seradella"}:
        return ["kq", "bağlama"]
    base_unit = unit_lookup.get(key)
    if not base_unit:
        return ["kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"]
    if base_unit == "kq":
        return ["kq", "ton", "qram"]
    if base_unit == "litr":
        return ["litr", "ml"]
    return [base_unit]


def _parse_positive_decimal(value, field_name):
    parsed = _parse_decimal(value, field_name)
    if parsed <= 0:
        raise ValueError(f"{field_name} düzgün deyil.")
    return parsed


def _allowed_units_for_farm_product_item(item_obj):
    forage_items = {"yonca", "koronilla", "seradella"}
    if not item_obj or not item_obj.unit:
        return {"kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"}
    if (item_obj.name or "").strip().lower() in forage_items:
        return {"kq", "bağlama"}
    if item_obj.unit == "kq":
        return {"kq", "ton", "qram"}
    if item_obj.unit == "litr":
        return {"litr", "ml"}
    return {item_obj.unit}


def _resolve_farm_expense_subcategory(category_name: str | None):
    if not category_name:
        return None

    mapping = {
        "Süd və Süd Məhsulları": ("Heyvandarlıq", "Süd məhsulları"),
        "Yumurta": ("Heyvandarlıq", "Yumurta"),
        "Ət Məhsulları": ("Heyvandarlıq", "Ət"),
        "Bal və Arıçılıq": ("Heyvandarlıq", "Arıçılıq"),
        "Meyvə": ("Bitkiçilik", "Meyvə-Tərəvəz alışı"),
        "Tərəvəz": ("Bitkiçilik", "Meyvə-Tərəvəz alışı"),
        "Göyərti": ("Bitkiçilik", "Meyvə-Tərəvəz alışı"),
        "Bostan Məhsulları": ("Bitkiçilik", "Meyvə-Tərəvəz alışı"),
        "Taxıl Məhsulları": ("Bitkiçilik", "Taxıl alışı"),
        "Yem Bitkiləri": ("Bitkiçilik", "Yem bitkisi alışı"),
        "Gübrələr": ("Heyvandarlıq", "Gübrə"),
    }

    mapping_entry = mapping.get(category_name)
    if not mapping_entry:
        return None

    category_label, subcat_label = mapping_entry
    category = ExpenseCategory.objects.filter(name=category_label).first()
    if not category:
        return None

    return ExpenseSubCategory.objects.filter(category=category, name=subcat_label).first()


def _sync_farm_product_links(user, product, quantity_val: Decimal):
    product_type = ContentType.objects.get_for_model(FarmProduct)
    linked_income = Income.objects.filter(content_type=product_type, object_id=product.id).first()
    linked_expense = Expense.objects.filter(content_type=product_type, object_id=product.id).first()

    if quantity_val < 0:
        try:
            amount_val = abs(float(product.price))
        except (TypeError, ValueError):
            amount_val = 0

        category_name = product.item.category.name if product.item and product.item.category else "Digər"
        if linked_income:
            if amount_val > 0:
                linked_income.category = category_name
                linked_income.item_name = product.item.name if product.item else product.manual_name
                linked_income.quantity = abs(quantity_val)
                linked_income.unit = product.unit
                linked_income.amount = amount_val
                linked_income.additional_info = product.additional_info
                linked_income.date = product.date
                linked_income.save()
            else:
                linked_income.delete()
        elif amount_val > 0:
            Income.objects.create(
                category=category_name,
                item_name=product.item.name if product.item else product.manual_name,
                quantity=abs(quantity_val),
                unit=product.unit,
                amount=amount_val,
                additional_info=product.additional_info,
                date=product.date,
                created_by=user,
                content_object=product,
            )
    elif linked_income:
        linked_income.delete()

    if quantity_val > 0:
        try:
            price_val = float(product.price or 0)
        except (TypeError, ValueError):
            price_val = 0

        if price_val > 0:
            item_name = product.item.name if product.item else product.manual_name
            category_name = product.item.category.name if product.item and product.item.category else None
            subcat = _resolve_farm_expense_subcategory(category_name)
            title = f"{item_name} alışı"

            if linked_expense:
                linked_expense.amount = product.price
                linked_expense.title = title
                linked_expense.additional_info = product.additional_info
                linked_expense.subcategory = subcat
                linked_expense.manual_name = None if subcat else title
                linked_expense.save()
            else:
                Expense.objects.create(
                    title=title,
                    amount=product.price,
                    subcategory=subcat,
                    manual_name=None if subcat else title,
                    additional_info=product.additional_info,
                    created_by=user,
                    content_object=product,
                )
        elif linked_expense:
            linked_expense.delete()
    elif linked_expense:
        linked_expense.delete()


def _create_farm_product(user, data):
    item_id = _blank_to_none(data.get("item"))
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    quantity_val = _parse_decimal(data.get("quantity"), "Miqdar")
    unit = _blank_to_none(data.get("unit"))
    price = _blank_to_none(data.get("price")) or "0"
    additional_info = _blank_to_none(data.get("additional_info"))
    entry_date = _parse_date(data.get("date"))

    if not (item_id or manual_name) or not unit:
        raise ValueError("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")

    item = None
    if item_id:
        item = FarmProductItem.objects.filter(id=item_id).first()
        if not item:
            raise ValueError("Seçilmiş məhsul tapılmadı.")
        if item.name == "Digər" and not manual_name:
            raise ValueError("Zəhmət olmasa, Digər üçün ad daxil edin.")
        if unit not in _allowed_units_for_farm_product_item(item):
            raise ValueError("Ölçü vahidi bu kateqoriya üçün uyğun deyil.")

    effective_unit = unit
    effective_manual = manual_name if not item else None
    if item:
        if item.unit and item.unit not in {"kq", "litr"}:
            effective_unit = item.unit
        if (item.name or "").strip().lower() in {"yonca", "koronilla", "seradella"}:
            effective_unit = unit
        effective_manual = manual_name if item.name == "Digər" else None

    if quantity_val < 0:
        base_unit = "bağlama" if (item and (item.name or "").strip().lower() in {"yonca", "koronilla", "seradella"} and effective_unit == "bağlama") else _farm_base_unit(effective_unit)
        available_base = _farm_stock_base(
            user,
            item.name if item else effective_manual,
            base_unit,
        )
        needed_base = _convert_farm_qty(abs(quantity_val), effective_unit, base_unit)
        if available_base < needed_base:
            raise ValueError("Stokda kifayət qədər məhsul yoxdur.")

    merged = _merge_manual_farm_record(user, effective_manual, quantity_val, effective_unit, price, additional_info, entry_date) if effective_manual else None
    if merged:
        if merged != "deleted":
            _sync_farm_product_links(user, merged, Decimal(str(merged.quantity)))
            return merged
        return None

    product = FarmProduct.objects.create(
        item=item,
        manual_name=effective_manual,
        quantity=quantity_val,
        unit=effective_unit,
        price=price,
        additional_info=additional_info,
        date=entry_date,
        created_by=user,
    )
    _sync_farm_product_links(user, product, quantity_val)
    return product


def _update_farm_product(user, data):
    product = FarmProduct.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not product:
        raise ValueError("Məhsul tapılmadı.")
    _assert_record_version(product, data)

    item_id = _blank_to_none(data.get("item"))
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    quantity_val = _parse_decimal(data.get("quantity"), "Miqdar")
    unit = _blank_to_none(data.get("unit"))
    price = _blank_to_none(data.get("price")) or "0"
    additional_info = _blank_to_none(data.get("additional_info"))
    entry_date = _parse_date(data.get("date"))

    if not (item_id or manual_name) or not unit:
        raise ValueError("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")

    prev_quantity = Decimal(str(product.quantity))
    prev_unit = product.unit
    prev_item_name = product.item.name if product.item else product.manual_name

    item = None
    if item_id:
        item = FarmProductItem.objects.filter(id=item_id).first()
        if not item:
            raise ValueError("Seçilmiş məhsul tapılmadı.")
        if item.name == "Digər" and not manual_name:
            raise ValueError("Zəhmət olmasa, Digər üçün ad daxil edin.")
        if unit not in _allowed_units_for_farm_product_item(item):
            raise ValueError("Ölçü vahidi bu kateqoriya üçün uyğun deyil.")

    effective_unit = unit
    effective_manual = manual_name if not item else None
    if item:
        if item.unit and item.unit not in {"kq", "litr"}:
            effective_unit = item.unit
        if (item.name or "").strip().lower() in {"yonca", "koronilla", "seradella"}:
            effective_unit = unit
        effective_manual = manual_name if item.name == "Digər" else None

    if quantity_val < 0:
        base_unit = "bağlama" if (item and (item.name or "").strip().lower() in {"yonca", "koronilla", "seradella"} and effective_unit == "bağlama") else _farm_base_unit(effective_unit)
        current_name = item.name if item else effective_manual
        available_base = _farm_stock_base(user, current_name, base_unit)
        if prev_item_name == current_name and _farm_base_unit(prev_unit) == base_unit:
            available_base += _convert_farm_qty(prev_quantity, prev_unit, base_unit)
        needed_base = _convert_farm_qty(abs(quantity_val), effective_unit, base_unit)
        if available_base < needed_base:
            raise ValueError("Stokda kifayət qədər məhsul yoxdur.")

    product.item = item
    product.manual_name = effective_manual
    product.quantity = quantity_val
    product.unit = effective_unit
    product.price = price
    product.additional_info = additional_info
    product.date = entry_date
    product.save()

    _sync_farm_product_links(user, product, quantity_val)
    return product


def _delete_farm_product(user, data):
    product = FarmProduct.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not product:
        raise ValueError("Məhsul tapılmadı.")
    _assert_record_version(product, data)
    product_type = ContentType.objects.get_for_model(FarmProduct)
    Expense.objects.filter(content_type=product_type, object_id=product.id).delete()
    Income.objects.filter(content_type=product_type, object_id=product.id).delete()
    deleted_id = product.id
    product.delete()
    return deleted_id


def _create_quick_expense(user, data):
    action = _blank_to_none(data.get("action")) or "quick_add"

    if action == "quick_add":
        name = (_blank_to_none(data.get("name")) or "").strip()
        amount_raw = _blank_to_none(data.get("custom_amount")) or data.get("amount")
        amount_val = _parse_positive_decimal(amount_raw, "Məbləğ")
        subcat_qs = ExpenseSubCategory.objects.filter(name__iexact=name).select_related("category")
        if name.lower() == "gübrə":
            subcat = subcat_qs.filter(category__name="Heyvandarlıq").first() or subcat_qs.first()
        else:
            subcat = subcat_qs.first()
        return Expense.objects.create(
            title=name,
            amount=amount_val,
            subcategory=subcat,
            manual_name=name if not subcat else None,
            created_by=user,
        )

    if action == "custom_amount":
        amount_val = _parse_positive_decimal(data.get("amount"), "Məbləğ")
        subcat = ExpenseSubCategory.objects.filter(name__iexact="Digər").select_related("category").first()
        return Expense.objects.create(
            title="Xüsusi xərc",
            amount=amount_val,
            subcategory=subcat,
            manual_name=None,
            created_by=user,
        )

    if action == "template_add":
        template_id = _blank_to_none(data.get("template_id"))
        if not template_id:
            raise ValueError("Şablon tapılmadı.")
        original = Expense.objects.filter(pk=template_id, created_by=user).first()
        if not original:
            raise ValueError("Şablon tapılmadı.")
        amount_raw = _blank_to_none(data.get("custom_amount")) or original.amount
        amount_val = _parse_positive_decimal(amount_raw, "Məbləğ")
        return Expense.objects.create(
            title=original.title,
            amount=amount_val,
            subcategory=original.subcategory,
            manual_name=original.manual_name,
            created_by=user,
        )

    raise ValueError("Bu sync əməliyyatı dəstəklənmir.")


def _create_quick_income(user, data):
    action = _blank_to_none(data.get("action")) or "quick_add"

    if action == "quick_add":
        amount_raw = _blank_to_none(data.get("custom_amount")) or data.get("amount")
        amount_val = _parse_positive_decimal(amount_raw, "Məbləğ")
        quantity_val = _parse_positive_decimal(data.get("quantity"), "Miqdar")
        payload = {
            "category": data.get("category"),
            "item_name": data.get("name"),
            "quantity": str(quantity_val),
            "unit": data.get("unit"),
            "amount": str(amount_val),
            "gender": data.get("gender") or "",
            "identification_no": data.get("identification_no") or "",
            "additional_info": data.get("additional_info") or "",
        }
        return _create_income(user, payload)

    if action == "custom_amount":
        amount_val = _parse_positive_decimal(data.get("amount"), "Məbləğ")
        return Income.objects.create(
            category="Digər",
            item_name="Xüsusi gəlir",
            quantity=1,
            unit="ədəd",
            amount=amount_val,
            created_by=user,
        )

    if action == "template_add":
        template_id = _blank_to_none(data.get("template_id"))
        if not template_id:
            raise ValueError("Şablon tapılmadı.")
        original = Income.objects.filter(pk=template_id, created_by=user).first()
        if not original:
            raise ValueError("Şablon tapılmadı.")
        amount_raw = _blank_to_none(data.get("custom_amount")) or original.amount
        amount_val = _parse_positive_decimal(amount_raw, "Məbləğ")
        payload = {
            "category": original.category,
            "item_name": original.item_name,
            "quantity": str(original.quantity),
            "unit": original.unit,
            "amount": str(amount_val),
            "gender": original.gender or "",
            "additional_info": original.additional_info or "",
        }
        return _create_income(user, payload)

    raise ValueError("Bu sync əməliyyatı dəstəklənmir.")


def _seed_unit_for_income(unit: str) -> str:
    return "kg" if unit == "kq" else unit


def _farm_base_unit(unit: str) -> str:
    if unit in {"kq", "ton", "qram"}:
        return "kq"
    if unit in {"litr", "ml"}:
        return "litr"
    return unit


def _farm_stock_base(user, item_name: str, base_unit: str) -> Decimal:
    item = FarmProductItem.objects.filter(name=item_name).first()
    if item:
        queryset = FarmProduct.objects.filter(created_by=user, item=item)
    else:
        queryset = FarmProduct.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=item_name,
        )

    total = Decimal("0")
    for product in queryset:
        if base_unit == "bağlama":
            if product.unit != "bağlama":
                continue
            total += Decimal(product.quantity)
        elif base_unit == "kq":
            if product.unit not in {"kq", "ton", "qram"}:
                continue
            total += _convert_farm_qty(Decimal(product.quantity), product.unit, "kq")
        elif base_unit == "litr":
            if product.unit not in {"litr", "ml"}:
                continue
            total += _convert_farm_qty(Decimal(product.quantity), product.unit, "litr")
        else:
            if product.unit != base_unit:
                continue
            total += Decimal(product.quantity)
    return total


def _adjust_seed_stock(user, item_name: str, quantity: Decimal, unit: str, note: str, price: Decimal | None = None, entry_date=None):
    if quantity == 0:
        return None
    item = SeedItem.objects.filter(name=item_name).first()
    return Seed.objects.create(
        item=item,
        manual_name=None if item else item_name,
        quantity=Decimal(str(quantity)),
        unit=_seed_unit_for_income(unit),
        price=price if price is not None else 0,
        additional_info=note,
        created_by=user,
        date=entry_date or timezone.now().date(),
    )


def _adjust_farm_stock(user, item_name: str, quantity: Decimal, unit: str, note: str, price: Decimal | None = None, entry_date=None):
    if quantity == 0:
        return None
    item = FarmProductItem.objects.filter(name=item_name).first()
    return FarmProduct.objects.create(
        item=item,
        manual_name=None if item else item_name,
        quantity=Decimal(str(quantity)),
        unit=unit,
        price=price if price is not None else 0,
        additional_info=note,
        created_by=user,
        date=entry_date or timezone.now().date(),
    )


def _get_animal_by_id(user, identification_no: str | None):
    if not identification_no:
        return None
    return Animal.objects.filter(created_by=user, identification_no=identification_no).first()


def _create_income(user, data):
    category = (_blank_to_none(data.get("category")) or "").strip()
    item_name = (_blank_to_none(data.get("item_name")) or "").strip()
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    quantity = _parse_positive_decimal(data.get("quantity"), "Miqdar")
    unit = (_blank_to_none(data.get("unit")) or "").strip()
    amount_val = _parse_positive_decimal(data.get("amount"), "Məbləğ")
    gender = (_blank_to_none(data.get("gender")) or "").strip()
    identification_no = (_blank_to_none(data.get("identification_no")) or "").strip()
    additional_info = _blank_to_none(data.get("additional_info"))
    entry_date = _parse_date(data.get("date"))

    if not category or not unit:
        raise ValueError("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")

    ctype = _category_type(category)
    if category.lower() == "digər" or item_name.lower() == "digər" or not item_name:
        if not manual_name:
            raise ValueError("Zəhmət olmasa, Digər üçün ad daxil edin.")
        item_name = manual_name

    if ctype == "animal" and not gender:
        raise ValueError("Zəhmət olmasa, heyvanlar üçün cinsiyyət seçin.")

    if ctype == "animal":
        qty_int = int(quantity)
        if Decimal(qty_int) != quantity:
            raise ValueError("Heyvanlar üçün miqdar tam ədəd olmalıdır.")
        if identification_no and abs(qty_int) != 1:
            raise ValueError("İdentifikasiya nömrəsi yalnız miqdar ±1 olduqda verilə bilər.")

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
        raise ValueError("Ölçü vahidi bu kateqoriya üçün uyğun deyil.")

    if ctype == "seed":
        available_kg = _seed_stock_kg(user, SeedItem.objects.filter(name=item_name).first(), item_name)
        needed_kg = _seed_to_kg(quantity, unit)
        if available_kg < needed_kg:
            raise ValueError("Stokda kifayət qədər toxum yoxdur.")
    elif ctype == "farm":
        base_unit = _farm_base_unit(unit)
        available_base = _farm_stock_base(user, item_name, base_unit)
        needed_base = _convert_farm_qty(quantity, unit, base_unit)
        if available_base < needed_base:
            raise ValueError("Stokda kifayət qədər məhsul yoxdur.")

    income = Income.objects.create(
        category=category,
        item_name=item_name,
        quantity=quantity,
        unit=unit,
        amount=amount_val,
        gender=gender if ctype == "animal" else None,
        additional_info=additional_info,
        date=entry_date,
        created_by=user,
    )

    note = "Gəlir satışı"
    if ctype == "seed":
        stock_item = _adjust_seed_stock(user, item_name, -abs(quantity), unit, note, amount_val, entry_date)
        if stock_item:
            income.content_object = stock_item
            income.save(update_fields=["content_type", "object_id"])
    elif ctype == "farm":
        stock_item = _adjust_farm_stock(user, item_name, -abs(quantity), unit, note, amount_val, entry_date)
        if stock_item:
            income.content_object = stock_item
            income.save(update_fields=["content_type", "object_id"])
    elif ctype == "animal":
        qty_int = int(quantity)
        target_animal = _get_animal_by_id(user, identification_no)
        if identification_no:
            if not target_animal:
                income.delete()
                raise ValueError("Bu identifikasiya nömrəsinə uyğun heyvan tapılmadı.")
            if target_animal.subcategory:
                if target_animal.subcategory.name != item_name:
                    income.delete()
                    raise ValueError("Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
            elif (target_animal.manual_name or "").strip() != item_name:
                income.delete()
                raise ValueError("Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
            subcat = target_animal.subcategory
        else:
            subcat = AnimalSubCategory.objects.filter(name=item_name).first()

        display_animal = Animal.objects.create(
            subcategory=subcat,
            manual_name=None if subcat else item_name,
            gender=gender,
            quantity=-abs(qty_int),
            price=amount_val,
            additional_info=f"Gəlir satışı | income:{income.id}",
            created_by=user,
            date=entry_date,
        )
        if identification_no:
            target_animal.delete()
        income.content_object = display_animal
        income.save(update_fields=["content_type", "object_id"])
    elif category.lower() == "digər" or (_blank_to_none(data.get("item_name")) or "").strip().lower() == "digər":
        stock_item = _adjust_other_stock(user, item_name, -abs(quantity), unit, note, amount_val, gender or None)
        if stock_item:
            income.content_object = stock_item
            income.save(update_fields=["content_type", "object_id"])

    return income


def _update_seed(user, data):
    seed = Seed.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not seed:
        raise ValueError("Toxum tapılmadı.")
    _assert_record_version(seed, data)

    item_id = _blank_to_none(data.get("item"))
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    quantity_val = _parse_decimal(data.get("quantity"), "Miqdar")
    unit = _blank_to_none(data.get("unit"))
    price = _blank_to_none(data.get("price")) or "0"
    additional_info = _blank_to_none(data.get("additional_info"))
    entry_date = _parse_date(data.get("date"))

    if not (item_id or manual_name) or not unit:
        raise ValueError("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")

    prev_quantity = Decimal(str(seed.quantity))
    prev_unit = seed.unit
    prev_item = seed.item
    prev_manual = seed.manual_name

    seed.quantity = quantity_val
    seed.unit = unit
    seed.additional_info = additional_info
    seed.date = entry_date
    if item_id:
        item = SeedItem.objects.filter(id=item_id).first()
        if not item:
            raise ValueError("Seçilmiş toxum növü tapılmadı.")
        if item.name == "Digər" and not manual_name:
            raise ValueError("Digər üçün ad daxil edin.")
        seed.manual_name = manual_name if item.name == "Digər" else None
        seed.item = item
    else:
        seed.manual_name = manual_name
        seed.item = None
    seed.price = price

    if quantity_val < 0:
        prev_total = _seed_to_kg(prev_quantity, prev_unit)
        available_kg = _seed_stock_kg(user, seed.item, seed.manual_name)
        if prev_item == seed.item and prev_manual == seed.manual_name:
            available_kg += prev_total
        needed_kg = _seed_to_kg(abs(quantity_val), unit)
        if available_kg < needed_kg:
            raise ValueError("Stokda kifayət qədər toxum yoxdur.")

    seed.save()

    seed_type = ContentType.objects.get_for_model(Seed)
    linked_income = Income.objects.filter(content_type=seed_type, object_id=seed.id).first()
    if quantity_val < 0:
        try:
            amount_val = abs(float(seed.price))
        except (TypeError, ValueError):
            amount_val = 0

        category_name = seed.item.category.name if seed.item and seed.item.category else "Digər"
        income_category_map = {
            "Taxıl toxumları": "Taxıl və Paxlalı Toxumları",
            "Paxlalı toxumları": "Taxıl və Paxlalı Toxumları",
            "Yem bitki toxumları": "Yem və Yağlı Bitki Toxumları",
            "Yağlı bitki toxumları": "Yem və Yağlı Bitki Toxumları",
            "Tərəvəz toxumları": "Tərəvəz və Bostan Toxumları",
            "Bostan toxumları": "Tərəvəz və Bostan Toxumları",
            "Meyvə toxumları": "Meyvə Toxumları",
        }
        income_category = income_category_map.get(category_name, "Digər")
        if linked_income:
            if amount_val > 0:
                linked_income.category = income_category
                linked_income.item_name = seed.item.name if seed.item else seed.manual_name
                linked_income.quantity = abs(quantity_val)
                linked_income.unit = "kq" if seed.unit == "kg" else seed.unit
                linked_income.amount = amount_val
                linked_income.additional_info = seed.additional_info
                linked_income.date = seed.date
                linked_income.save()
            else:
                linked_income.delete()
        elif amount_val > 0:
            Income.objects.create(
                category=income_category,
                item_name=seed.item.name if seed.item else seed.manual_name,
                quantity=abs(quantity_val),
                unit="kq" if seed.unit == "kg" else seed.unit,
                amount=amount_val,
                additional_info=seed.additional_info,
                date=seed.date,
                created_by=user,
                content_object=seed,
            )
    elif linked_income:
        linked_income.delete()

    linked_expense = Expense.objects.filter(content_type=seed_type, object_id=seed.id).first()
    if linked_expense:
        if quantity_val > 0 and seed.price and float(seed.price) > 0:
            linked_expense.amount = seed.price
            linked_expense.title = f"Toxum alışı: {seed.item.name if seed.item else seed.manual_name}"
            linked_expense.additional_info = seed.additional_info
            linked_expense.save()
        else:
            linked_expense.delete()
    elif quantity_val > 0 and seed.price and float(seed.price) > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name__icontains="Toxum").first()
        Expense.objects.create(
            title=f"Toxum alışı: {seed.item.name if seed.item else seed.manual_name}",
            amount=seed.price,
            subcategory=expense_sub,
            manual_name="" if expense_sub else "Toxum alışı",
            additional_info=seed.additional_info,
            created_by=user,
            content_object=seed,
        )
    return seed


def _delete_seed(user, data):
    seed = Seed.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not seed:
        raise ValueError("Toxum tapılmadı.")
    _assert_record_version(seed, data)
    seed_type = ContentType.objects.get_for_model(Seed)
    Expense.objects.filter(content_type=seed_type, object_id=seed.id).delete()
    Income.objects.filter(content_type=seed_type, object_id=seed.id).delete()
    deleted_id = seed.id
    seed.delete()
    return deleted_id


def _update_tool(user, data):
    tool = Tool.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not tool:
        raise ValueError("Alət tapılmadı.")
    _assert_record_version(tool, data)

    item_id = _blank_to_none(data.get("item"))
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    quantity_val = _parse_int(data.get("quantity"), "Miqdar")
    price = _blank_to_none(data.get("price")) or "0"
    additional_info = _blank_to_none(data.get("additional_info"))
    entry_date = _parse_date(data.get("date"))

    if not (item_id or manual_name):
        raise ValueError("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")

    prev_quantity = int(tool.quantity)
    prev_item = tool.item
    prev_manual = tool.manual_name

    tool.quantity = quantity_val
    tool.additional_info = additional_info
    tool.date = entry_date
    if item_id:
        item = ToolItem.objects.filter(id=item_id).first()
        if not item:
            raise ValueError("Seçilmiş alət növü tapılmadı.")
        if item.name == "Digər" and not manual_name:
            raise ValueError("Digər üçün ad daxil edin.")
        tool.manual_name = manual_name if item.name == "Digər" else None
        tool.item = item
    else:
        tool.manual_name = manual_name
        tool.item = None
    tool.price = price

    if quantity_val < 0:
        available = _tool_stock_total(
            user,
            tool.item,
            tool.manual_name if (not tool.item or (tool.item and tool.item.name == "Digər")) else None,
        )
        if prev_item == tool.item and prev_manual == tool.manual_name:
            available += prev_quantity
        if available < abs(quantity_val):
            raise ValueError("Stokda kifayət qədər alət yoxdur.")

    tool.save()

    tool_type = ContentType.objects.get_for_model(Tool)
    linked_income = Income.objects.filter(content_type=tool_type, object_id=tool.id).first()
    if quantity_val < 0:
        try:
            amount_val = abs(float(tool.price))
        except (TypeError, ValueError):
            amount_val = 0
        if linked_income:
            if amount_val > 0:
                linked_income.category = "Digər"
                linked_income.item_name = tool.item.name if tool.item else tool.manual_name
                linked_income.quantity = abs(quantity_val)
                linked_income.unit = "ədəd"
                linked_income.amount = amount_val
                linked_income.additional_info = tool.additional_info
                linked_income.date = tool.date
                linked_income.save()
            else:
                linked_income.delete()
        elif amount_val > 0:
            Income.objects.create(
                category="Digər",
                item_name=tool.item.name if tool.item else tool.manual_name,
                quantity=abs(quantity_val),
                unit="ədəd",
                amount=amount_val,
                additional_info=tool.additional_info,
                date=tool.date,
                created_by=user,
                content_object=tool,
            )
    elif linked_income:
        linked_income.delete()

    linked_expense = Expense.objects.filter(content_type=tool_type, object_id=tool.id).first()
    if linked_expense:
        if quantity_val > 0 and tool.price and float(tool.price) > 0:
            linked_expense.amount = tool.price
            linked_expense.title = f"Alət alışı: {tool.item.name if tool.item else tool.manual_name}"
            linked_expense.additional_info = tool.additional_info
            linked_expense.save()
        else:
            linked_expense.delete()
    elif quantity_val > 0 and tool.price and float(tool.price) > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name="Texnika alışı").first()
        Expense.objects.create(
            title=f"Alət alışı: {tool.item.name if tool.item else tool.manual_name}",
            amount=tool.price,
            subcategory=expense_sub,
            manual_name="" if expense_sub else "Alət alışı (Digər)",
            additional_info=tool.additional_info,
            created_by=user,
            content_object=tool,
        )
    return tool


def _delete_tool(user, data):
    tool = Tool.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not tool:
        raise ValueError("Alət tapılmadı.")
    _assert_record_version(tool, data)
    tool_type = ContentType.objects.get_for_model(Tool)
    Expense.objects.filter(content_type=tool_type, object_id=tool.id).delete()
    Income.objects.filter(content_type=tool_type, object_id=tool.id).delete()
    deleted_id = tool.id
    tool.delete()
    return deleted_id


def _update_animal(user, data):
    animal = Animal.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not animal:
        raise ValueError("Heyvan tapılmadı.")
    _assert_record_version(animal, data)

    subcategory_id = _blank_to_none(data.get("subcategory"))
    identification_no = _blank_to_none(data.get("identification_no"))
    quantity = _parse_int(data.get("quantity"), "Miqdar", default=1)
    additional_info = _blank_to_none(data.get("additional_info"))
    gender = _blank_to_none(data.get("gender")) or "erkek"
    weight = _blank_to_none(data.get("weight"))
    price = _blank_to_none(data.get("price")) or "0"
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    entry_date = _parse_date(data.get("date"))

    if not (subcategory_id or manual_name) or not gender:
        raise ValueError("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")
    if quantity == 0:
        raise ValueError("Miqdar 0 ola bilməz.")

    if abs(quantity) != 1:
        identification_no = None
    elif identification_no and Animal.objects.filter(identification_no=identification_no).exclude(pk=animal.pk).exists():
        raise ValueError("Bu identifikasiya nömrəsi artıq mövcuddur.")

    animal.identification_no = identification_no
    animal.quantity = quantity
    animal.additional_info = additional_info
    animal.gender = gender
    animal.date = entry_date
    if subcategory_id:
        subcategory = AnimalSubCategory.objects.filter(id=subcategory_id).first()
        if not subcategory:
            raise ValueError("Seçilmiş alt kateqoriya tapılmadı.")
        if subcategory.name == "Digər" and not manual_name:
            raise ValueError("Digər üçün ad daxil edin.")
        animal.manual_name = manual_name if subcategory.name == "Digər" else None
        animal.subcategory = subcategory
    else:
        animal.manual_name = manual_name
        animal.subcategory = None

    animal.weight = weight
    animal.price = price
    animal.save()

    animal_type = ContentType.objects.get_for_model(Animal)
    linked_expense = Expense.objects.filter(content_type=animal_type, object_id=animal.id).first()
    if linked_expense:
        if animal.price and float(animal.price) > 0:
            linked_expense.amount = animal.price
            linked_expense.title = f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}"
            linked_expense.additional_info = animal.additional_info
            linked_expense.save()
        else:
            linked_expense.delete()
    elif animal.price and float(animal.price) > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name="Heyvan alışı").first()
        Expense.objects.create(
            title=f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}",
            amount=animal.price,
            subcategory=expense_sub,
            manual_name="" if expense_sub else "Heyvan alışı (Digər)",
            additional_info=animal.additional_info,
            created_by=user,
            content_object=animal,
        )
    return animal


def _delete_animal(user, data):
    animal = Animal.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not animal:
        raise ValueError("Heyvan tapılmadı.")
    _assert_record_version(animal, data)
    animal_type = ContentType.objects.get_for_model(Animal)
    Expense.objects.filter(content_type=animal_type, object_id=animal.id).delete()
    deleted_id = animal.id
    animal.delete()
    return deleted_id


def _update_expense(user, data):
    expense = Expense.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not expense:
        raise ValueError("Xərc tapılmadı.")
    _assert_record_version(expense, data)
    title = _blank_to_none(data.get("title"))
    amount_val = float(_parse_positive_decimal(data.get("amount"), "Məbləğ"))
    subcategory_id = _blank_to_none(data.get("subcategory"))
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    additional_info = _blank_to_none(data.get("additional_info"))

    subcategory = ExpenseSubCategory.objects.filter(id=subcategory_id).first() if subcategory_id else None
    if not (subcategory or manual_name):
        raise ValueError("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")

    expense.title = normalize_manual_label(title if title else (subcategory.name if subcategory else manual_name))
    expense.amount = amount_val
    expense.subcategory = subcategory
    expense.manual_name = None if subcategory else normalize_manual_label(title if title else manual_name)
    expense.additional_info = additional_info
    expense.save()

    if expense.content_object:
        item = expense.content_object
        if hasattr(item, "price"):
            item.price = expense.amount
        elif hasattr(item, "amount"):
            item.amount = expense.amount
        if hasattr(item, "additional_info"):
            item.additional_info = additional_info
        item.save()
    return expense


def _delete_expense(user, data):
    expense = Expense.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not expense:
        raise ValueError("Xərc tapılmadı.")
    _assert_record_version(expense, data)
    if expense.content_object:
        expense.content_object.delete()
    deleted_id = expense.id
    expense.delete()
    return deleted_id


def _update_supplier(user, data):
    supplier = Supplier.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not supplier:
        raise ValueError("Təchizatçı tapılmadı.")
    _assert_record_version(supplier, data)

    name = (_blank_to_none(data.get("name")) or "").strip()
    category = (_blank_to_none(data.get("category")) or "").strip()
    manual_category = (_blank_to_none(data.get("manual_category")) or "").strip()
    location = (_blank_to_none(data.get("location")) or "").strip()
    phone = Supplier.normalize_phone((_blank_to_none(data.get("phone")) or "").strip())
    additional_info = (_blank_to_none(data.get("additional_info")) or "").strip()

    if not name:
        raise ValueError("Ad tələb olunur.")
    if not category:
        raise ValueError("Kateqoriya tələb olunur.")
    if category == "Digər" and not manual_category:
        raise ValueError("Digər üçün kateqoriya adı tələb olunur.")

    supplier.name = name
    supplier.category = category
    supplier.manual_category = manual_category
    supplier.location = location
    supplier.rating = _parse_int(data.get("rating"), "Reytinq", default=5)
    supplier.phone = phone
    supplier.additional_info = additional_info
    supplier.last_order_date = _parse_date(data.get("last_order_date")) if _blank_to_none(data.get("last_order_date")) else None
    supplier.save()
    return supplier


def _delete_supplier(user, data):
    supplier = Supplier.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not supplier:
        raise ValueError("Təchizatçı tapılmadı.")
    _assert_record_version(supplier, data)
    deleted_id = supplier.id
    supplier.delete()
    return deleted_id


def _delete_income_animals(user, income_id: int) -> None:
    tag = f"income:{income_id}"
    Animal.objects.filter(created_by=user, additional_info__icontains=tag).delete()


def _update_income(user, data):
    income = Income.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not income:
        raise ValueError("Gəlir tapılmadı.")
    _assert_record_version(income, data)

    prev_category = income.category
    prev_item = income.item_name
    prev_quantity = Decimal(str(income.quantity))
    prev_unit = income.unit
    prev_gender = income.gender or ""
    prev_amount = Decimal(str(income.amount))

    category = (_blank_to_none(data.get("category")) or "").strip()
    item_name = (_blank_to_none(data.get("item_name")) or "").strip()
    manual_name = normalize_manual_label(_blank_to_none(data.get("manual_name")))
    quantity = _parse_positive_decimal(data.get("quantity"), "Miqdar")
    unit = (_blank_to_none(data.get("unit")) or "").strip()
    amount_val = _parse_positive_decimal(data.get("amount"), "Məbləğ")
    gender = (_blank_to_none(data.get("gender")) or "").strip()
    identification_no = (_blank_to_none(data.get("identification_no")) or "").strip()
    additional_info = _blank_to_none(data.get("additional_info"))
    date_value = _parse_date(data.get("date"))

    if not category or not unit:
        raise ValueError("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")
    ctype = _category_type(category)
    if category.lower() == "digər" or item_name.lower() == "digər" or not item_name:
        if not manual_name:
            raise ValueError("Zəhmət olmasa, Digər üçün ad daxil edin.")
        item_name = manual_name
    if ctype == "animal" and not gender:
        raise ValueError("Zəhmət olmasa, heyvanlar üçün cinsiyyət seçin.")
    if ctype == "animal":
        qty_int = int(quantity)
        if Decimal(qty_int) != quantity:
            raise ValueError("Heyvanlar üçün miqdar tam ədəd olmalıdır.")
        if identification_no and abs(qty_int) != 1:
            raise ValueError("İdentifikasiya nömrəsi yalnız miqdar ±1 olduqda verilə bilər.")

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
        raise ValueError("Ölçü vahidi bu kateqoriya üçün uyğun deyil.")

    prev_type = _category_type(prev_category)
    new_type = ctype
    if new_type == "seed":
        available_kg = _seed_stock_kg(user, SeedItem.objects.filter(name=item_name).first(), item_name)
        if prev_type == "seed" and prev_item == item_name:
            available_kg += _seed_to_kg(prev_quantity, prev_unit)
        needed_kg = _seed_to_kg(quantity, unit)
        if available_kg < needed_kg:
            raise ValueError("Stokda kifayət qədər toxum yoxdur.")
    elif new_type == "farm":
        base_unit = _farm_base_unit(unit)
        available_base = _farm_stock_base(user, item_name, base_unit)
        if prev_type == "farm" and prev_item == item_name and _farm_base_unit(prev_unit) == base_unit:
            available_base += _convert_farm_qty(prev_quantity, prev_unit, base_unit)
        needed_base = _convert_farm_qty(quantity, unit, base_unit)
        if available_base < needed_base:
            raise ValueError("Stokda kifayət qədər məhsul yoxdur.")

    income.category = category
    income.item_name = item_name
    income.quantity = quantity
    income.unit = unit
    income.amount = amount_val
    income.gender = gender if ctype == "animal" else None
    income.additional_info = additional_info
    income.date = date_value
    income.save()

    note = "Gəlir düzəlişi"
    if prev_type == "seed":
        _adjust_seed_stock(user, prev_item, abs(prev_quantity), prev_unit, note, prev_amount, date_value)
    elif prev_type == "farm":
        _adjust_farm_stock(user, prev_item, abs(prev_quantity), prev_unit, note, prev_amount, date_value)
    elif prev_type == "animal":
        _delete_income_animals(user, income.id)

    if new_type == "seed":
        stock_item = _adjust_seed_stock(user, item_name, -abs(quantity), unit, note, amount_val, date_value)
        if stock_item:
            income.content_object = stock_item
            income.save(update_fields=["content_type", "object_id"])
    elif new_type == "farm":
        stock_item = _adjust_farm_stock(user, item_name, -abs(quantity), unit, note, amount_val, date_value)
        if stock_item:
            income.content_object = stock_item
            income.save(update_fields=["content_type", "object_id"])
    elif new_type == "animal":
        qty_int = int(quantity)
        target_animal = _get_animal_by_id(user, identification_no)
        if identification_no:
            if not target_animal:
                raise ValueError("Bu identifikasiya nömrəsinə uyğun heyvan tapılmadı.")
            if target_animal.subcategory:
                if target_animal.subcategory.name != item_name:
                    raise ValueError("Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
            elif (target_animal.manual_name or "").strip() != item_name:
                raise ValueError("Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
            subcat = target_animal.subcategory
        else:
            subcat = AnimalSubCategory.objects.filter(name=item_name).first()
        display_animal = Animal.objects.create(
            subcategory=subcat,
            manual_name=None if subcat else item_name,
            gender=gender,
            quantity=-abs(qty_int),
            price=amount_val,
            additional_info=f"Gəlir satışı | income:{income.id}",
            created_by=user,
            date=date_value,
        )
        if identification_no:
            target_animal.delete()
        income.content_object = display_animal
        income.save(update_fields=["content_type", "object_id"])
    else:
        if income.content_object:
            income.content_object = None
            income.save(update_fields=["content_type", "object_id"])
    return income


def _delete_income(user, data):
    income = Income.objects.filter(pk=_get_record_id(data), created_by=user).first()
    if not income:
        raise ValueError("Gəlir tapılmadı.")
    _assert_record_version(income, data)
    note = "Gəlir silindi"
    ctype = _category_type(income.category)
    if ctype == "seed":
        _adjust_seed_stock(user, income.item_name, abs(Decimal(str(income.quantity))), income.unit, note, Decimal(str(income.amount)), income.date)
    elif ctype == "farm":
        _adjust_farm_stock(user, income.item_name, abs(Decimal(str(income.quantity))), income.unit, note, Decimal(str(income.amount)), income.date)
    elif ctype == "animal":
        _delete_income_animals(user, income.id)
    deleted_id = income.id
    income.delete()
    return deleted_id


def _update_stock(user, data):
    update_type = _blank_to_none(data.get("update_type"))
    update_id = _blank_to_none(data.get("update_id"))
    target_raw = data.get("target_quantity")
    note = "Stok səhifəsindən düzəliş"

    if not update_type or not update_id:
        raise ValueError("Məlumatlar natamamdır.")

    if update_type == "seed":
        target_value = _parse_decimal(target_raw, "Miqdar")
        seed_qs = Seed.objects.filter(created_by=user, item_id=update_id)
        current_total = Decimal("0")
        for seed in seed_qs:
            current_total += _seed_to_kg(Decimal(seed.quantity), seed.unit)
        delta = target_value - current_total
        if delta != 0:
            return Seed.objects.create(item_id=update_id, quantity=delta, unit="kg", price=0, additional_info=note, created_by=user)
        return None

    if update_type == "seed_other":
        target_value = _parse_decimal(target_raw, "Miqdar")
        seed_qs = Seed.objects.filter(created_by=user, manual_name=update_id).filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        current_total = Decimal("0")
        for seed in seed_qs:
            current_total += _seed_to_kg(Decimal(seed.quantity), seed.unit)
        delta = target_value - current_total
        if delta != 0:
            return Seed.objects.create(item=None, manual_name=update_id, quantity=delta, unit="kg", price=0, additional_info=note, created_by=user)
        return None

    if update_type == "tool":
        target_value = _parse_decimal(target_raw, "Miqdar")
        if target_value % 1 != 0:
            raise ValueError("Alətlər üçün miqdar tam ədəd olmalıdır.")
        tool_qs = Tool.objects.filter(created_by=user, item_id=update_id)
        current_total = sum(int(t.quantity) for t in tool_qs)
        delta = int(target_value) - current_total
        if delta != 0:
            return Tool.objects.create(item_id=update_id, quantity=delta, price=0, additional_info=note, created_by=user)
        return None

    if update_type == "tool_other":
        target_value = _parse_decimal(target_raw, "Miqdar")
        if target_value % 1 != 0:
            raise ValueError("Alətlər üçün miqdar tam ədəd olmalıdır.")
        tool_qs = Tool.objects.filter(created_by=user, manual_name=update_id).filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        current_total = sum(int(t.quantity) for t in tool_qs)
        delta = int(target_value) - current_total
        if delta != 0:
            return Tool.objects.create(item=None, manual_name=update_id, quantity=delta, price=0, additional_info=note, created_by=user)
        return None

    if update_type == "farm_product":
        target_value = _parse_decimal(target_raw, "Miqdar")
        unit_key = None
        item_id = update_id
        if "||" in str(update_id):
            item_id, unit_key = str(update_id).rsplit("||", 1)
        product_qs = FarmProduct.objects.filter(created_by=user, item_id=item_id)
        item = FarmProductItem.objects.filter(id=item_id).first()
        if not item:
            raise ValueError("Məhsul tapılmadı.")
        base_unit = item.unit or "kq"
        if unit_key:
            product_qs = product_qs.filter(unit=unit_key)
            if unit_key == "bağlama":
                base_unit = "bağlama"
        current_total = Decimal("0")
        for product in product_qs:
            current_total += _convert_farm_qty(Decimal(product.quantity), product.unit, base_unit)
        unit_value = unit_key or base_unit
        delta = target_value - current_total
        if delta != 0:
            return FarmProduct.objects.create(item_id=item_id, quantity=delta, unit=unit_value, price=0, additional_info=note, created_by=user)
        return None

    if update_type == "farm_product_other":
        target_value = _parse_decimal(target_raw, "Miqdar")
        if "||" not in str(update_id):
            raise ValueError("Məlumatlar natamamdır.")
        name_key, unit_key = str(update_id).rsplit("||", 1)
        product_qs = FarmProduct.objects.filter(created_by=user).filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"), manual_name=name_key, unit=unit_key)
        current_total = Decimal("0")
        for product in product_qs:
            current_total += Decimal(product.quantity)
        delta = target_value - current_total
        if delta != 0:
            return FarmProduct.objects.create(item=None, manual_name=name_key, quantity=delta, unit=unit_key, price=0, additional_info=note, created_by=user)
        return None

    if update_type in {"animal_sub", "animal_other"}:
        male_target = _parse_int(data.get("male_target"), "Miqdar", default=0)
        female_target = _parse_int(data.get("female_target"), "Miqdar", default=0)
        if update_type == "animal_sub":
            animals_qs = Animal.objects.filter(created_by=user, subcategory_id=update_id).exclude(quantity=0)
        else:
            animals_qs = Animal.objects.filter(created_by=user, manual_name=update_id).exclude(quantity=0).filter(Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər"))

        current_male = sum(int(getattr(a, "quantity", 1) or 1) for a in animals_qs.filter(gender="erkek"))
        current_female = sum(int(getattr(a, "quantity", 1) or 1) for a in animals_qs.filter(gender="disi"))
        male_delta = male_target - current_male
        female_delta = female_target - current_female

        created_any = None

        def create_animals(count, gender_value):
            nonlocal created_any
            if count <= 0:
                return
            payload = {"gender": gender_value, "additional_info": note, "created_by": user, "quantity": count}
            if update_type == "animal_sub":
                payload["subcategory_id"] = update_id
            else:
                payload["subcategory"] = None
                payload["manual_name"] = update_id
            created_any = Animal.objects.create(**payload)

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

        def add_negative_entry(count, gender_value):
            nonlocal created_any
            if count <= 0:
                return
            payload = {"gender": gender_value, "quantity": -abs(int(count)), "additional_info": "Stok azaldı", "created_by": user}
            if update_type == "animal_sub":
                payload["subcategory_id"] = update_id
            else:
                payload["subcategory"] = None
                payload["manual_name"] = update_id
            created_any = Animal.objects.create(**payload)

        if male_delta > 0:
            create_animals(male_delta, "erkek")
        elif male_delta < 0:
            disable_animals(abs(male_delta), "erkek")
            add_negative_entry(abs(male_delta), "erkek")
        if female_delta > 0:
            create_animals(female_delta, "disi")
        elif female_delta < 0:
            disable_animals(abs(female_delta), "disi")
            add_negative_entry(abs(female_delta), "disi")
        return created_any

    raise ValueError("Bu kateqoriya üçün yeniləmə dəstəklənmir.")


PROCESSORS = {
    ("seed", "create"): _create_seed,
    ("seed", "update"): _update_seed,
    ("seed", "delete"): _delete_seed,
    ("tool", "create"): _create_tool,
    ("tool", "update"): _update_tool,
    ("tool", "delete"): _delete_tool,
    ("animal", "create"): _create_animal,
    ("animal", "update"): _update_animal,
    ("animal", "delete"): _delete_animal,
    ("expense", "create"): _create_expense,
    ("expense", "update"): _update_expense,
    ("expense", "delete"): _delete_expense,
    ("supplier", "create"): _create_supplier,
    ("supplier", "update"): _update_supplier,
    ("supplier", "delete"): _delete_supplier,
    ("income", "create"): _create_income,
    ("income", "update"): _update_income,
    ("income", "delete"): _delete_income,
    ("farm_product", "create"): _create_farm_product,
    ("farm_product", "update"): _update_farm_product,
    ("farm_product", "delete"): _delete_farm_product,
    ("quick_expense", "quick_add"): _create_quick_expense,
    ("quick_expense", "custom_amount"): _create_quick_expense,
    ("quick_expense", "template_add"): _create_quick_expense,
    ("quick_income", "quick_add"): _create_quick_income,
    ("quick_income", "custom_amount"): _create_quick_income,
    ("quick_income", "template_add"): _create_quick_income,
    ("stock", "update"): _update_stock,
}


def _sync_result_metadata(result):
    if result is None:
        return "", None
    if hasattr(result, "_meta") and hasattr(result, "pk"):
        return result._meta.label_lower, result.pk
    if isinstance(result, int):
        return "", result
    return "", None


def _latest_change_for_model(model, user):
    updated_field = "updated_at" if any(field.name == "updated_at" for field in model._meta.fields) else "created_at"
    return model.objects.filter(created_by=user).order_by(f"-{updated_field}").values_list(updated_field, flat=True).first()


def _count_changes_for_model(model, user, since_dt):
    updated_field = "updated_at" if any(field.name == "updated_at" for field in model._meta.fields) else "created_at"
    filter_kwargs = {f"{updated_field}__gt": since_dt} if since_dt else {}
    return model.objects.filter(created_by=user, **filter_kwargs).count()


@login_required
def sync_page(request):
    return render(request, "sync/sync_page.html")


@login_required
@require_GET
def sync_status(request):
    device_id = _blank_to_none(request.GET.get("device_id"))
    state = None
    if device_id:
        state = DeviceSyncState.objects.filter(user=request.user, device_id=device_id).first()

    latest_cursor = None
    for model in SYNC_MODELS.values():
        candidate = _latest_change_for_model(model, request.user)
        if candidate and (latest_cursor is None or candidate > latest_cursor):
            latest_cursor = candidate

    return JsonResponse(
        {
            "device_id": device_id,
            "last_sync": state.last_synced_at.isoformat() if state and state.last_synced_at else None,
            "last_error": state.last_error if state else "",
            "latest_cursor": latest_cursor.isoformat() if latest_cursor else None,
            "server_time": timezone.now().isoformat(),
        }
    )


@login_required
@require_GET
def sync_pull_status(request):
    since_dt = _parse_datetime(request.GET.get("since"))
    device_id = _blank_to_none(request.GET.get("device_id"))
    operations = SyncOperation.objects.filter(
        user=request.user,
        status=SyncOperation.STATUS_COMPLETED,
    )

    if device_id:
        operations = operations.exclude(device_id=device_id)

    if since_dt:
        operations = operations.filter(processed_at__gt=since_dt)

    changes = {key: 0 for key in SYNC_MODELS.keys()}
    for entity_type in operations.values_list("entity_type", flat=True):
        if entity_type in changes:
            changes[entity_type] += 1

    total_changes = sum(changes.values())
    latest_operation = operations.order_by("-processed_at", "-received_at").first()
    latest_cursor = latest_operation.processed_at or latest_operation.received_at if latest_operation else None
    return JsonResponse(
        {
            "has_changes": total_changes > 0,
            "total_changes": total_changes,
            "changes": changes,
            "latest_cursor": latest_cursor.isoformat() if latest_cursor else None,
        }
    )


@login_required
@require_POST
def sync_push(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON düzgün deyil."}, status=400)

    device_id = _blank_to_none(payload.get("device_id"))
    operations = payload.get("operations") or []
    if not device_id:
        return JsonResponse({"error": "device_id tələb olunur."}, status=400)
    if not isinstance(operations, list):
        return JsonResponse({"error": "operations list olmalıdır."}, status=400)

    state, _ = DeviceSyncState.objects.get_or_create(user=request.user, device_id=device_id)
    results = []
    first_error = ""
    synced_any = False

    for operation in operations:
        operation_id = _blank_to_none(operation.get("id"))
        entity = _blank_to_none(operation.get("entity"))
        action = _blank_to_none(operation.get("action"))
        data = operation.get("data") or {}

        if not operation_id or not entity or not action:
            results.append(
                {
                    "id": operation.get("id"),
                    "status": "failed",
                    "error": "Operation məlumatı natamamdır.",
                }
            )
            if not first_error:
                first_error = "Operation məlumatı natamamdır."
            continue

        sync_operation, created = SyncOperation.objects.get_or_create(
            user=request.user,
            device_id=device_id,
            operation_id=operation_id,
            defaults={
                "entity_type": entity,
                "action": action,
                "status": SyncOperation.STATUS_PENDING,
            },
        )

        if not created and sync_operation.status == SyncOperation.STATUS_COMPLETED:
            results.append(
                {
                    "id": operation_id,
                    "status": "completed",
                    "target_model": sync_operation.target_model,
                    "target_id": sync_operation.target_object_id,
                    "deduplicated": True,
                }
            )
            synced_any = True
            continue

        processor = PROCESSORS.get((entity, action))
        if not processor:
            message = "Bu sync əməliyyatı dəstəklənmir."
            sync_operation.status = SyncOperation.STATUS_FAILED
            sync_operation.error_message = message
            sync_operation.processed_at = timezone.now()
            sync_operation.save(update_fields=["status", "error_message", "processed_at"])
            results.append({"id": operation_id, "status": "failed", "error": message})
            if not first_error:
                first_error = message
            continue

        try:
            with transaction.atomic():
                created_object = processor(request.user, data)
        except ValueError as exc:
            message = str(exc)
            sync_operation.status = SyncOperation.STATUS_FAILED
            sync_operation.error_message = message
            sync_operation.processed_at = timezone.now()
            sync_operation.save(update_fields=["status", "error_message", "processed_at"])
            results.append({"id": operation_id, "status": "failed", "error": message})
            if not first_error:
                first_error = message
            continue
        except Exception as exc:
            message = f"Gözlənilməz sync xətası: {exc}"
            print("SYNC PUSH ERROR", operation_id, entity, action)
            traceback.print_exc()
            sync_operation.status = SyncOperation.STATUS_FAILED
            sync_operation.error_message = message
            sync_operation.processed_at = timezone.now()
            sync_operation.save(update_fields=["status", "error_message", "processed_at"])
            results.append({"id": operation_id, "status": "failed", "error": message})
            if not first_error:
                first_error = message
            continue

        target_model, target_id = _sync_result_metadata(created_object)

        sync_operation.entity_type = entity
        sync_operation.action = action
        sync_operation.status = SyncOperation.STATUS_COMPLETED
        sync_operation.error_message = ""
        sync_operation.target_model = target_model
        sync_operation.target_object_id = target_id
        sync_operation.processed_at = timezone.now()
        sync_operation.save(
            update_fields=[
                "entity_type",
                "action",
                "status",
                "error_message",
                "target_model",
                "target_object_id",
                "processed_at",
            ]
        )
        synced_any = True
        results.append(
            {
                "id": operation_id,
                "status": "completed",
                "target_model": target_model,
                "target_id": target_id,
            }
        )

    if synced_any:
        state.last_synced_at = timezone.now()
    state.last_error = first_error
    state.save(update_fields=["last_synced_at", "last_error", "updated_at"])

    return JsonResponse(
        {
            "results": results,
            "last_sync": state.last_synced_at.isoformat() if state.last_synced_at else None,
            "last_error": state.last_error,
        }
    )

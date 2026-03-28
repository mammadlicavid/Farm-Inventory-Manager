import hashlib
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.http import HttpResponse
from django.db.models import Case, DecimalField, F, IntegerField, Q, Sum, Value, When
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render
from django.utils import timezone

from expenses.models import ExpenseCategory
from incomes.views import _build_category_payload

from .models import ScanItem, UserBarcode

from common.icons import get_animal_icon_by_name, get_seed_icon_by_name, get_tool_icon_by_name, get_farm_product_icon_by_name
from common.messages import add_crud_success_message
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
from animals.models import Animal, AnimalCategory, AnimalSubCategory
from farm_products.models import FarmProduct, FarmProductCategory, FarmProductItem
from seeds.models import Seed, SeedCategory, SeedItem
from tools.models import Tool, ToolCategory, ToolItem

ADD_PAGE_CATALOG_CACHE_KEY = "inventory:add-page-catalog:v1"
ADD_PAGE_CATALOG_CACHE_TTL = 300
STOCKS_PAGE_CACHE_TTL = 20


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
        return [_normalized_metadata(item) for item in value if _normalized_metadata(item) not in ("", None, [], {})]
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


def _build_add_page_catalog():
    cached = cache.get(ADD_PAGE_CATALOG_CACHE_KEY)
    if cached is not None:
        return cached

    expense_categories = []
    for category in ExpenseCategory.objects.exclude(name="Maliyyə və Digər").prefetch_related("subcategories"):
        expense_categories.append(
            {
                "id": category.id,
                "name": category.name,
                "subcategories": _unique_rows([
                    {"id": sub.id, "name": sub.name}
                    for sub in category.subcategories.all()
                ]),
            }
        )
    expense_categories = _unique_rows(expense_categories)

    animal_categories = []
    for category in order_queryset_by_name_list(AnimalCategory.objects.all(), ANIMAL_CATEGORY_ORDER).prefetch_related("subcategories"):
        ordered_subcategories = order_queryset_by_name_list(
            category.subcategories.all(),
            ANIMAL_SUBCATEGORY_ORDER.get(category.name, []),
        )
        animal_categories.append(
            {
                "id": category.id,
                "name": category.name,
                "subcategories": _unique_rows([
                    {"id": sub.id, "name": sub.name}
                    for sub in ordered_subcategories
                ]),
            }
        )
    animal_categories = _unique_rows(animal_categories)

    seed_categories = []
    for category in order_queryset_by_name_list(SeedCategory.objects.all(), SEED_CATEGORY_ORDER).prefetch_related("items"):
        ordered_items = order_queryset_by_name_list(
            category.items.all(),
            SEED_ITEM_ORDER.get(category.name, []),
        )
        seed_categories.append(
            {
                "id": category.id,
                "name": category.name,
                "items": _unique_rows([
                    {"id": item.id, "name": item.name}
                    for item in ordered_items
                ]),
            }
        )
    seed_categories = _unique_rows(seed_categories)

    tool_categories = []
    for category in order_queryset_by_name_list(ToolCategory.objects.all(), TOOL_CATEGORY_ORDER).prefetch_related("items"):
        ordered_items = order_queryset_by_name_list(
            category.items.all(),
            TOOL_ITEM_ORDER.get(category.name, []),
        )
        tool_categories.append(
            {
                "id": category.id,
                "name": category.name,
                "items": _unique_rows([
                    {"id": item.id, "name": item.name}
                    for item in ordered_items
                ]),
            }
        )
    tool_categories = _unique_rows(tool_categories)

    farm_categories = []
    for category in order_queryset_by_name_list(FarmProductCategory.objects.all(), FARM_PRODUCT_CATEGORY_ORDER).prefetch_related("items"):
        ordered_items = order_queryset_by_name_list(
            category.items.all(),
            FARM_PRODUCT_ITEM_ORDER.get(category.name, []),
        )
        farm_categories.append(
            {
                "id": category.id,
                "name": category.name,
                "items": _unique_rows([
                    {"id": item.id, "name": item.name, "unit": item.unit or ""}
                    for item in ordered_items
                ]),
            }
        )
    farm_categories = _unique_rows(farm_categories)

    income_categories, income_category_data = _build_category_payload()
    income_categories = _unique_rows([{"name": name} for name in income_categories])
    income_categories = [row["name"] for row in income_categories]
    form_types = [
        {"key": "seed", "label": "Toxum"},
        {"key": "animal", "label": "Heyvan"},
        {"key": "tool", "label": "Alət"},
        {"key": "farm", "label": "Təsərrüfat Məhsulları"},
        {"key": "expense", "label": "Xərclər"},
        {"key": "income", "label": "Gəlirlər"},
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
    cache.set(ADD_PAGE_CATALOG_CACHE_KEY, payload, ADD_PAGE_CATALOG_CACHE_TTL)
    return payload


def _build_add_page_context():
    return {
        "today": timezone.now().date(),
        **_build_add_page_catalog(),
    }

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
    cache_key = f"inventory:stocks-page:v3:user:{user.id}"
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

    # Seeds (only item-based, not manual "Digər")
    seed_total_expr = Sum(
        Case(
            When(unit="kg", then=F("quantity")),
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
                "unit": "kg",
                "icon": get_seed_icon_by_name(payload["name"]),
                "update_type": "seed",
                "update_id": item_id,
                "input_step": "0.01",
            }
        )

    # Tools (only item-based, not manual "Digər")
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

    # Animals (sum quantity by subcategory)
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

    # Digər (manual entries)
    # Seeds manual
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
                "unit": "kg",
                "icon": get_seed_icon_by_name(payload["name"]),
                "update_type": "seed_other",
                "update_id": name,
                "input_step": "0.01",
            }
        )

    # Tools manual
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

    # Animals manual
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

    # Farm products (item-based)
    farm_totals = {}
    farm_qs = (
        FarmProduct.objects.filter(created_by=user, item__isnull=False)
        .select_related("item", "item__category")
        .only(
            "id",
            "quantity",
            "unit",
            "item_id",
            "item__name",
            "item__unit",
            "item__category_id",
            "item__category__name",
        )
    )
    for product in farm_qs:
        if not product.item:
            continue
        if (product.item.name or "").strip().lower() == "digər":
            continue
        is_forage = _is_forage_item(product.item.name)
        if is_forage and product.unit == "bağlama":
            base_unit = "bağlama"
        elif product.unit in {"kq", "ton", "qram"}:
            base_unit = "kq"
        elif product.unit in {"litr", "ml"}:
            base_unit = "litr"
        else:
            base_unit = product.unit

        key = (product.item_id, product.unit) if base_unit == "bağlama" else (product.item_id, "base")
        payload = farm_totals.setdefault(
            key,
            {
                "name": product.item.name,
                "category_id": product.item.category_id,
                "category_name": product.item.category.name if product.item.category else "",
                "total_qty": Decimal("0"),
                "unit": product.unit if base_unit == "bağlama" else (product.item.unit or product.unit),
                "base_unit": base_unit,
            },
        )
        payload["total_qty"] += _convert_farm_qty(Decimal(product.quantity), product.unit, payload["base_unit"])

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

    # Farm products manual (Digər)
    farm_other_totals = {}
    farm_other_qs = (
        FarmProduct.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        .exclude(manual_name__isnull=True)
        .exclude(manual_name="")
        .exclude(manual_name__iexact="Digər")
    )
    for product in farm_other_qs:
        name_key = product.manual_name.strip()
        unit_key = product.unit or ""
        key = f"{name_key}||{unit_key}"
        payload = farm_other_totals.setdefault(
            key,
            {
                "name": name_key,
                "unit": unit_key,
                "total_qty": Decimal("0"),
            },
        )
        payload["total_qty"] += Decimal(product.quantity)

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

    context = {
        "seed_categories": seed_categories,
        "tool_categories": tool_categories,
        "animal_categories": animal_categories,
        "farm_product_categories": farm_product_categories,
        "items": sorted(
            items,
            key=lambda item: (
                1 if Decimal(str(item["quantity"])) == 0 else 0,
                {"toxumlar": 0, "aletler": 1, "heyvanlar": 2, "teserrufat": 3, "diger": 4}.get(item["main"], 9),
                (item.get("subtitle") or "").lower(),
                (item.get("title") or "").lower(),
            ),
        ),
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
        messages.error(request, "Məlumatlar natamamdır.")
        return redirect("inventory:stocks")

    try:
        target_value = Decimal(str(target_raw))
    except Exception:
        messages.error(request, "Miqdar düzgün deyil.")
        return redirect("inventory:stocks")

    note = "Stok səhifəsindən düzəliş"

    if update_type == "seed":
        seed_qs = Seed.objects.filter(created_by=request.user, item_id=update_id)
        current_total = Decimal("0")
        for seed in seed_qs:
            if seed.unit == "kg":
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
            if seed.unit == "kg":
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
            messages.error(request, "Alətlər üçün miqdar tam ədəd olmalıdır.")
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
            messages.error(request, "Alətlər üçün miqdar tam ədəd olmalıdır.")
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
            messages.error(request, "Məhsul tapılmadı.")
            return redirect("inventory:stocks")

        is_forage = _is_forage_item(item.name)
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
            messages.error(request, "Məlumatlar natamamdır.")
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
            messages.error(request, "Məlumatlar natamamdır.")
            return redirect("inventory:stocks")

        try:
            male_target = int(male_raw)
            female_target = int(female_raw)
        except Exception:
            messages.error(request, "Heyvanlar üçün miqdar tam ədəd olmalıdır.")
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

        def add_negative_entry(count, gender_value):
            if count <= 0:
                return
            payload = {
                "gender": gender_value,
                "quantity": -abs(int(count)),
                "additional_info": "Stok azaldı",
                "created_by": request.user,
            }
            if update_type == "animal_sub":
                payload["subcategory_id"] = update_id
            else:
                payload["subcategory"] = None
                payload["manual_name"] = update_id
            Animal.objects.create(**payload)

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

        if male_delta != 0 or female_delta != 0:
            add_crud_success_message(request, "Animal", "update")
        return redirect("inventory:stocks")

    messages.error(request, "Bu kateqoriya üçün yeniləmə dəstəklənmir.")
    return redirect("inventory:stocks")

@login_required
def add_product(request):
    return render(request, "inventory/add_product.html", _build_add_page_context())


@login_required
def barcode_builder(request):
    return render(request, "inventory/barcode_builder.html", _build_add_page_context())

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

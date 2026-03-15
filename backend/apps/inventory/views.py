from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from .models import ScanItem

from common.icons import get_animal_icon_by_name, get_seed_icon_by_name, get_tool_icon_by_name, get_farm_product_icon_by_name
from common.messages import add_crud_success_message
from common.category_order import (
    ANIMAL_CATEGORY_ORDER,
    FARM_PRODUCT_CATEGORY_ORDER,
    SEED_CATEGORY_ORDER,
    TOOL_CATEGORY_ORDER,
    order_queryset_by_name_list,
)
from animals.models import Animal, AnimalCategory, AnimalSubCategory
from farm_products.models import FarmProduct, FarmProductCategory, FarmProductItem
from seeds.models import Seed, SeedCategory, SeedItem
from tools.models import Tool, ToolCategory, ToolItem


def _is_forage_item(name: str) -> bool:
    return (name or "").strip().lower() in {"yonca", "koronilla", "seradella"}

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

    seed_categories = list(order_queryset_by_name_list(SeedCategory.objects.all(), SEED_CATEGORY_ORDER))
    tool_categories = list(order_queryset_by_name_list(ToolCategory.objects.all(), TOOL_CATEGORY_ORDER))
    animal_categories = list(order_queryset_by_name_list(AnimalCategory.objects.all(), ANIMAL_CATEGORY_ORDER))
    farm_product_categories = list(
        order_queryset_by_name_list(FarmProductCategory.objects.all(), FARM_PRODUCT_CATEGORY_ORDER)
    )
    farm_diger_category_id = next((cat.id for cat in farm_product_categories if cat.name == "Digər"), None)

    def to_kg(quantity: Decimal, unit: str) -> Decimal:
        if unit == "kg":
            return quantity
        if unit == "ton":
            return quantity * Decimal("1000")
        if unit == "qram":
            return quantity / Decimal("1000")
        return quantity

    items = []

    # Seeds (only item-based, not manual "Digər")
    seed_totals = {}
    seed_qs = (
        Seed.objects.filter(created_by=user, item__isnull=False)
        .select_related("item", "item__category")
    )
    for seed in seed_qs:
        if not seed.item:
            continue
        if (seed.item.name or "").strip().lower() == "digər":
            continue
        key = seed.item_id
        payload = seed_totals.setdefault(
            key,
            {
                "name": seed.item.name,
                "category_id": seed.item.category_id,
                "category_name": seed.item.category.name if seed.item.category else "",
                "total_kg": Decimal("0"),
            },
        )
        payload["total_kg"] += to_kg(Decimal(seed.quantity), seed.unit)

    seed_items = SeedItem.objects.select_related("category").exclude(name__iexact="Digər")
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
    tool_totals = {}
    tool_qs = (
        Tool.objects.filter(created_by=user, item__isnull=False)
        .select_related("item", "item__category")
    )
    for tool in tool_qs:
        if not tool.item:
            continue
        if (tool.item.name or "").strip().lower() == "digər":
            continue
        key = tool.item_id
        payload = tool_totals.setdefault(
            key,
            {
                "name": tool.item.name,
                "category_id": tool.item.category_id,
                "category_name": tool.item.category.name if tool.item.category else "",
                "total_qty": 0,
            },
        )
        payload["total_qty"] += int(tool.quantity)

    tool_items = ToolItem.objects.select_related("category").exclude(name__iexact="Digər")
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
    animal_totals = {}
    animal_qs = (
        Animal.objects.filter(created_by=user, subcategory__isnull=False)
        .exclude(quantity=0)
        .select_related("subcategory", "subcategory__category")
    )
    for animal in animal_qs:
        if not animal.subcategory:
            continue
        if (animal.subcategory.name or "").strip().lower() == "digər":
            continue
        key = animal.subcategory_id
        payload = animal_totals.setdefault(
            key,
            {
                "name": animal.subcategory.name,
                "category_id": animal.subcategory.category_id,
                "category_name": animal.subcategory.category.name if animal.subcategory.category else "",
                "total_qty": 0,
                "male_qty": 0,
                "female_qty": 0,
            },
        )
        qty_val = int(getattr(animal, "quantity", 1) or 1)
        payload["total_qty"] += qty_val
        if animal.gender == "erkek":
            payload["male_qty"] += qty_val
        elif animal.gender == "disi":
            payload["female_qty"] += qty_val

    animal_subs = AnimalSubCategory.objects.select_related("category").exclude(name__iexact="Digər")
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
    seed_other_totals = {}
    seed_other_qs = (
        Seed.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        .exclude(manual_name__isnull=True)
        .exclude(manual_name="")
        .exclude(manual_name__iexact="Digər")
    )
    for seed in seed_other_qs:
        key = seed.manual_name.strip()
        payload = seed_other_totals.setdefault(
            key,
            {
                "name": seed.manual_name.strip(),
                "total_kg": Decimal("0"),
            },
        )
        payload["total_kg"] += to_kg(Decimal(seed.quantity), seed.unit)

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
    tool_other_totals = {}
    tool_other_qs = (
        Tool.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        .exclude(manual_name__isnull=True)
        .exclude(manual_name="")
        .exclude(manual_name__iexact="Digər")
    )
    for tool in tool_other_qs:
        key = tool.manual_name.strip()
        payload = tool_other_totals.setdefault(
            key,
            {
                "name": tool.manual_name.strip(),
                "total_qty": 0,
            },
        )
        payload["total_qty"] += int(tool.quantity)

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
    animal_other_totals = {}
    animal_other_qs = (
        Animal.objects.filter(created_by=user)
        .exclude(quantity=0)
        .filter(Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər"))
        .exclude(manual_name__isnull=True)
        .exclude(manual_name="")
        .exclude(manual_name__iexact="Digər")
    )
    for animal in animal_other_qs:
        key = animal.manual_name.strip()
        payload = animal_other_totals.setdefault(
            key,
            {
                "name": animal.manual_name.strip(),
                "total_qty": 0,
                "male_qty": 0,
                "female_qty": 0,
            },
        )
        qty_val = int(getattr(animal, "quantity", 1) or 1)
        payload["total_qty"] += qty_val
        if animal.gender == "erkek":
            payload["male_qty"] += qty_val
        elif animal.gender == "disi":
            payload["female_qty"] += qty_val

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

    farm_items = FarmProductItem.objects.select_related("category").exclude(name__iexact="Digər")
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
    return render(request, "inventory/stocks.html", context)


@login_required
def update_stock_quantity(request):
    if request.method != "POST":
        return redirect("inventory:stocks")

    update_type = request.POST.get("update_type")
    update_id = request.POST.get("update_id")
    target_raw = request.POST.get("target_quantity")

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
    return render(request, "inventory/add_product.html", {"today": timezone.now().date()})

@login_required
def lookup_scan_code(request):
    code = request.GET.get("code", "").strip()

    if not code:
        return JsonResponse({"success": False, "message": "Kod göndərilməyib."}, status=400)

    try:
        item = ScanItem.objects.get(code=code, is_active=True)
    except ScanItem.DoesNotExist:
        return JsonResponse({"success": False, "message": "Kod tapılmadı."}, status=404)

    return JsonResponse({
        "success": True,
        "item": {
            "code": item.code,
            "name": item.name,
            "category": item.category,
            "unit": item.unit or "",
            "default_price": str(item.default_price),
        }
    })
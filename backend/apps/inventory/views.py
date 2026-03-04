from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.db.models import Case, IntegerField, When

from common.icons import get_animal_icon_by_name, get_seed_icon_by_name, get_tool_icon_by_name
from common.messages import add_crud_success_message
from animals.models import Animal, AnimalCategory, AnimalSubCategory
from seeds.models import Seed, SeedCategory, SeedItem
from tools.models import Tool, ToolCategory, ToolItem

def home(request):
    return HttpResponse("Home page")

@login_required
def dashboard(request):
    return HttpResponse("Dashboard ✅ You are logged in.")

@login_required
def products_placeholder(request):
    user = request.user

    category_order = Case(
        When(name="Digər", then=1),
        default=0,
        output_field=IntegerField(),
    )
    seed_categories = list(SeedCategory.objects.all().order_by(category_order, "name"))
    tool_categories = list(ToolCategory.objects.all().order_by(category_order, "name"))
    animal_categories = list(AnimalCategory.objects.all().order_by(category_order, "name"))

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

    # Animals (count active by subcategory)
    animal_totals = {}
    animal_qs = (
        Animal.objects.filter(created_by=user, subcategory__isnull=False, status="aktiv")
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
        payload["total_qty"] += 1
        if animal.gender == "erkek":
            payload["male_qty"] += 1
        elif animal.gender == "disi":
            payload["female_qty"] += 1

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
        Seed.objects.filter(created_by=user, item__isnull=True)
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
        Tool.objects.filter(created_by=user, item__isnull=True)
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
        Animal.objects.filter(created_by=user, subcategory__isnull=True, status="aktiv")
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
        payload["total_qty"] += 1
        if animal.gender == "erkek":
            payload["male_qty"] += 1
        elif animal.gender == "disi":
            payload["female_qty"] += 1

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

    context = {
        "seed_categories": seed_categories,
        "tool_categories": tool_categories,
        "animal_categories": animal_categories,
        "items": sorted(
            items,
            key=lambda item: (
                1 if Decimal(str(item["quantity"])) == 0 else 0,
                {"toxumlar": 0, "aletler": 1, "heyvanlar": 2, "diger": 3}.get(item["main"], 9),
                (item.get("subtitle") or "").lower(),
                (item.get("title") or "").lower(),
            ),
        ),
    }
    return render(request, "inventory/products.html", context)


@login_required
def update_product_quantity(request):
    if request.method != "POST":
        return redirect("inventory:products")

    update_type = request.POST.get("update_type")
    update_id = request.POST.get("update_id")
    target_raw = request.POST.get("target_quantity")

    if not update_type or not update_id or target_raw is None:
        messages.error(request, "Məlumatlar natamamdır.")
        return redirect("inventory:products")

    try:
        target_value = Decimal(str(target_raw))
    except Exception:
        messages.error(request, "Miqdar düzgün deyil.")
        return redirect("inventory:products")

    note = "Məhsullar səhifəsindən düzəliş"

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
        return redirect("inventory:products")

    if update_type == "seed_other":
        seed_qs = Seed.objects.filter(created_by=request.user, item__isnull=True, manual_name=update_id)
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
        return redirect("inventory:products")

    if update_type == "tool":
        tool_qs = Tool.objects.filter(created_by=request.user, item_id=update_id)
        if target_value % 1 != 0:
            messages.error(request, "Alətlər üçün miqdar tam ədəd olmalıdır.")
            return redirect("inventory:products")
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
        return redirect("inventory:products")

    if update_type == "tool_other":
        tool_qs = Tool.objects.filter(created_by=request.user, item__isnull=True, manual_name=update_id)
        if target_value % 1 != 0:
            messages.error(request, "Alətlər üçün miqdar tam ədəd olmalıdır.")
            return redirect("inventory:products")
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
        return redirect("inventory:products")

    if update_type in {"animal_sub", "animal_other"}:
        male_raw = request.POST.get("male_target")
        female_raw = request.POST.get("female_target")
        if male_raw is None or female_raw is None:
            messages.error(request, "Məlumatlar natamamdır.")
            return redirect("inventory:products")

        try:
            male_target = int(male_raw)
            female_target = int(female_raw)
        except Exception:
            messages.error(request, "Heyvanlar üçün miqdar tam ədəd olmalıdır.")
            return redirect("inventory:products")

        if update_type == "animal_sub":
            animals_qs = Animal.objects.filter(
                created_by=request.user,
                subcategory_id=update_id,
                status="aktiv",
            )
        else:
            animals_qs = Animal.objects.filter(
                created_by=request.user,
                subcategory__isnull=True,
                manual_name=update_id,
                status="aktiv",
            )

        current_male = animals_qs.filter(gender="erkek").count()
        current_female = animals_qs.filter(gender="disi").count()

        male_delta = male_target - current_male
        female_delta = female_target - current_female

        def create_animals(count, gender_value):
            if count <= 0:
                return
            new_animals = []
            for _ in range(count):
                if update_type == "animal_sub":
                    new_animals.append(
                        Animal(
                            subcategory_id=update_id,
                            gender=gender_value,
                            additional_info=note,
                            created_by=request.user,
                        )
                    )
                else:
                    new_animals.append(
                        Animal(
                            subcategory=None,
                            manual_name=update_id,
                            gender=gender_value,
                            additional_info=note,
                            created_by=request.user,
                        )
                    )
            Animal.objects.bulk_create(new_animals)

        def disable_animals(count, gender_value):
            if count <= 0:
                return
            to_disable_ids = list(
                animals_qs.filter(gender=gender_value).order_by("-created_at").values_list("id", flat=True)[:count]
            )
            if to_disable_ids:
                Animal.objects.filter(id__in=to_disable_ids).update(status="satilib")

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
        return redirect("inventory:products")

    messages.error(request, "Bu kateqoriya üçün yeniləmə dəstəklənmir.")
    return redirect("inventory:products")

@login_required
def add_product(request):
    return render(request, "inventory/add_product.html")

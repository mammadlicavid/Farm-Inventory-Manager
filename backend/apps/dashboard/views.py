from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from seeds.models import Seed
from animals.models import Animal, AnimalCategory, AnimalSubCategory
from tools.models import Tool
from expenses.models import Expense
from incomes.models import Income
from django.db.models import Sum
from common.formatting import format_currency

@login_required
def dashboard(request):
    now = timezone.localtime(timezone.now())
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    new_stocks = (
        Seed.objects.filter(created_by=request.user, created_at__gte=start_of_week).count()
        + Animal.objects.filter(created_by=request.user, created_at__gte=start_of_week).count()
        + Tool.objects.filter(created_by=request.user, created_at__gte=start_of_week).count()
    )

    weekly_expenses = (
        Expense.objects.filter(created_by=request.user, created_at__gte=start_of_week)
        .aggregate(Sum("amount"))
        .get("amount__sum")
        or 0
    )
    weekly_income = (
        Income.objects.filter(created_by=request.user, created_at__gte=start_of_week)
        .aggregate(Sum("amount"))
        .get("amount__sum")
        or 0
    )
    weekly_net = weekly_income - weekly_expenses
    display_name = (request.user.first_name or "").strip() or request.user.get_username()

    # Dynamic data for Low Stock Alerts (Ehtiyat Xəbərdarlığı)
    from farm_products.models import FarmProduct
    low_stock_alerts = []

    def add_alert(name, total, unit, icon, critical_threshold, warning_threshold, max_val_base):
        if total <= warning_threshold:
            status = "kritik" if total <= critical_threshold else "az"
            max_val = max(max_val_base, int(total) + (20 if status == 'az' else 10))
            percentage = 100 if max_val == 0 else int((total / max_val) * 100)
            low_stock_alerts.append({
                "name": name,
                "status": status,
                "status_text": "Kritik" if status == "kritik" else "Az qalıb",
                "current": int(total) if total == int(total) else float(total),
                "max": max_val,
                "unit": unit,
                "icon": icon,
                "color": "red" if status == "kritik" else "yellow",
                "percentage": percentage
            })

    # Seeds (Threshold 10/25)
    for row in Seed.objects.filter(created_by=request.user).values('item__name', 'manual_name').annotate(total=Sum('quantity')):
        name = row['item__name'] or row['manual_name'] or "Toxum"
        add_alert(name, row['total'] or 0, "kq", "fa-wheat-awn", 10, 25, 50)

    # Animals (Threshold 2/8)
    for row in Animal.objects.filter(created_by=request.user).values('subcategory__name', 'manual_name').annotate(total=Sum('quantity')):
        name = row['subcategory__name'] or row['manual_name'] or "Heyvan"
        add_alert(name, row['total'] or 0, "ədəd", "fa-cow", 2, 8, 20)

    # Tools (Threshold 2/5)
    for row in Tool.objects.filter(created_by=request.user).values('item__name', 'manual_name').annotate(total=Sum('quantity')):
        name = row['item__name'] or row['manual_name'] or "Alət"
        add_alert(name, row['total'] or 0, "ədəd", "fa-wrench", 2, 5, 10)

    # Farm Products (Threshold 15/40)
    for row in FarmProduct.objects.filter(created_by=request.user).values('item__name', 'manual_name', 'unit').annotate(total=Sum('quantity')):
        name = row['item__name'] or row['manual_name'] or "Məhsul"
        unit = row['unit'] or "kq"
        add_alert(name, row['total'] or 0, unit, "fa-box", 15, 40, 50)

    low_stock_alerts.sort(key=lambda x: (0 if x['status'] == 'kritik' else 1, x['percentage']))
    low_stock_alerts = low_stock_alerts[:4]

    # Fallback to display mock if completely empty so design can be seen by user when starting fresh
    if not low_stock_alerts:
        low_stock_alerts = [
            {
                "name": "Heyvan yemi (Nümunə)", "status": "az", "status_text": "Az qalıb", 
                "current": 15, "max": 50, "unit": "kq", "icon": "fa-seedling", "color": "yellow", "percentage": 30
            },
            {
                "name": "Dizel yanacaq (Nümunə)", "status": "az", "status_text": "Az qalıb", 
                "current": 8, "max": 20, "unit": "litr", "icon": "fa-gas-pump", "color": "yellow", "percentage": 40
            },
            {
                "name": "Arpa toxumu (Nümunə)", "status": "kritik", "status_text": "Kritik", 
                "current": 5, "max": 30, "unit": "kq", "icon": "fa-wheat-awn", "color": "red", "percentage": 16
            },
            {
                "name": "Baytarlıq dərmanı (Nümunə)", "status": "kritik", "status_text": "Kritik", 
                "current": 2, "max": 10, "unit": "ədəd", "icon": "fa-capsules", "color": "red", "percentage": 20
            }
        ]
    critical_count = sum(1 for item in low_stock_alerts if item["status"] == "kritik")

    context = {
        "user_name" : display_name,
        "stats" : {
            "new_addition": new_stocks,
            "weekly_net": weekly_net,
            "weekly_net_display": format_currency(weekly_net, 2),
            "animals": Animal.objects.filter(created_by=request.user, created_at__gte=start_of_week).count(),
        },
        "low_stock_alerts": low_stock_alerts,
        "critical_count": critical_count,
    }

    return render(request, "dashboard/index.html", context)


@login_required
def quick_expense(request):
    from expenses.models import Expense, ExpenseSubCategory
    from common.formatting import format_currency
    from django.contrib import messages as django_messages

    def _compact_number(value):
        try:
            return format_currency(value, 2).rstrip("0").rstrip(".")
        except Exception:
            return str(value)

    def _expense_template_measure(expense):
        linked = getattr(expense, "content_object", None)
        if linked is not None:
            quantity = getattr(linked, "quantity", None)
            unit = getattr(linked, "unit", None)
            if quantity is not None:
                return _compact_number(quantity), unit or "ədəd"

        raw = (expense.additional_info or "").strip()
        if raw.startswith("Miqdar:"):
            payload = raw.replace("Miqdar:", "", 1).strip()
            parts = payload.split()
            if len(parts) >= 2:
                return parts[0], " ".join(parts[1:])
            if payload:
                return payload, "ədəd"

        return "1", "ədəd"

    # Quick-tap preset items (name, icon, default amount, subcategory slug)
    QUICK_ITEMS = [
        {"name": "Yem", "icon": "🐄", "amount": 50, "quantity": 25, "unit": "kq"},
        {"name": "Yanacaq", "icon": "⛽", "amount": 80, "quantity": 20, "unit": "litr"},
        {"name": "Gübrə", "icon": "🪴", "amount": 120, "quantity": 10, "unit": "kq"},
        {"name": "Baytar", "icon": "💉", "amount": 1, "unit": "xidmət", "quantity": 1},
    ]

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "quick_add":
            name = request.POST.get("name", "")
            amount = request.POST.get("amount", "0")
            custom_amount = request.POST.get("custom_amount", "")
            try:
                amount_val = float(amount)
            except (ValueError, TypeError):
                amount_val = 0
            if custom_amount:
                try:
                    amount_val = float(custom_amount)
                except (ValueError, TypeError):
                    pass

            if amount_val > 0:
                # Try to find matching subcategory (prefer Heyvandarlıq for Gübrə)
                subcat_qs = ExpenseSubCategory.objects.filter(name__iexact=name).select_related("category")
                if name.lower() == "gübrə":
                    subcat = subcat_qs.filter(category__name="Heyvandarlıq").first() or subcat_qs.first()
                else:
                    subcat = subcat_qs.first()
                Expense.objects.create(
                    title=name,
                    amount=amount_val,
                    subcategory=subcat,
                    manual_name=name if not subcat else None,
                    created_by=request.user,
                )
                django_messages.success(request, f"{name} — {format_currency(amount_val, 0)}₼ əlavə edildi")

        elif action == "custom_amount":
            amount = request.POST.get("amount", "0")
            try:
                amount_val = float(amount)
            except (ValueError, TypeError):
                amount_val = 0

            if amount_val > 0:
                subcat = ExpenseSubCategory.objects.filter(name__iexact="Digər").select_related("category").first()
                Expense.objects.create(
                    title="Xüsusi xərc",
                    amount=amount_val,
                    subcategory=subcat,
                    manual_name=None,
                    created_by=request.user,
                )
                django_messages.success(request, f"Xüsusi xərc — {format_currency(amount_val, 0)}₼ əlavə edildi")

        elif action == "template_add":
            template_id = request.POST.get("template_id")
            custom_amount = request.POST.get("custom_amount", "")
            if template_id:
                try:
                    original = Expense.objects.get(pk=template_id, created_by=request.user)
                    amount_val = original.amount
                    if custom_amount:
                        try:
                            amount_val = float(custom_amount)
                        except (ValueError, TypeError):
                            amount_val = original.amount
                    Expense.objects.create(
                        title=original.title,
                        amount=amount_val,
                        subcategory=original.subcategory,
                        manual_name=original.manual_name,
                        created_by=request.user,
                    )
                    django_messages.success(request, f"{original.title} — {format_currency(amount_val, 0)}₼ əlavə edildi")
                except Expense.DoesNotExist:
                    pass

        return redirect("quick_expense")

    # GET — build context
    # Recent expenses as "templates" (last 10 unique by title)
    recent_expenses = (
        Expense.objects.filter(created_by=request.user)
        .select_related("subcategory", "subcategory__category")
        .order_by("-created_at")[:20]
    )
    subcat_lookup = {
        sc.name.lower(): sc
        for sc in ExpenseSubCategory.objects.select_related("category").all()
    }
    # Deduplicate by title, keep most recent
    seen_titles = set()
    templates = []
    for exp in recent_expenses:
        if exp.title not in seen_titles and len(templates) < 8:
            seen_titles.add(exp.title)
            exp.amount_display = format_currency(exp.amount, 2)
            exp.quantity_display, exp.unit_display = _expense_template_measure(exp)
            exp.display_title = exp.title
            if exp.title:
                title_stripped = exp.title.strip()
                if ":" in title_stripped:
                    base, rest = title_stripped.split(":", 1)
                    base = base.strip()
                    rest = rest.strip()
                    if base and rest and base.lower() in {
                        "heyvan alışı",
                        "toxum alışı",
                        "alət alışı",
                        "texnika alışı",
                    }:
                        exp.display_title = rest
            # Build tags
            tags = []
            if exp.subcategory:
                tags.append(exp.subcategory.name)
                if exp.subcategory.category:
                    tags.append(exp.subcategory.category.name)
            elif exp.manual_name:
                tags.append(exp.manual_name)
            exp.tags = tags
            def resolve_subcat(name: str):
                if not name:
                    return None
                return subcat_lookup.get(name.lower())

            sub_name = ""
            cat_name = ""
            if exp.subcategory:
                sub_name = exp.subcategory.name
                cat_name = exp.subcategory.category.name if exp.subcategory.category else ""
            else:
                # Try manual_name, then title as a fallback
                match = resolve_subcat(exp.manual_name) or resolve_subcat(exp.title)

                # Heuristics for common titles
                if not match and exp.title:
                    title_lower = exp.title.lower()
                    if title_lower.startswith("toxum alışı"):
                        match = resolve_subcat("Toxumlar")
                    elif title_lower.startswith("alət alışı"):
                        match = resolve_subcat("Texnika alışı")
                    elif title_lower.startswith("heyvan alışı"):
                        match = resolve_subcat("Heyvan alışı")

                if match:
                    sub_name = match.name
                    cat_name = match.category.name if match.category else ""
                elif exp.manual_name:
                    sub_name = exp.manual_name
                    cat_name = ""

            exp.subcategory_name = sub_name
            exp.category_name = cat_name
            cat_tag = cat_name or "Digər"
            sub_tag = sub_name or "Digər"
            # If template came from expenses page (no linked object), show only main category.
            if getattr(exp, "content_object", None) is None:
                exp.primary_tags = [cat_tag]
            elif sub_name:
                exp.primary_tags = [cat_tag, sub_tag]
            else:
                exp.primary_tags = [cat_tag]
            templates.append(exp)

    context = {
        "quick_items": QUICK_ITEMS,
        "templates": templates,
    }
    return render(request, "dashboard/quick_expense.html", context)


@login_required
def quick_income(request):
    from incomes.models import Income, UNIT_EDAD, UNIT_KQ, UNIT_LITR
    from incomes.views import (
        _adjust_farm_stock,
        _adjust_seed_stock,
        _allowed_units_for_farm,
        _category_type,
        _farm_base_unit,
        _farm_stock_base,
        _farm_to_base,
        _farm_unit_lookup,
        _get_animal_by_id,
        _seed_stock_kg,
        _seed_to_kg,
    )
    from animals.models import Animal, AnimalSubCategory
    from common.formatting import format_currency
    from django.contrib import messages as django_messages

    QUICK_ITEMS = [
        {"name": "İnək südü", "icon": "🥛", "amount": 35, "category": "Süd və Süd Məhsulları", "quantity": 10, "unit": UNIT_LITR},
        {"name": "Toyuq yumurtası", "icon": "🥚", "amount": 18, "category": "Yumurta", "quantity": 30, "unit": UNIT_EDAD},
        {"name": "Bal", "icon": "🍯", "amount": 45, "category": "Bal və Arıçılıq", "quantity": 3, "unit": UNIT_KQ},
        {"name": "Kartof", "icon": "🥔", "amount": 28, "category": "Tərəvəz", "quantity": 8, "unit": UNIT_KQ},
    ]

    def create_income_entry(*, category, item_name, quantity, unit, amount, gender="", identification_no="", additional_info=None):
        ctype = _category_type(category)
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
            available_kg = _seed_stock_kg(request.user, item_name)
            needed_kg = _seed_to_kg(quantity, unit)
            if available_kg < needed_kg:
                raise ValueError("Stokda kifayət qədər toxum yoxdur.")
        elif ctype == "farm":
            base_unit = _farm_base_unit(unit)
            available_base = _farm_stock_base(request.user, item_name, base_unit)
            needed_base = _farm_to_base(quantity, unit, base_unit)
            if available_base < needed_base:
                raise ValueError("Stokda kifayət qədər məhsul yoxdur.")

        income = Income.objects.create(
            category=category,
            item_name=item_name,
            quantity=quantity,
            unit=unit,
            amount=amount,
            gender=gender if ctype == "animal" else None,
            additional_info=additional_info,
            created_by=request.user,
        )

        note = "Gəlir satışı"
        if ctype == "seed":
            stock_item = _adjust_seed_stock(request.user, item_name, -abs(quantity), unit, note, amount)
            if stock_item:
                income.content_object = stock_item
                income.save(update_fields=["content_type", "object_id"])
        elif ctype == "farm":
            stock_item = _adjust_farm_stock(request.user, item_name, -abs(quantity), unit, note, amount)
            if stock_item:
                income.content_object = stock_item
                income.save(update_fields=["content_type", "object_id"])
        elif ctype == "animal":
            qty_int = int(quantity)
            target_animal = _get_animal_by_id(request.user, identification_no)
            if identification_no:
                if not target_animal:
                    income.delete()
                    raise ValueError("Bu identifikasiya nömrəsinə uyğun heyvan tapılmadı.")
                if target_animal.subcategory:
                    if target_animal.subcategory.name != item_name:
                        income.delete()
                        raise ValueError("Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
                else:
                    if (target_animal.manual_name or "").strip() != item_name:
                        income.delete()
                        raise ValueError("Seçilmiş heyvan ID-si bu kateqoriyaya uyğun deyil.")
                subcat = target_animal.subcategory
            else:
                subcat = AnimalSubCategory.objects.filter(name=item_name).first()

            income_tag = f"income:{income.id}"
            display_animal = Animal.objects.create(
                subcategory=subcat,
                manual_name=None if subcat else item_name,
                gender=gender,
                quantity=-abs(qty_int),
                price=amount,
                additional_info=f"Gəlir satışı | {income_tag}",
                created_by=request.user,
            )
            if identification_no and target_animal:
                target_animal.delete()
            income.content_object = display_animal
            income.save(update_fields=["content_type", "object_id"])

        return income

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "quick_add":
            name = request.POST.get("name", "")
            category = request.POST.get("category", "Digər")
            unit = request.POST.get("unit", UNIT_EDAD)
            quantity = request.POST.get("quantity", "1")
            amount = request.POST.get("amount", "0")
            custom_amount = request.POST.get("custom_amount", "")
            try:
                quantity_val = float(quantity)
            except (ValueError, TypeError):
                quantity_val = 1
            try:
                amount_val = float(amount)
            except (ValueError, TypeError):
                amount_val = 0
            if custom_amount:
                try:
                    amount_val = float(custom_amount)
                except (ValueError, TypeError):
                    pass

            if amount_val > 0:
                try:
                    create_income_entry(
                        category=category,
                        item_name=name,
                        quantity=quantity_val,
                        unit=unit,
                        amount=amount_val,
                    )
                    django_messages.success(request, f"{name} — {format_currency(amount_val, 0)}₼ əlavə edildi")
                except ValueError as exc:
                    django_messages.error(request, str(exc))

        elif action == "custom_amount":
            amount = request.POST.get("amount", "0")
            try:
                amount_val = float(amount)
            except (ValueError, TypeError):
                amount_val = 0

            if amount_val > 0:
                Income.objects.create(
                    category="Digər",
                    item_name="Xüsusi gəlir",
                    quantity=1,
                    unit=UNIT_EDAD,
                    amount=amount_val,
                    created_by=request.user,
                )
                django_messages.success(request, f"Xüsusi gəlir — {format_currency(amount_val, 0)}₼ əlavə edildi")

        elif action == "template_add":
            template_id = request.POST.get("template_id")
            custom_amount = request.POST.get("custom_amount", "")
            if template_id:
                try:
                    original = Income.objects.get(pk=template_id, created_by=request.user)
                    amount_val = original.amount
                    if custom_amount:
                        try:
                            amount_val = float(custom_amount)
                        except (ValueError, TypeError):
                            amount_val = original.amount
                    try:
                        create_income_entry(
                            category=original.category,
                            item_name=original.item_name,
                            quantity=original.quantity,
                            unit=original.unit,
                            amount=amount_val,
                            gender=original.gender or "",
                            additional_info=original.additional_info,
                        )
                        django_messages.success(request, f"{original.item_name} — {format_currency(amount_val, 0)}₼ əlavə edildi")
                    except ValueError as exc:
                        django_messages.error(request, str(exc))
                except Income.DoesNotExist:
                    pass

        return redirect("quick_income")

    recent_incomes = Income.objects.filter(created_by=request.user).order_by("-created_at")[:20]
    seen_items = set()
    templates = []
    for income in recent_incomes:
        unique_key = (income.item_name, income.category)
        if unique_key not in seen_items and len(templates) < 8:
            seen_items.add(unique_key)
            income.amount_display = format_currency(income.amount, 2)
            income.quantity_display = format_currency(income.quantity, 2).rstrip("0").rstrip(".")
            income.primary_tags = [income.category or "Digər", income.unit or "ədəd"]
            templates.append(income)

    context = {
        "quick_items": QUICK_ITEMS,
        "templates": templates,
    }
    return render(request, "dashboard/quick_income.html", context)


@login_required
def stock_warnings(request):
    return render(request, "dashboard/stock_warnings_placeholder.html")

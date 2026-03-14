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

    context = {
        "user_name" : request.user.get_username(),
        "stats" : {
            "new_addition": new_stocks,
            "weekly_net": weekly_net,
            "weekly_net_display": format_currency(weekly_net, 2),
            "animals": Animal.objects.filter(created_by=request.user, created_at__gte=start_of_week).count(),
        },
    }

    return render(request, "dashboard/index.html", context)


@login_required
def quick_expense(request):
    from expenses.models import Expense, ExpenseSubCategory
    from common.formatting import format_currency
    from django.contrib import messages as django_messages

    # Quick-tap preset items (name, icon, default amount, subcategory slug)
    QUICK_ITEMS = [
        {"name": "Yem", "icon": "🐄", "amount": 50},
        {"name": "Yanacaq", "icon": "⛽", "amount": 80},
        {"name": "Gübrə", "icon": "🪴", "amount": 120},
        {"name": "Baytar", "icon": "💉", "amount": 100},
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

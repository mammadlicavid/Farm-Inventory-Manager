from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from seeds.models import Seed
from animals.models import Animal, AnimalCategory, AnimalSubCategory
from tools.models import Tool
from expenses.models import Expense
from django.db.models import Sum

@login_required
def dashboard(request):
    session_start_str = request.session.get("session_start")
    session_start = parse_datetime(session_start_str) if session_start_str else None

    if session_start is None:
        session_start = timezone.now()

    new_products = (
        Seed.objects.filter(created_by=request.user, created_at__gte=session_start).count()
         + Animal.objects.filter(created_by=request.user, created_at__gte=session_start).count()
         + Tool.objects.filter(created_by=request.user, created_at__gte=session_start).count()
    )

    context = {
        "user_name" : request.user.get_username(),
        "stats" : {
            "new_addition": new_products,
            "expenses": Expense.objects.filter(created_by=request.user).aggregate(Sum('amount'))['amount__sum'] or 0,
            "animals": Animal.objects.filter(created_by=request.user).count(),
        },
    }

    return render(request, "dashboard/index.html", context)


@login_required
def tez_xerc(request):
    from expenses.models import Expense, ExpenseSubCategory
    from common.formatting import format_currency
    from django.contrib import messages as django_messages

    # Quick-tap preset items (name, icon, default amount, subcategory slug)
    QUICK_ITEMS = [
        {"name": "Yem", "icon": "🐄", "amount": 50},
        {"name": "Yanacaq", "icon": "⛽", "amount": 80},
        {"name": "Gübrə", "icon": "🌱", "amount": 120},
        {"name": "Baytar", "icon": "💉", "amount": 100},
    ]

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "quick_add":
            name = request.POST.get("name", "")
            amount = request.POST.get("amount", "0")
            try:
                amount_val = float(amount)
            except (ValueError, TypeError):
                amount_val = 0

            if amount_val > 0:
                # Try to find matching subcategory
                subcat = ExpenseSubCategory.objects.filter(name__iexact=name).first()
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
                Expense.objects.create(
                    title="Xüsusi xərc",
                    amount=amount_val,
                    created_by=request.user,
                )
                django_messages.success(request, f"Xüsusi xərc — {format_currency(amount_val, 0)}₼ əlavə edildi")

        elif action == "template_add":
            template_id = request.POST.get("template_id")
            if template_id:
                try:
                    original = Expense.objects.get(pk=template_id, created_by=request.user)
                    Expense.objects.create(
                        title=original.title,
                        amount=original.amount,
                        subcategory=original.subcategory,
                        manual_name=original.manual_name,
                        created_by=request.user,
                    )
                    django_messages.success(request, f"{original.title} — {format_currency(original.amount, 0)}₼ əlavə edildi")
                except Expense.DoesNotExist:
                    pass

        return redirect("tez_xerc")

    # GET — build context
    # Recent expenses as "templates" (last 10 unique by title)
    recent_expenses = (
        Expense.objects.filter(created_by=request.user)
        .order_by("-created_at")[:20]
    )
    # Deduplicate by title, keep most recent
    seen_titles = set()
    templates = []
    for exp in recent_expenses:
        if exp.title not in seen_titles and len(templates) < 8:
            seen_titles.add(exp.title)
            exp.amount_display = format_currency(exp.amount, 0)
            # Build tags
            tags = []
            if exp.subcategory:
                tags.append(exp.subcategory.name)
                if exp.subcategory.category:
                    tags.append(exp.subcategory.category.name)
            elif exp.manual_name:
                tags.append(exp.manual_name)
            exp.tags = tags
            templates.append(exp)

    context = {
        "quick_items": QUICK_ITEMS,
        "templates": templates,
    }
    return render(request, "dashboard/tez_xerc.html", context)
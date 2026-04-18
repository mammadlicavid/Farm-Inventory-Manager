import calendar as month_calendar
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils import translation
from django.core.cache import cache
from django.db.models import Case, DecimalField, F, IntegerField, Q, Sum, Value, When
from django.urls import reverse
from django.utils.formats import date_format

from seeds.models import Seed
from animals.models import Animal
from tools.models import Tool
from farm_products.models import FarmProduct
from expenses.models import Expense
from incomes.models import Income
from common.formatting import format_currency
from common.view_cache import (
    get_calendar_bust_value,
    get_dashboard_bust_value,
)
from common.zero_price_source import get_zero_price_source_label
from common.expense_titles import translate_expense_title
from notifications.services import sync_stock_alert_notifications


CALENDAR_WEEKDAY_LABELS = [
    _("B.e."),
    _("Ç.a."),
    _("Ç."),
    _("C.a."),
    _("C."),
    _("Ş."),
    _("B."),
]


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


def _count_positive_seed_groups(user) -> int:
    seed_total_expr = Sum(
        Case(
            When(unit="kg", then=F("quantity")),
            When(unit="ton", then=F("quantity") * Value(Decimal("1000"))),
            When(unit="qram", then=F("quantity") / Value(Decimal("1000"))),
            default=F("quantity"),
            output_field=DecimalField(max_digits=14, decimal_places=4),
        )
    )
    item_groups = (
        Seed.objects.filter(created_by=user, item__isnull=False)
        .exclude(item__name__iexact="Digər")
        .values("item_id")
        .annotate(total_kg=seed_total_expr)
        .filter(total_kg__gt=0)
        .count()
    )
    manual_groups = (
        Seed.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        .exclude(manual_name__isnull=True)
        .exclude(manual_name="")
        .exclude(manual_name__iexact="Digər")
        .values("manual_name")
        .annotate(total_kg=seed_total_expr)
        .filter(total_kg__gt=0)
        .count()
    )
    return item_groups + manual_groups


def _count_positive_tool_groups(user) -> int:
    item_groups = (
        Tool.objects.filter(created_by=user, item__isnull=False)
        .exclude(item__name__iexact="Digər")
        .values("item_id")
        .annotate(total_qty=Sum("quantity"))
        .filter(total_qty__gt=0)
        .count()
    )
    manual_groups = (
        Tool.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        .exclude(manual_name__isnull=True)
        .exclude(manual_name="")
        .exclude(manual_name__iexact="Digər")
        .values("manual_name")
        .annotate(total_qty=Sum("quantity"))
        .filter(total_qty__gt=0)
        .count()
    )
    return item_groups + manual_groups


def _count_positive_animal_groups(user) -> int:
    subcategory_groups = (
        Animal.objects.filter(created_by=user)
        .exclude(quantity=0)
        .filter(subcategory__isnull=False)
        .exclude(subcategory__name__iexact="Digər")
        .values("subcategory_id")
        .annotate(total_qty=Sum("quantity"))
        .filter(total_qty__gt=0)
        .count()
    )
    manual_groups = (
        Animal.objects.filter(created_by=user)
        .exclude(quantity=0)
        .filter(Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər"))
        .exclude(manual_name__isnull=True)
        .exclude(manual_name="")
        .exclude(manual_name__iexact="Digər")
        .values("manual_name")
        .annotate(total_qty=Sum("quantity"))
        .filter(total_qty__gt=0)
        .count()
    )
    return subcategory_groups + manual_groups


def _count_positive_farm_groups(user) -> int:
    grouped_totals = {}
    item_rows = (
        FarmProduct.objects.filter(created_by=user, item__isnull=False)
        .exclude(item__name__iexact="Digər")
        .values("item_id", "item__unit", "unit")
        .annotate(total_qty=Sum("quantity"))
    )
    for row in item_rows:
        item_unit = row["item__unit"] or row["unit"] or ""
        stock_unit = row["unit"] or ""
        if stock_unit in {"kq", "ton", "qram"}:
            base_unit = "kq"
        elif stock_unit in {"litr", "ml"}:
            base_unit = "litr"
        else:
            base_unit = item_unit or stock_unit
        key = ("item", row["item_id"], stock_unit) if base_unit == "bağlama" else ("item", row["item_id"])
        grouped_totals[key] = grouped_totals.get(key, Decimal("0")) + _convert_farm_qty(
            Decimal(row["total_qty"] or 0),
            stock_unit,
            base_unit,
        )

    manual_rows = (
        FarmProduct.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"))
        .exclude(manual_name__isnull=True)
        .exclude(manual_name="")
        .exclude(manual_name__iexact="Digər")
        .values("manual_name", "unit")
        .annotate(total_qty=Sum("quantity"))
    )
    for row in manual_rows:
        key = ("manual", (row["manual_name"] or "").strip(), row["unit"] or "")
        grouped_totals[key] = grouped_totals.get(key, Decimal("0")) + Decimal(row["total_qty"] or 0)

    return sum(1 for total in grouped_totals.values() if total > 0)


def _build_stock_overview(user):
    seed_groups = _count_positive_seed_groups(user)
    animal_groups = _count_positive_animal_groups(user)
    tool_groups = _count_positive_tool_groups(user)
    farm_groups = _count_positive_farm_groups(user)
    stock_breakdown = [
        {"label": _("Toxum"), "count": seed_groups, "icon": "fa-seedling"},
        {"label": _("Heyvan"), "count": animal_groups, "icon": "fa-cow"},
        {"label": _("Alət"), "count": tool_groups, "icon": "fa-wrench"},
        {"label": _("Məhsul"), "count": farm_groups, "icon": "fa-warehouse"},
    ]
    return {
        "stock_groups": seed_groups + animal_groups + tool_groups + farm_groups,
        "stock_breakdown": stock_breakdown,
    }


def _safe_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _clean_calendar_note(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"\s*\|\s*income:\d+\b", "", str(value))
    cleaned = re.sub(r"\bincome:\d+\b", "", cleaned)
    return cleaned.strip()


def _is_income_origin_note(value: str | None) -> bool:
    note = _clean_calendar_note(value).lower()
    return note.startswith("gəlir satışı") or note.startswith("gelir satışı")


def _display_record_name(primary_name: str | None, manual_name: str | None, fallback: str) -> str:
    primary = str(primary_name or "").strip()
    if primary and primary.lower() != "digər":
        return primary

    manual = str(manual_name or "").strip()
    if manual and manual.lower() != "digər":
        return manual

    return fallback


def _month_start_from_query(raw_value: str | None, fallback: date) -> date:
    raw = str(raw_value or "").strip()
    if raw:
        try:
            return date.fromisoformat(f"{raw}-01")
        except ValueError:
            pass
    return fallback.replace(day=1)


def _shift_month(month_start: date, delta: int) -> date:
    month_index = month_start.month - 1 + delta
    year = month_start.year + (month_index // 12)
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _month_bounds(month_start: date) -> tuple[date, date]:
    next_month = _shift_month(month_start, 1)
    return month_start, next_month - timedelta(days=1)


def _selected_day_from_query(raw_value: str | None, month_start: date) -> date | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    try:
        selected = date.fromisoformat(raw)
    except ValueError:
        return None
    if selected.year == month_start.year and selected.month == month_start.month:
        return selected
    return None


def _activity_sort_stamp(activity_date: date, created_at=None):
    if created_at is not None:
        return created_at
    return timezone.make_aware(
        datetime.combine(activity_date, time.min),
        timezone.get_current_timezone(),
    )


def _activity_badge(label: str, badge_class: str) -> dict[str, str]:
    return {
        "label": label,
        "class_name": badge_class,
    }


def _summarize_day_activities(activities: list[dict]) -> dict:
    summary = {
        "total": len(activities),
        "stock_in": 0,
        "stock_out": 0,
        "income": 0,
        "expense": 0,
        "income_total": Decimal("0"),
        "expense_total": Decimal("0"),
    }

    for activity in activities:
        kind = activity["kind"]
        financial_role = activity.get("financial_role")
        if kind == "stock-in":
            summary["stock_in"] += 1
        elif kind == "stock-out":
            summary["stock_out"] += 1
        if kind == "income":
            summary["income"] += 1
        elif kind == "expense":
            summary["expense"] += 1

        if financial_role == "income":
            summary["income_total"] += _safe_decimal(activity.get("amount"))
        elif financial_role == "expense":
            summary["expense_total"] += _safe_decimal(activity.get("amount"))

    badges = []
    if summary["stock_in"]:
        badges.append(_activity_badge(_("{} əlavə").format(summary["stock_in"]), "stock-in"))
    if summary["income"]:
        badges.append(_activity_badge(_("{} satış").format(summary["income"]), "income"))
    if summary["expense"]:
        badges.append(_activity_badge(_("{} xərc").format(summary["expense"]), "expense"))
    if summary["stock_out"]:
        badges.append(_activity_badge(_("{} azalma").format(summary["stock_out"]), "stock-out"))

    preview_items = [
        {
            "title": activity["title"],
            "icon": activity["icon"],
            "class_name": activity["kind"],
        }
        for activity in activities[:2]
    ]

    summary["badges"] = badges
    summary["preview_items"] = preview_items
    summary["more_count"] = max(len(activities) - len(preview_items), 0)
    return summary


def _build_calendar_activity_map(user, month_start: date, month_end: date) -> dict[date, list[dict]]:
    activity_map: dict[date, list[dict]] = defaultdict(list)

    def append(entry: dict):
        activity_map[entry["date"]].append(entry)

    seeds = (
        Seed.objects.filter(created_by=user, date__range=(month_start, month_end))
        .select_related("item")
        .only(
            "date",
            "created_at",
            "quantity",
            "unit",
            "price",
            "manual_name",
            "additional_info",
            "item__name",
        )
    )
    for seed in seeds:
        if _is_income_origin_note(seed.additional_info):
            continue
        quantity = _safe_decimal(seed.quantity)
        if quantity == 0:
            continue
        kind = "stock-in" if quantity > 0 else "stock-out"
        price_value = _safe_decimal(seed.price)
        financial_role = ""
        amount = None
        amount_prefix = ""
        if price_value > 0:
            financial_role = "expense" if kind == "stock-in" else "income"
            amount = price_value
            amount_prefix = "-" if financial_role == "expense" else "+"
        append(
            {
                "date": seed.date,
                "sort_stamp": _activity_sort_stamp(seed.date, getattr(seed, "created_at", None)),
                "kind": kind,
                "financial_role": financial_role,
                "icon": "fa-seedling",
                "title": _display_record_name(
                    getattr(seed.item, "name", None),
                    seed.manual_name,
                    str(_("Toxum")),
                ),
                "subtitle": str(_("Toxumlar bölməsi")),
                "operation_label": str(_("Stok hərəkəti")),
                "quantity": abs(quantity),
                "unit": seed.unit or "kg",
                "quantity_prefix": "+" if kind == "stock-in" else "-",
                "amount": amount,
                "amount_prefix": amount_prefix,
                "note": get_zero_price_source_label(seed) or _clean_calendar_note(seed.additional_info),
            }
        )

    animals = (
        Animal.objects.filter(created_by=user, date__range=(month_start, month_end))
        .select_related("subcategory")
        .only(
            "date",
            "created_at",
            "quantity",
            "price",
            "manual_name",
            "additional_info",
            "identification_no",
            "subcategory__name",
        )
    )
    for animal in animals:
        if _is_income_origin_note(animal.additional_info):
            continue
        quantity = _safe_decimal(animal.quantity)
        if quantity == 0:
            continue
        kind = "stock-in" if quantity > 0 else "stock-out"
        price_value = _safe_decimal(animal.price)
        financial_role = ""
        amount = None
        amount_prefix = ""
        if price_value > 0:
            financial_role = "expense" if kind == "stock-in" else "income"
            amount = price_value
            amount_prefix = "-" if financial_role == "expense" else "+"
        animal_note = get_zero_price_source_label(animal) or _clean_calendar_note(animal.additional_info)
        if animal.identification_no:
            animal_note = (
                f"{animal_note} • ID: {animal.identification_no}"
                if animal_note
                else f"ID: {animal.identification_no}"
            )
        append(
            {
                "date": animal.date,
                "sort_stamp": _activity_sort_stamp(animal.date, getattr(animal, "created_at", None)),
                "kind": kind,
                "financial_role": financial_role,
                "icon": "fa-cow",
                "title": _display_record_name(
                    getattr(animal.subcategory, "name", None),
                    animal.manual_name,
                    str(_("Heyvan")),
                ),
                "subtitle": str(_("Heyvanlar bölməsi")),
                "operation_label": str(_("Stok hərəkəti")),
                "quantity": abs(quantity),
                "unit": "ədəd",
                "quantity_prefix": "+" if kind == "stock-in" else "-",
                "amount": amount,
                "amount_prefix": amount_prefix,
                "note": animal_note,
            }
        )

    tools = (
        Tool.objects.filter(created_by=user, date__range=(month_start, month_end))
        .select_related("item")
        .only(
            "date",
            "created_at",
            "quantity",
            "price",
            "manual_name",
            "additional_info",
            "item__name",
        )
    )
    for tool in tools:
        if _is_income_origin_note(tool.additional_info):
            continue
        quantity = _safe_decimal(tool.quantity)
        if quantity == 0:
            continue
        kind = "stock-in" if quantity > 0 else "stock-out"
        price_value = _safe_decimal(tool.price)
        financial_role = ""
        amount = None
        amount_prefix = ""
        if price_value > 0:
            financial_role = "expense" if kind == "stock-in" else "income"
            amount = price_value
            amount_prefix = "-" if financial_role == "expense" else "+"
        append(
            {
                "date": tool.date,
                "sort_stamp": _activity_sort_stamp(tool.date, getattr(tool, "created_at", None)),
                "kind": kind,
                "financial_role": financial_role,
                "icon": "fa-wrench",
                "title": _display_record_name(
                    getattr(tool.item, "name", None),
                    tool.manual_name,
                    str(_("Alət")),
                ),
                "subtitle": str(_("Alətlər bölməsi")),
                "operation_label": str(_("Stok hərəkəti")),
                "quantity": abs(quantity),
                "unit": "ədəd",
                "quantity_prefix": "+" if kind == "stock-in" else "-",
                "amount": amount,
                "amount_prefix": amount_prefix,
                "note": get_zero_price_source_label(tool) or _clean_calendar_note(tool.additional_info),
            }
        )

    products = (
        FarmProduct.objects.filter(created_by=user, date__range=(month_start, month_end))
        .select_related("item")
        .only(
            "date",
            "created_at",
            "quantity",
            "unit",
            "price",
            "manual_name",
            "additional_info",
            "item__name",
        )
    )
    for product in products:
        if _is_income_origin_note(product.additional_info):
            continue
        quantity = _safe_decimal(product.quantity)
        if quantity == 0:
            continue
        kind = "stock-in" if quantity > 0 else "stock-out"
        price_value = _safe_decimal(product.price)
        financial_role = ""
        amount = None
        amount_prefix = ""
        if price_value > 0:
            financial_role = "expense" if kind == "stock-in" else "income"
            amount = price_value
            amount_prefix = "-" if financial_role == "expense" else "+"
        append(
            {
                "date": product.date,
                "sort_stamp": _activity_sort_stamp(product.date, getattr(product, "created_at", None)),
                "kind": kind,
                "financial_role": financial_role,
                "icon": "fa-warehouse",
                "title": _display_record_name(
                    getattr(product.item, "name", None),
                    product.manual_name,
                    str(_("Məhsul")),
                ),
                "subtitle": str(_("Hazır məhsullar bölməsi")),
                "operation_label": str(_("Stok hərəkəti")),
                "quantity": abs(quantity),
                "unit": product.unit or "ədəd",
                "quantity_prefix": "+" if kind == "stock-in" else "-",
                "amount": amount,
                "amount_prefix": amount_prefix,
                "note": get_zero_price_source_label(product) or _clean_calendar_note(product.additional_info),
            }
        )

    incomes = Income.objects.filter(created_by=user, date__range=(month_start, month_end)).only(
        "date",
        "created_at",
        "category",
        "item_name",
        "quantity",
        "unit",
        "amount",
        "additional_info",
        "content_type_id",
        "object_id",
    )
    for income in incomes:
        linked_object = getattr(income, "content_object", None)
        linked_note = getattr(linked_object, "additional_info", "") if linked_object is not None else ""
        if linked_object is not None and not _is_income_origin_note(linked_note):
            continue
        append(
            {
                "date": income.date,
                "sort_stamp": _activity_sort_stamp(income.date, getattr(income, "created_at", None)),
                "kind": "income",
                "financial_role": "income",
                "icon": "fa-money-bill-trend-up",
                "title": _display_record_name(income.item_name, None, str(_("Gəlir"))),
                "subtitle": str(_("Gəlir səhifəsi")),
                "operation_label": income.category or str(_("Satış")),
                "quantity": abs(_safe_decimal(income.quantity)),
                "unit": income.unit or "ədəd",
                "quantity_prefix": "",
                "amount": _safe_decimal(income.amount),
                "amount_prefix": "+",
                "note": _clean_calendar_note(income.additional_info),
            }
        )

    expenses = Expense.objects.filter(created_by=user, date__range=(month_start, month_end)).select_related(
        "subcategory",
        "subcategory__category",
    ).only(
        "date",
        "created_at",
        "title",
        "manual_name",
        "amount",
        "additional_info",
        "content_type_id",
        "object_id",
        "subcategory__name",
        "subcategory__category__name",
    )
    for expense in expenses:
        if expense.content_type_id and expense.object_id:
            continue
        expense_title = translate_expense_title(str(expense.title or expense.manual_name or _("Xərc")).strip())
        expense_subtitle = (
            getattr(expense.subcategory, "name", None)
            or getattr(getattr(expense.subcategory, "category", None), "name", None)
            or str(_("Xərc"))
        )
        append(
            {
                "date": expense.date,
                "sort_stamp": _activity_sort_stamp(expense.date, getattr(expense, "created_at", None)),
                "kind": "expense",
                "financial_role": "expense",
                "icon": "fa-receipt",
                "title": expense_title,
                "subtitle": str(_("Xərc səhifəsi")),
                "operation_label": expense_subtitle,
                "quantity": None,
                "unit": "",
                "quantity_prefix": "",
                "amount": _safe_decimal(expense.amount),
                "amount_prefix": "-",
                "note": _clean_calendar_note(expense.additional_info),
            }
        )

    priority = {
        "income": 0,
        "expense": 1,
        "stock-out": 2,
        "stock-in": 3,
    }
    for day, activities in activity_map.items():
        activities.sort(
            key=lambda item: (item["sort_stamp"], -priority.get(item["kind"], 10)),
            reverse=True,
        )

    return activity_map


def _choose_selected_day(month_start: date, today: date, requested_day: date | None, activity_map) -> date:
    if requested_day is not None:
        return requested_day
    if today.year == month_start.year and today.month == month_start.month:
        return today
    active_days = sorted(activity_map.keys())
    if active_days:
        return active_days[0]
    return month_start


def _build_calendar_grid(month_start: date, today: date, selected_day: date, activity_map) -> list[list[dict]]:
    grid = []
    calendar_rows = month_calendar.Calendar(firstweekday=0).monthdatescalendar(
        month_start.year,
        month_start.month,
    )
    for week in calendar_rows:
        week_cells = []
        for day in week:
            activities = activity_map.get(day, [])
            summary = _summarize_day_activities(activities)
            week_cells.append(
                {
                    "date": day,
                    "date_iso": day.isoformat(),
                    "month_key": day.strftime("%Y-%m"),
                    "day_number": day.day,
                    "in_month": day.month == month_start.month,
                    "is_today": day == today,
                    "is_selected": day == selected_day,
                    "summary": summary,
                }
            )
        grid.append(week_cells)
    return grid


@login_required
def calendar_page(request):
    user = request.user
    today = timezone.localdate()
    month_start = _month_start_from_query(request.GET.get("month"), today)
    month_start, month_end = _month_bounds(month_start)
    requested_day = _selected_day_from_query(request.GET.get("day"), month_start)
    language_code = (translation.get_language() or "az").lower()
    calendar_cache_key = (
        f"calendar:v1:{user.pk}:{get_calendar_bust_value(user.pk)}:{language_code}:"
        f"{month_start.isoformat()}:{today.isoformat()}:{requested_day.isoformat() if requested_day else ''}"
    )
    cached_context = cache.get(calendar_cache_key)
    if cached_context is not None:
        return render(request, "dashboard/calendar.html", cached_context)

    activity_map = _build_calendar_activity_map(user, month_start, month_end)
    selected_day = _choose_selected_day(month_start, today, requested_day, activity_map)
    selected_day_activities = activity_map.get(selected_day, [])
    selected_day_summary = _summarize_day_activities(selected_day_activities)
    calendar_grid = _build_calendar_grid(month_start, today, selected_day, activity_map)

    monthly_income = sum(
        (
            _safe_decimal(activity["amount"])
            for activities in activity_map.values()
            for activity in activities
            if activity.get("financial_role") == "income"
        ),
        start=Decimal("0"),
    )
    monthly_expense = sum(
        (
            _safe_decimal(activity["amount"])
            for activities in activity_map.values()
            for activity in activities
            if activity.get("financial_role") == "expense"
        ),
        start=Decimal("0"),
    )
    monthly_stock_actions = sum(
        1
        for activities in activity_map.values()
        for activity in activities
        if activity["kind"] in {"stock-in", "stock-out"}
    )

    context = {
        "calendar_data": {
            "month_label": date_format(month_start, "F Y"),
            "active_month_key": month_start.strftime("%Y-%m"),
            "prev_month_key": _shift_month(month_start, -1).strftime("%Y-%m"),
            "next_month_key": _shift_month(month_start, 1).strftime("%Y-%m"),
            "today_month_key": today.strftime("%Y-%m"),
            "today_iso": today.isoformat(),
            "weekday_labels": CALENDAR_WEEKDAY_LABELS,
            "weeks": calendar_grid,
            "active_day_count": len(activity_map),
            "total_activity_count": sum(len(activities) for activities in activity_map.values()),
            "monthly_stock_actions": monthly_stock_actions,
            "monthly_income": monthly_income,
            "monthly_expense": monthly_expense,
            "selected_day": {
                "label": date_format(selected_day, "j F Y, l"),
                "date_iso": selected_day.isoformat(),
                "is_today": selected_day == today,
                "summary": selected_day_summary,
                "activities": selected_day_activities,
                "income_total": selected_day_summary["income_total"],
                "expense_total": selected_day_summary["expense_total"],
            },
        }
    }
    cache.set(calendar_cache_key, context, 300)
    return render(request, "dashboard/calendar.html", context)


@login_required
def dashboard(request):
    user = request.user
    now = timezone.localtime(timezone.now())
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    language_code = (translation.get_language() or "az").lower()
    cache_key = (
        f"dashboard:v6:{user.pk}:{get_dashboard_bust_value(user.pk)}:"
        f"{language_code}:{start_of_week.date().isoformat()}"
    )
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return render(request, "dashboard/index.html", cached_context)

    weekly_seed_count = Seed.objects.filter(created_by=user, created_at__gte=start_of_week).count()
    weekly_animal_count = Animal.objects.filter(created_by=user, created_at__gte=start_of_week).count()
    weekly_tool_count = Tool.objects.filter(created_by=user, created_at__gte=start_of_week).count()
    new_stocks = weekly_seed_count + weekly_animal_count + weekly_tool_count

    weekly_expenses = (
        Expense.objects.filter(created_by=user, created_at__gte=start_of_week)
        .aggregate(Sum("amount"))
        .get("amount__sum")
        or 0
    )
    weekly_income = (
        Income.objects.filter(created_by=user, created_at__gte=start_of_week)
        .aggregate(Sum("amount"))
        .get("amount__sum")
        or 0
    )
    weekly_net = weekly_income - weekly_expenses
    display_name = (user.first_name or "").strip() or user.get_username()
    stock_overview = _build_stock_overview(user)
    has_any_records = any(
        queryset.exists()
        for queryset in (
            Seed.objects.filter(created_by=user),
            Animal.objects.filter(created_by=user),
            Tool.objects.filter(created_by=user),
            FarmProduct.objects.filter(created_by=user),
            Expense.objects.filter(created_by=user),
            Income.objects.filter(created_by=user),
        )
    )

    low_stock_alerts, pending_notification_count = sync_stock_alert_notifications(user)
    low_stock_alerts = low_stock_alerts[:4]
    critical_count = sum(1 for item in low_stock_alerts if item["status"] == "kritik")

    context = {
        "user_name": display_name,
        "overview": {
            "stock_groups": stock_overview["stock_groups"],
            "stock_breakdown": stock_overview["stock_breakdown"],
            "weekly_income": weekly_income,
            "weekly_income_display": format_currency(weekly_income, 2),
            "weekly_expenses": weekly_expenses,
            "weekly_expenses_display": format_currency(weekly_expenses, 2),
            "weekly_balance": weekly_net,
            "weekly_balance_display": format_currency(weekly_net, 2),
            "new_additions": new_stocks,
            "new_animals": weekly_animal_count,
        },
        "show_onboarding": not has_any_records,
        "low_stock_alerts": low_stock_alerts,
        "critical_count": critical_count,
        "pending_notification_count": pending_notification_count,
    }
    cache.set(cache_key, context, 300)

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
                django_messages.success(
                    request,
                    _("{name} — {amount}₼ əlavə edildi").format(
                        name=name,
                        amount=format_currency(amount_val, 0),
                    ),
                )

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
                django_messages.success(
                    request,
                    _("Xüsusi xərc — {amount}₼ əlavə edildi").format(
                        amount=format_currency(amount_val, 0),
                    ),
                )

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
                    django_messages.success(
                        request,
                        _("{title} — {amount}₼ əlavə edildi").format(
                            title=original.title,
                            amount=format_currency(amount_val, 0),
                        ),
                    )
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
            exp.display_title = translate_expense_title(exp.title)
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
                    django_messages.success(
                        request,
                        _("{name} — {amount}₼ əlavə edildi").format(
                            name=name,
                            amount=format_currency(amount_val, 0),
                        ),
                    )
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
                django_messages.success(
                    request,
                    _("Xüsusi gəlir — {amount}₼ əlavə edildi").format(
                        amount=format_currency(amount_val, 0),
                    ),
                )

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
                        django_messages.success(
                            request,
                            _("{item_name} — {amount}₼ əlavə edildi").format(
                                item_name=original.item_name,
                                amount=format_currency(amount_val, 0),
                            ),
                        )
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
    return redirect("notifications:list")

from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect

from expenses.models import Expense   # Keep this if expenses is installed as "expenses"
from common.formatting import format_currency


@login_required
def reports_list(request):
    user = request.user
    today = date.today()
    year = today.year

    qs = (
        Expense.objects
        .filter(created_by=user, date__year=year)
        .select_related("subcategory", "subcategory__category")
    )

    total_expense = qs.aggregate(total=Sum("amount"))["total"] or 0
    month_expense = qs.filter(date__month=today.month).aggregate(total=Sum("amount"))["total"] or 0
    
    breakdown_rows = (
        qs.values("subcategory__category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    breakdown_list = []
    for row in breakdown_rows:
        name = row["subcategory__category__name"] or "Digər"
        amt = row["total"] or 0
        pct = 0
        if total_expense:
            pct = round((float(amt) / float(total_expense)) * 100)

        breakdown_list.append({
            "name": name,
            "amount": float(amt),
            "amount_display": format_currency(amt, 0),
            "pct": pct
        })

    month_rows = (
        qs.annotate(m=TruncMonth("date"))
        .values("m")
        .annotate(total=Sum("amount"))
        .order_by("m")
    )

    month_map = {
        r["m"].month: float(r["total"] or 0)
        for r in month_rows if r["m"]
    }

    az_months = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avq", "Sen", "Okt", "Noy", "Dek"]

    trend_months = az_months
    trend_values = [month_map.get(i + 1, 0) for i in range(12)]

    context = {
    "total_expense": float(total_expense),
    "month_expense": float(month_expense),
    "total_expense_display": format_currency(total_expense, 0),
    "month_expense_display": format_currency(month_expense, 0),
    "breakdown_list": breakdown_list,
    "trend_months": trend_months,
    "trend_values": trend_values,
    "report_year": year,
    }

    return render(request, "reports/reports_list.html", context)


@login_required
def reports_form(request):
    if request.method == "POST":
        return redirect("reports:list")

    return render(request, "reports/reports_form.html")

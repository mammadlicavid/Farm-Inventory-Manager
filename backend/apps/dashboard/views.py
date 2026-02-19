from django.shortcuts import render
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
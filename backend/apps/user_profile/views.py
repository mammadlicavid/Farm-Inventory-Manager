from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from seeds.models import Seed
from animals.models import Animal
from tools.models import Tool
from expenses.models import Expense
from django.db.models import Sum


@login_required
def profile_page(request):
    user = request.user

    # Calculate total products (seeds + animals + tools)
    total_seeds = Seed.objects.filter(created_by=user).count()
    total_animals = Animal.objects.filter(created_by=user).count()
    total_tools = Tool.objects.filter(created_by=user).count()
    total_products = total_seeds + total_animals + total_tools

    # Calculate total expenses
    total_expenses = (
        Expense.objects.filter(created_by=user)
        .aggregate(Sum('amount'))['amount__sum'] or 0
    )

    # Calculate membership duration in months
    join_date = user.date_joined
    now = timezone.now()
    membership_months = (
        (now.year - join_date.year) * 12 + (now.month - join_date.month)
    )
    if membership_months < 1:
        membership_months = 1

    context = {
        'user': user,
        'total_products': total_products,
        'total_expenses': total_expenses,
        'membership_months': membership_months,
        'join_date': join_date.strftime('%Y-%m-%d'),
    }

    return render(request, 'profile/profile.html', context)

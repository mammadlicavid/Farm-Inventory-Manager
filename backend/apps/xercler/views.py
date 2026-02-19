from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from .models import Expense
from .forms import ExpenseForm

@login_required
def expense_list(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            return redirect('xercler:expense_list')
    else:
        form = ExpenseForm()

    # Get expenses
    expenses = Expense.objects.filter(created_by=request.user).order_by('-date', '-created_at')[:5]  # Last 5 expenses

    # Calculate weekly total
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    weekly_total = Expense.objects.filter(
        created_by=request.user,
        date__gte=week_start
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'form': form,
        'expenses': expenses,
        'weekly_total': weekly_total,
    }
    return render(request, 'xercler/xercler.html', context)

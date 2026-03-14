from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.http import JsonResponse

from .models import Expense, ExpenseCategory, ExpenseSubCategory
from common.messages import add_crud_success_message
from common.icons import get_expense_icon
from common.formatting import format_currency

def _build_subcategory_data(categories):
    return {
        str(cat.id): [{"id": sub.id, "name": sub.name} for sub in cat.subcategories.all()]
        for cat in categories
    }

def _get_display_additional_info(expense: Expense) -> str:
    """
    Return the note to show in UI for 'Əlavə Məlumat'.

    Rules:
    - If the expense is linked to an inventory item that has `additional_info`,
      use that value.
    - Otherwise, use the Expense.additional_info unless it is an old
      auto-generated string starting with "Miqdar:" or "İdentifikasiya No:".
    """
    linked = getattr(expense, "content_object", None)
    if linked is not None and hasattr(linked, "additional_info"):
        note = getattr(linked, "additional_info") or ""
        return note.strip()

    raw = expense.additional_info or ""
    stripped = raw.strip()
    if stripped.startswith("Miqdar:") or stripped.startswith("Çəki:") or stripped.startswith("İdentifikasiya No:"):
        return ""
    return raw

@login_required
def expense_list(request):
    expenses_qs = Expense.objects.filter(created_by=request.user).select_related('subcategory', 'subcategory__category')
    
    # Perform aggregations on QuerySet before converting to list
    total_amount = expenses_qs.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Weekly total calculation on QuerySet
    last_week = timezone.now().date() - timedelta(days=7)
    weekly_total = expenses_qs.filter(date__gte=last_week).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Convert to list for secondary processing (attaching display info)
    expenses = list(expenses_qs)

    subcat_lookup = {
        s.name.lower(): s
        for s in ExpenseSubCategory.objects.select_related("category").all()
    }

    # Attach display-only additional info and icon class
    for exp in expenses:
        exp.display_additional_info = _get_display_additional_info(exp)
        exp.icon_class = get_expense_icon(exp)
        exp.amount_display = format_currency(exp.amount, 2)
        exp.display_title = exp.title
        exp.display_type_tag = ""
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
                    exp.display_type_tag = base
        if exp.subcategory and exp.subcategory.category:
            exp.display_category_name = exp.subcategory.category.name
        else:
            match = None
            if exp.manual_name:
                match = subcat_lookup.get(exp.manual_name.lower())
            if not match and exp.title:
                match = subcat_lookup.get(exp.title.lower())
            if match and match.category:
                exp.display_category_name = match.category.name
            else:
                exp.display_category_name = "Digər"
    
    # Categories for the form
    categories = (
        ExpenseCategory.objects.exclude(name="Maliyyə və Digər")
        .prefetch_related('subcategories')
    )
    
    context = {
        'expenses': expenses,
        'total_amount': total_amount,
        'weekly_total': weekly_total,
        'weekly_total_display': format_currency(weekly_total, 2),
        'categories': categories,
        'subcategory_data': _build_subcategory_data(categories),
        'today': timezone.now().date(),
        'yesterday': timezone.now().date() - timedelta(days=1),
    }
    return render(request, 'expenses/expense_list.html', context)

@login_required
def add_expense(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        manual_name = request.POST.get('manual_name')
        subcategory_id = request.POST.get('subcategory')
        additional_info = request.POST.get('additional_info')
        
        subcategory = None
        if subcategory_id:
            try:
                subcategory = ExpenseSubCategory.objects.get(id=subcategory_id)
            except ExpenseSubCategory.DoesNotExist:
                pass
        
        if not (subcategory or manual_name) or not amount:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return redirect('expenses:expense_list')

        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = 0
        if amount_val <= 0:
            messages.error(request, 'Məbləğ düzgün deyil.')
            return redirect('expenses:expense_list')
        
        if not title:
            title = subcategory.name if subcategory else manual_name

        Expense.objects.create(
            title=title,
            amount=amount_val,
            subcategory=subcategory,
            manual_name=None if subcategory else title,
            additional_info=additional_info,
            created_by=request.user
        )
        add_crud_success_message(request, "Expense", "create")
        return redirect('expenses:expense_list')
    
    return redirect('expenses:expense_list')

@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, created_by=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        subcategory_id = request.POST.get('subcategory')
        manual_name = request.POST.get('manual_name')
        additional_info = request.POST.get('additional_info')
        
        subcategory = None
        if subcategory_id:
            try:
                subcategory = ExpenseSubCategory.objects.get(id=subcategory_id)
            except ExpenseSubCategory.DoesNotExist:
                pass
        
        if not (subcategory or manual_name) or not amount:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            categories = ExpenseCategory.objects.exclude(name="Maliyyə və Digər").prefetch_related('subcategories')
            return render(request, 'expenses/expense_form.html', {
                'expense': expense,
                'categories': categories,
                'subcategory_data': _build_subcategory_data(categories),
            })

        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = 0
        if amount_val <= 0:
            messages.error(request, 'Məbləğ düzgün deyil.')
            categories = ExpenseCategory.objects.exclude(name="Maliyyə və Digər").prefetch_related('subcategories')
            return render(request, 'expenses/expense_form.html', {
                'expense': expense,
                'categories': categories,
                'subcategory_data': _build_subcategory_data(categories),
            })
            
        expense.title = title if title else (subcategory.name if subcategory else manual_name)
        expense.amount = amount_val
        expense.subcategory = subcategory
        expense.manual_name = None if subcategory else (title if title else manual_name)
        expense.additional_info = additional_info
        expense.save()

        # Reverse Synchronization: Expense -> Inventory
        if expense.content_object:
            item = expense.content_object
            # Update price/amount on the linked item
            if hasattr(item, 'price'):
                item.price = expense.amount
            elif hasattr(item, 'amount'):
                item.amount = expense.amount
            if hasattr(item, 'additional_info'):
                item.additional_info = additional_info
            
            # Optionally update title/name if it changed? 
            # Usually inventory name is more specific, so we might keep it.
            # But we should at least sync the price.
            item.save()
        
        add_crud_success_message(request, "Expense", "update")
        return redirect('expenses:expense_list')

    # Initial GET render: compute display_additional_info for textarea
    expense.display_additional_info = _get_display_additional_info(expense)
    categories = (
        ExpenseCategory.objects.exclude(name="Maliyyə və Digər")
        .prefetch_related('subcategories')
    )
    return render(request, 'expenses/expense_form.html', {
        'expense': expense,
        'categories': categories,
        'subcategory_data': _build_subcategory_data(categories),
    })

@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, created_by=request.user)
    if request.method == 'POST':
        # Reverse Synchronization: Deleting expense deletes the linked item
        if expense.content_object:
            expense.content_object.delete()
        
        expense.delete()
        add_crud_success_message(request, "Expense", "delete")
    return redirect('expenses:expense_list')

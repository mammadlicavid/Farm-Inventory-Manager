from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Q

from .models import Tool, ToolCategory, ToolItem
from .forms import ToolForm
from common.messages import add_crud_success_message
from common.text import normalize_manual_label
from common.category_order import (
    TOOL_CATEGORY_ORDER,
    TOOL_ITEM_ORDER,
    order_queryset_by_name_list,
)
from common.icons import get_tool_icon_for_tool
from expenses.models import Expense, ExpenseSubCategory
from incomes.models import Income


def _tool_stock_total(user, item, manual_name: str | None) -> int:
    if item:
        qs = Tool.objects.filter(created_by=user, item=item)
    else:
        qs = Tool.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=manual_name,
        )
    total = 0
    for tool in qs:
        total += int(tool.quantity)
    return total


def _parse_date(value: str | None):
    if not value:
        return timezone.now().date()
    try:
        return date.fromisoformat(value)
    except Exception:
        return timezone.now().date()


def _ordered_tool_categories():
    return order_queryset_by_name_list(ToolCategory.objects.all(), TOOL_CATEGORY_ORDER)


def _sync_tool_related_records(user, tool):
    quantity_val = int(tool.quantity)
    tool_type = ContentType.objects.get_for_model(Tool)
    linked_income = Income.objects.filter(content_type=tool_type, object_id=tool.id).first()

    if quantity_val < 0:
        try:
            amount_val = abs(float(tool.price))
        except (TypeError, ValueError):
            amount_val = 0
        if linked_income:
            if amount_val > 0:
                linked_income.category = "Digər"
                linked_income.item_name = tool.item.name if tool.item else tool.manual_name
                linked_income.quantity = abs(quantity_val)
                linked_income.unit = "ədəd"
                linked_income.amount = amount_val
                linked_income.additional_info = tool.additional_info
                linked_income.date = tool.date
                linked_income.save()
            else:
                linked_income.delete()
        elif amount_val > 0:
            Income.objects.create(
                category="Digər",
                item_name=tool.item.name if tool.item else tool.manual_name,
                quantity=abs(quantity_val),
                unit="ədəd",
                amount=amount_val,
                additional_info=tool.additional_info,
                date=tool.date,
                created_by=user,
                content_object=tool,
            )
    elif linked_income:
        linked_income.delete()

    linked_expense = Expense.objects.filter(content_type=tool_type, object_id=tool.id).first()
    try:
        price_val = float(tool.price or 0)
    except (TypeError, ValueError):
        price_val = 0

    if quantity_val > 0 and price_val > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name='Texnika alışı').first()
        if linked_expense:
            linked_expense.amount = tool.price
            linked_expense.title = f"Alət alışı: {tool.item.name if tool.item else tool.manual_name}"
            linked_expense.additional_info = tool.additional_info
            linked_expense.subcategory = expense_sub
            linked_expense.manual_name = None if expense_sub else "Alət alışı (Digər)"
            linked_expense.save()
        else:
            Expense.objects.create(
                title=f"Alət alışı: {tool.item.name if tool.item else tool.manual_name}",
                amount=tool.price,
                subcategory=expense_sub,
                manual_name=None if expense_sub else "Alət alışı (Digər)",
                additional_info=tool.additional_info,
                created_by=user,
                content_object=tool
            )
    elif linked_expense:
        linked_expense.delete()


def _merge_manual_tool(user, manual_name, quantity_val, price, additional_info, entry_date):
    existing = (
        Tool.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"), manual_name__iexact=manual_name)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None

    total_qty = int(existing.quantity) + int(quantity_val)
    if total_qty == 0:
        tool_type = ContentType.objects.get_for_model(Tool)
        Expense.objects.filter(content_type=tool_type, object_id=existing.id).delete()
        Income.objects.filter(content_type=tool_type, object_id=existing.id).delete()
        existing.delete()
        return "deleted"

    existing.item = None
    existing.manual_name = manual_name
    existing.quantity = total_qty
    existing.price = price
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.save()
    _sync_tool_related_records(user, existing)
    return existing

@login_required
def tool_list(request):
    query = (request.GET.get('q') or '').strip()
    alets_qs = Tool.objects.filter(created_by=request.user).select_related('item', 'item__category')

    if query:
        alets_qs = alets_qs.filter(item__name__icontains=query) | \
                   alets_qs.filter(item__category__name__icontains=query) | \
                   alets_qs.filter(additional_info__icontains=query) | \
                   alets_qs.filter(manual_name__icontains=query)

    alets = list(alets_qs)
    for alet in alets:
        alet.icon_class = get_tool_icon_for_tool(alet)
        try:
            alet.price_display = abs(float(alet.price))
        except Exception:
            alet.price_display = alet.price

    categories = _ordered_tool_categories()
    
    today = timezone.now().date()
    context = {
        'alets': alets,
        'categories': categories,
        'today': today,
        'yesterday': today - timedelta(days=1),
    }
    return render(request, 'tools/tool_list.html', context)

@login_required
def get_tool_items(request):
    category_id = request.GET.get('category_id')
    category = ToolCategory.objects.filter(id=category_id).first()
    items_qs = ToolItem.objects.filter(category_id=category_id)
    if category:
        items_qs = order_queryset_by_name_list(
            items_qs,
            TOOL_ITEM_ORDER.get(category.name, []),
        )
    items = items_qs.values('id', 'name')
    return JsonResponse(list(items), safe=False)

@login_required
def tool_create(request):
    if request.method == 'POST':
        item_id = request.POST.get('item')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        additional_info = request.POST.get('additional_info')
        date_raw = request.POST.get('date')
        entry_date = _parse_date(date_raw)
        
        # Backend Validation
        if not (item_id or manual_name) or not quantity:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return redirect('tools:tool_list')

        # Handle empty price
        price = price if price and price.strip() else 0

        try:
            quantity_val = int(quantity)
        except (TypeError, ValueError):
            messages.error(request, "Miqdar düzgün deyil.")
            return redirect('tools:tool_list')
        
        try:
            item = None
            if item_id:
                item = ToolItem.objects.get(id=item_id)
                if item.name == "Digər" and not manual_name:
                    messages.error(request, "Zəhmət olmasa, Digər üçün ad daxil edin.")
                    return redirect('tools:tool_list')
            
            if quantity_val < 0:
                available = _tool_stock_total(
                    request.user,
                    item,
                    manual_name if (not item or item.name == "Digər") else None,
                )
                if available < abs(quantity_val):
                    messages.error(request, "Stokda kifayət qədər alət yoxdur.")
                    return redirect('tools:tool_list')

            manual_value = manual_name if (not item or item.name == "Digər") else None
            merged = _merge_manual_tool(request.user, manual_value, quantity_val, price, additional_info, entry_date) if manual_value else None
            if merged == "deleted":
                add_crud_success_message(request, "Tool", "delete")
                return redirect('tools:tool_list')
            if merged:
                add_crud_success_message(request, "Tool", "update")
                return redirect('tools:tool_list')

            tool = Tool.objects.create(
                item=item,
                manual_name=manual_value,
                quantity=quantity,
                price=price,
                additional_info=additional_info,
                date=entry_date,
                created_by=request.user
            )

            if quantity_val < 0:
                try:
                    amount_val = abs(float(price))
                except (TypeError, ValueError):
                    amount_val = 0
                if amount_val <= 0:
                    messages.error(request, "Gəlir üçün məbləğ daxil edin.")
                    tool.delete()
                    return redirect('tools:tool_list')

                Income.objects.create(
                    category="Digər",
                    item_name=item.name if item else manual_name,
                    quantity=abs(quantity_val),
                    unit="ədəd",
                    amount=amount_val,
                    additional_info=additional_info,
                    date=entry_date,
                    created_by=request.user,
                    content_object=tool,
                )

            # Automatic Expense Integration
            if quantity_val > 0 and price and float(price) > 0:
                try:
                    # 'Texnika alışı' is a suitable subcategory, or 'Təmir və Baxım'
                    # But if it's a new tool, 'Texnika alışı' is better.
                    expense_sub = ExpenseSubCategory.objects.get(name='Texnika alışı')
                    Expense.objects.create(
                        title=f"Alət alışı: {item.name if item else manual_name}",
                        amount=price,
                        subcategory=expense_sub,
                        additional_info=additional_info,
                        created_by=request.user,
                        content_object=tool
                    )
                except ExpenseSubCategory.DoesNotExist:
                    # Fallback
                    Expense.objects.create(
                        title=f"Alət alışı: {item.name if item else manual_name}",
                        amount=price,
                        manual_name="Alət alışı (Digər)",
                        additional_info=additional_info,
                        created_by=request.user,
                        content_object=tool
                    )
        except ToolItem.DoesNotExist:
            messages.error(request, "Seçilmiş alət növü tapılmadı.")
        else:
            add_crud_success_message(request, "Tool", "create")

        return redirect('tools:tool_list')
    
    return redirect('tools:tool_list')

@login_required
def tool_update(request, pk):
    tool = get_object_or_404(Tool, pk=pk, created_by=request.user)
    if request.method == 'POST':
        item_id = request.POST.get('item')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        additional_info = request.POST.get('additional_info')
        date_raw = request.POST.get('date')
        entry_date = _parse_date(date_raw)
        
        # Backend Validation
        if not (item_id or manual_name) or not quantity:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return render(request, 'tools/tool_form.html', {
                'alet': tool,
                'categories': _ordered_tool_categories(),
            })

        try:
            quantity_val = int(quantity)
        except (TypeError, ValueError):
            messages.error(request, "Miqdar düzgün deyil.")
            return render(request, 'tools/tool_form.html', {
                'alet': tool,
                'categories': _ordered_tool_categories(),
            })

        prev_quantity = int(tool.quantity)
        prev_item = tool.item
        prev_manual = tool.manual_name

        # Update tool object
        tool.quantity = quantity
        tool.additional_info = additional_info
        tool.date = entry_date
        if item_id:
            item = ToolItem.objects.get(id=item_id)
            if item.name == "Digər" and not manual_name:
                messages.error(request, 'Zəhmət olmasa, Digər üçün ad daxil edin.')
                return render(request, 'tools/tool_form.html', {
                    'alet': tool,
                    'categories': _ordered_tool_categories(),
                })
            tool.manual_name = manual_name if item.name == "Digər" else None
        else:
            tool.manual_name = manual_name
        
        # Handle empty price
        tool.price = price if price and price.strip() else 0
        
        if item_id:
            tool.item = ToolItem.objects.get(id=item_id)
        else:
            tool.item = None

        if quantity_val < 0:
            available = _tool_stock_total(
                request.user,
                tool.item,
                tool.manual_name if (not tool.item or (tool.item and tool.item.name == "Digər")) else None,
            )
            if prev_item == tool.item and prev_manual == tool.manual_name:
                available += prev_quantity
            if available < abs(quantity_val):
                messages.error(request, "Stokda kifayət qədər alət yoxdur.")
                return render(request, 'tools/tool_form.html', {
                    'alet': tool,
                    'categories': _ordered_tool_categories(),
                })
            
        tool.save()

        tool_type = ContentType.objects.get_for_model(Tool)
        linked_income = Income.objects.filter(content_type=tool_type, object_id=tool.id).first()

        if quantity_val < 0:
            try:
                amount_val = abs(float(tool.price))
            except (TypeError, ValueError):
                amount_val = 0
            if linked_income:
                if amount_val > 0:
                    linked_income.category = "Digər"
                    linked_income.item_name = tool.item.name if tool.item else tool.manual_name
                    linked_income.quantity = abs(quantity_val)
                    linked_income.unit = "ədəd"
                    linked_income.amount = amount_val
                    linked_income.additional_info = tool.additional_info
                    linked_income.date = tool.date
                    linked_income.save()
                else:
                    linked_income.delete()
            else:
                if amount_val > 0:
                    Income.objects.create(
                        category="Digər",
                        item_name=tool.item.name if tool.item else tool.manual_name,
                        quantity=abs(quantity_val),
                        unit="ədəd",
                        amount=amount_val,
                        additional_info=tool.additional_info,
                        date=tool.date,
                        created_by=request.user,
                        content_object=tool,
                    )
        else:
            if linked_income:
                linked_income.delete()

        # Update linked Expense if exists
        tool_type = ContentType.objects.get_for_model(Tool)
        linked_expense = Expense.objects.filter(content_type=tool_type, object_id=tool.id).first()
        
        if linked_expense:
            if quantity_val > 0 and tool.price and float(tool.price) > 0:
                linked_expense.amount = tool.price
                linked_expense.title = f"Alət alışı: {tool.item.name if tool.item else tool.manual_name}"
                linked_expense.additional_info = tool.additional_info
                linked_expense.save()
            else:
                linked_expense.delete()
        elif quantity_val > 0 and tool.price and float(tool.price) > 0:
            # Create new expense if price was previously 0 or null
            try:
                expense_sub = ExpenseSubCategory.objects.get(name='Texnika alışı')
                Expense.objects.create(
                    title=f"Alət alışı: {tool.item.name if tool.item else tool.manual_name}",
                    amount=tool.price,
                    subcategory=expense_sub,
                    additional_info=tool.additional_info,
                    created_by=request.user,
                    content_object=tool
                )
            except ExpenseSubCategory.DoesNotExist:
                Expense.objects.create(
                    title=f"Alət alışı: {tool.item.name if tool.item else tool.manual_name}",
                    amount=tool.price,
                    manual_name="Alət alışı (Digər)",
                    additional_info=tool.additional_info,
                    created_by=request.user,
                    content_object=tool
                )

        add_crud_success_message(request, "Tool", "update")
        return redirect('tools:tool_list')
    
    categories = _ordered_tool_categories()
    return render(request, 'tools/tool_form.html', {
        'alet': tool,
        'categories': categories,
    })

@login_required
def tool_delete(request, pk):
    tool = get_object_or_404(Tool, pk=pk, created_by=request.user)
    if request.method == 'POST':
        # Manually delete linked expenses
        tool_type = ContentType.objects.get_for_model(Tool)
        Expense.objects.filter(content_type=tool_type, object_id=tool.id).delete()
        Income.objects.filter(content_type=tool_type, object_id=tool.id).delete()
        tool.delete()
        add_crud_success_message(request, "Tool", "delete")
        return redirect('tools:tool_list')
    return render(request, 'tools/tool_confirm_delete.html', {'alet': tool})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

from .models import Tool, ToolCategory, ToolItem
from .forms import ToolForm
from common.messages import add_crud_success_message
from common.icons import get_tool_icon_for_tool
from expenses.models import Expense, ExpenseSubCategory

@login_required
def tool_list(request):
    query = request.GET.get('q')
    alets_qs = Tool.objects.filter(created_by=request.user).select_related('item', 'item__category')

    if query:
        alets_qs = alets_qs.filter(item__name__icontains=query) | \
                   alets_qs.filter(item__category__name__icontains=query) | \
                   alets_qs.filter(additional_info__icontains=query) | \
                   alets_qs.filter(manual_name__icontains=query)

    alets = list(alets_qs)
    for alet in alets:
        alet.icon_class = get_tool_icon_for_tool(alet)

    categories = ToolCategory.objects.all()
    
    context = {
        'alets': alets,
        'categories': categories,
    }
    return render(request, 'tools/tool_list.html', context)

@login_required
def get_tool_items(request):
    category_id = request.GET.get('category_id')
    items = ToolItem.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse(list(items), safe=False)

@login_required
def tool_create(request):
    if request.method == 'POST':
        item_id = request.POST.get('item')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        manual_name = request.POST.get('manual_name')
        additional_info = request.POST.get('additional_info')
        
        # Backend Validation
        if not (item_id or manual_name) or not quantity:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return redirect('tools:tool_list')

        # Handle empty price
        price = price if price and price.strip() else 0
        
        try:
            item = None
            if item_id:
                item = ToolItem.objects.get(id=item_id)
            
            tool = Tool.objects.create(
                item=item,
                manual_name=manual_name if not item else None,
                quantity=quantity,
                price=price,
                additional_info=additional_info,
                created_by=request.user
            )

            # Automatic Expense Integration
            if price and float(price) > 0:
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
        manual_name = request.POST.get('manual_name')
        additional_info = request.POST.get('additional_info')
        
        # Backend Validation
        if not (item_id or manual_name) or not quantity:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return render(request, 'tools/tool_form.html', {
                'alet': tool,
                'categories': ToolCategory.objects.all(),
            })

        # Update tool object
        tool.quantity = quantity
        tool.additional_info = additional_info
        tool.manual_name = manual_name if not item_id else None
        
        # Handle empty price
        tool.price = price if price and price.strip() else 0
        
        if item_id:
            tool.item = ToolItem.objects.get(id=item_id)
        else:
            tool.item = None
            
        tool.save()

        # Update linked Expense if exists
        tool_type = ContentType.objects.get_for_model(Tool)
        linked_expense = Expense.objects.filter(content_type=tool_type, object_id=tool.id).first()
        
        if linked_expense:
            if tool.price and float(tool.price) > 0:
                linked_expense.amount = tool.price
                linked_expense.title = f"Alət alışı: {tool.item.name if tool.item else tool.manual_name}"
                linked_expense.additional_info = tool.additional_info
                linked_expense.save()
            else:
                linked_expense.delete()
        elif tool.price and float(tool.price) > 0:
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
    
    categories = ToolCategory.objects.all()
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
        tool.delete()
        add_crud_success_message(request, "Tool", "delete")
        return redirect('tools:tool_list')
    return render(request, 'tools/tool_confirm_delete.html', {'alet': tool})

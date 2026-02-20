from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

from .models import Seed, SeedCategory, SeedItem
from .forms import SeedForm
from common.messages import add_crud_success_message
from common.icons import get_seed_icon_for_seed
from expenses.models import Expense, ExpenseSubCategory

@login_required
def seed_list(request):
    query = request.GET.get('q')
    seeds_qs = Seed.objects.filter(created_by=request.user).select_related('item', 'item__category')

    if query:
        seeds_qs = seeds_qs.filter(item__name__icontains=query) | \
                   seeds_qs.filter(item__category__name__icontains=query) | \
                   seeds_qs.filter(additional_info__icontains=query) | \
                   seeds_qs.filter(manual_name__icontains=query)

    seeds = list(seeds_qs)
    for seed in seeds:
        seed.icon_class = get_seed_icon_for_seed(seed)

    categories = SeedCategory.objects.all()
    
    context = {
        'seeds': seeds,
        'categories': categories,
    }
    return render(request, 'seeds/seed_list.html', context)

@login_required
def get_seed_items(request):
    category_id = request.GET.get('category_id')
    items = SeedItem.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse(list(items), safe=False)

@login_required
def seed_create(request):
    if request.method == 'POST':
        item_id = request.POST.get('item')
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        price = request.POST.get('price')
        manual_name = request.POST.get('manual_name')
        additional_info = request.POST.get('additional_info')
        
        # Backend Validation
        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return redirect('seeds:seed_list')

        # Handle empty numeric fields
        price = price if price and price.strip() else 0
        
        try:
            item = None
            if item_id:
                item = SeedItem.objects.get(id=item_id)
            
            seed = Seed.objects.create(
                item=item,
                manual_name=manual_name if not item else None,
                quantity=quantity,
                unit=unit,
                price=price,
                additional_info=additional_info,
                created_by=request.user
            )

            # Automatic Expense Integration
            if price and float(price) > 0:
                try:
                    # Try to find 'Toxumlar' subcategory
                    expense_sub = ExpenseSubCategory.objects.filter(name__icontains='Toxum').first()
                    if expense_sub:
                        Expense.objects.create(
                            title=f"Toxum alışı: {item.name if item else manual_name}",
                            amount=price,
                            subcategory=expense_sub,
                            additional_info=additional_info,
                            created_by=request.user,
                            content_object=seed
                        )
                    else:
                        # Fallback
                        Expense.objects.create(
                            title=f"Toxum alışı: {item.name if item else manual_name}",
                            amount=price,
                            manual_name="Toxum alışı",
                            additional_info=additional_info,
                            created_by=request.user,
                            content_object=seed
                        )
                except Exception as e:
                    # Don't let expense creation failure break seed creation
                    print(f"Error creating seed expense: {e}")
        except SeedItem.DoesNotExist:
            messages.error(request, "Seçilmiş toxum növü tapılmadı.")
        else:
            add_crud_success_message(request, "Seed", "create")

        return redirect('seeds:seed_list')
    
    return redirect('seeds:seed_list')

@login_required
def seed_update(request, pk):
    seed = get_object_or_404(Seed, pk=pk, created_by=request.user)
    if request.method == 'POST':
        item_id = request.POST.get('item')
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        price = request.POST.get('price')
        manual_name = request.POST.get('manual_name')
        additional_info = request.POST.get('additional_info')
        
        # Backend Validation
        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return render(request, 'seeds/seed_form.html', {
                'seed': seed,
                'categories': SeedCategory.objects.all(),
            })

        # Update seed object
        seed.quantity = quantity
        seed.unit = unit
        seed.additional_info = additional_info
        seed.manual_name = manual_name if not item_id else None
        
        # Handle empty price
        seed.price = price if price and price.strip() else 0
        
        if item_id:
            seed.item = SeedItem.objects.get(id=item_id)
        else:
            seed.item = None
            
        seed.save()

        # Update linked Expense if exists
        seed_type = ContentType.objects.get_for_model(Seed)
        linked_expense = Expense.objects.filter(content_type=seed_type, object_id=seed.id).first()
        
        if linked_expense:
            if seed.price and float(seed.price) > 0:
                linked_expense.amount = seed.price
                linked_expense.title = f"Toxum alışı: {seed.item.name if seed.item else seed.manual_name}"
                linked_expense.additional_info = seed.additional_info
                linked_expense.save()
            else:
                linked_expense.delete()
        elif seed.price and float(seed.price) > 0:
            # Create new expense if price was previously 0 or null
            expense_sub = ExpenseSubCategory.objects.filter(name__icontains='Toxum').first()
            if expense_sub:
                Expense.objects.create(
                    title=f"Toxum alışı: {seed.item.name if seed.item else seed.manual_name}",
                    amount=seed.price,
                    subcategory=expense_sub,
                    additional_info=seed.additional_info,
                    created_by=request.user,
                    content_object=seed
                )
            else:
                Expense.objects.create(
                    title=f"Toxum alışı: {seed.item.name if seed.item else seed.manual_name}",
                    amount=seed.price,
                    manual_name="Toxum alışı",
                    additional_info=seed.additional_info,
                    created_by=request.user,
                    content_object=seed
                )

        add_crud_success_message(request, "Seed", "update")
        return redirect('seeds:seed_list')
    
    categories = SeedCategory.objects.all()
    return render(request, 'seeds/seed_form.html', {
        'seed': seed,
        'categories': categories,
    })

@login_required
def seed_delete(request, pk):
    seed = get_object_or_404(Seed, pk=pk, created_by=request.user)
    if request.method == 'POST':
        # Manually delete linked expenses
        seed_type = ContentType.objects.get_for_model(Seed)
        Expense.objects.filter(content_type=seed_type, object_id=seed.id).delete()
        seed.delete()
        add_crud_success_message(request, "Seed", "delete")
        return redirect('seeds:seed_list')
    return render(request, 'seeds/seed_confirm_delete.html', {'seed': seed})

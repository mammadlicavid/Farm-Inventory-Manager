from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Q
import re
from datetime import date, timedelta
from django.utils import timezone

from .models import Animal, AnimalCategory, AnimalSubCategory
from .forms import AnimalForm
from common.messages import add_crud_success_message
from common.text import normalize_manual_label
from common.category_order import (
    ANIMAL_CATEGORY_ORDER,
    ANIMAL_SUBCATEGORY_ORDER,
    order_queryset_by_name_list,
    sort_objects_by_name_list,
)
from common.icons import get_animal_icon_for_animal
from expenses.models import Expense, ExpenseSubCategory

ANIMAL_FORM_CATALOG_CACHE_KEY = "animals:form-catalog:v1"
ANIMAL_FORM_CATALOG_TTL = 300


def _build_subcategory_data(categories):
    payload = {}
    for cat in categories:
        order_list = ANIMAL_SUBCATEGORY_ORDER.get(cat.name, [])
        subs = sort_objects_by_name_list(cat.subcategories.all(), order_list)
        payload[str(cat.id)] = [{"id": sub.id, "name": sub.name} for sub in subs]
    return payload


def _parse_date(value: str | None):
    if not value:
        return timezone.now().date()
    try:
        return date.fromisoformat(value)
    except Exception:
        return timezone.now().date()


def _parse_filter_date(value: str | None):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def _clean_additional_info(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s*\|\s*income:\d+\b", "", value)
    cleaned = re.sub(r"\bincome:\d+\b", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned or None


def _ordered_animal_categories():
    return order_queryset_by_name_list(AnimalCategory.objects.all(), ANIMAL_CATEGORY_ORDER)


def _animal_form_catalog():
    cached = cache.get(ANIMAL_FORM_CATALOG_CACHE_KEY)
    if cached is not None:
        return cached
    categories = list(_ordered_animal_categories().prefetch_related('subcategories'))
    payload = {
        "categories": categories,
        "subcategory_data": _build_subcategory_data(categories),
    }
    cache.set(ANIMAL_FORM_CATALOG_CACHE_KEY, payload, ANIMAL_FORM_CATALOG_TTL)
    return payload


def _sync_animal_related_records(user, animal):
    animal_type = ContentType.objects.get_for_model(Animal)
    linked_expense = Expense.objects.filter(content_type=animal_type, object_id=animal.id).first()
    try:
        price_val = float(animal.price or 0)
    except (TypeError, ValueError):
        price_val = 0

    if animal.quantity > 0 and price_val > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name='Heyvan alışı').first()
        if linked_expense:
            linked_expense.amount = animal.price
            linked_expense.title = f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}"
            linked_expense.additional_info = animal.additional_info
            linked_expense.subcategory = expense_sub
            linked_expense.manual_name = None if expense_sub else "Heyvan alışı (Digər)"
            linked_expense.save()
        else:
            Expense.objects.create(
                title=f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}",
                amount=animal.price,
                subcategory=expense_sub,
                manual_name=None if expense_sub else "Heyvan alışı (Digər)",
                additional_info=animal.additional_info,
                created_by=user,
                content_object=animal
            )
    elif linked_expense:
        linked_expense.delete()


def _merge_manual_animal(user, manual_name, gender, quantity, weight, price, additional_info, entry_date):
    existing = (
        Animal.objects.filter(created_by=user, gender=gender, identification_no__isnull=True)
        .filter((Q(subcategory__isnull=True) | Q(subcategory__name__iexact="Digər")), manual_name__iexact=manual_name)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None

    total_qty = int(existing.quantity) + int(quantity)
    if total_qty == 0:
        animal_type = ContentType.objects.get_for_model(Animal)
        Expense.objects.filter(content_type=animal_type, object_id=existing.id).delete()
        existing.delete()
        return "deleted"

    existing.subcategory = None
    existing.manual_name = manual_name
    existing.quantity = total_qty
    existing.weight = weight
    existing.price = price
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.save()
    _sync_animal_related_records(user, existing)
    return existing

@login_required
def animal_list(request):
    query = (request.GET.get('q') or '').strip()
    category_id = (request.GET.get('category') or '').strip()
    subcategory_id = (request.GET.get('subcategory') or '').strip()
    date_from_raw = (request.GET.get('date_from') or '').strip()
    date_to_raw = (request.GET.get('date_to') or '').strip()
    movement = (request.GET.get('movement') or '').strip()
    animals_qs = (
        Animal.objects.filter(created_by=request.user)
        .exclude(quantity=0)
        .exclude(additional_info__icontains="Gəlir stoku | income:")
        .select_related('subcategory', 'subcategory__category')
        .only(
            'id',
            'quantity',
            'weight',
            'date',
            'gender',
            'identification_no',
            'manual_name',
            'additional_info',
            'price',
            'updated_at',
            'subcategory__id',
            'subcategory__name',
            'subcategory__category__id',
            'subcategory__category__name',
        )
    )

    if query:
        animals_qs = animals_qs.filter(
            Q(identification_no__icontains=query)
            | Q(additional_info__icontains=query)
            | Q(subcategory__name__icontains=query)
            | Q(manual_name__icontains=query)
        )

    selected_category = AnimalCategory.objects.filter(pk=category_id).first() if category_id else None
    if selected_category:
        if (selected_category.name or "").strip().lower() == "digər":
            animals_qs = animals_qs.filter(Q(subcategory__category=selected_category) | Q(subcategory__isnull=True))
        else:
            animals_qs = animals_qs.filter(subcategory__category=selected_category)

    filtered_subcategories = []
    if selected_category:
        filtered_subcategories = sort_objects_by_name_list(
            AnimalSubCategory.objects.filter(category=selected_category),
            ANIMAL_SUBCATEGORY_ORDER.get(selected_category.name, []),
        )

    if subcategory_id:
        animals_qs = animals_qs.filter(subcategory_id=subcategory_id)

    date_from = _parse_filter_date(date_from_raw)
    if date_from:
        animals_qs = animals_qs.filter(date__gte=date_from)

    date_to = _parse_filter_date(date_to_raw)
    if date_to:
        animals_qs = animals_qs.filter(date__lte=date_to)

    if movement == "increase":
        animals_qs = animals_qs.filter(quantity__gt=0)
    elif movement == "decrease":
        animals_qs = animals_qs.filter(quantity__lt=0)

    animals = list(animals_qs)
    for animal in animals:
        animal.icon_class = get_animal_icon_for_animal(animal)
        animal.display_additional_info = _clean_additional_info(animal.additional_info)

    form_catalog = _animal_form_catalog()
    
    today = timezone.now().date()
    context = {
        'animals': animals,
        'categories': form_catalog["categories"],
        'subcategory_data': form_catalog["subcategory_data"],
        'filter_subcategories': filtered_subcategories,
        'selected_category': category_id,
        'selected_subcategory': subcategory_id,
        'selected_date_from': date_from_raw,
        'selected_date_to': date_to_raw,
        'selected_movement': movement,
        'today': today,
        'yesterday': today - timedelta(days=1),
    }
    return render(request, 'animals/animal_list.html', context)

@login_required
def animal_create(request):
    redirect_to = request.POST.get('next') or 'animals:animal_list'
    if request.method == 'POST':
        subcategory_id = request.POST.get('subcategory')
        identification_no = request.POST.get('identification_no')
        quantity_raw = request.POST.get('quantity')
        additional_info = request.POST.get('additional_info')
        gender = request.POST.get('gender')
        weight = request.POST.get('weight')
        price = request.POST.get('price')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        date_raw = request.POST.get('date')
        entry_date = _parse_date(date_raw)
        
        # Backend Validation
        if not (subcategory_id or manual_name) or not gender:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return redirect(redirect_to)

        try:
            quantity = int(quantity_raw or "1")
        except (TypeError, ValueError):
            messages.error(request, "Miqdar düzgün deyil.")
            return redirect(redirect_to)
        if quantity == 0:
            messages.error(request, "Miqdar 0 ola bilməz.")
            return redirect(redirect_to)

        # Handle empty numeric fields
        weight = weight if weight and weight.strip() else None
        price = price if price and price.strip() else 0
        
        if not gender:
            gender = 'erkek'
            
        try:
            subcategory = None
            if subcategory_id:
                subcategory = AnimalSubCategory.objects.get(id=subcategory_id)
                if subcategory.name == "Digər" and not manual_name:
                    messages.error(request, "Zəhmət olmasa, Digər üçün ad daxil edin.")
                    return redirect(redirect_to)

            if abs(quantity) != 1:
                identification_no = None
            elif identification_no:
                if Animal.objects.filter(identification_no=identification_no).exists():
                    messages.error(request, "Bu identifikasiya nömrəsi artıq mövcuddur.")
                    return redirect(redirect_to)
            
            manual_value = manual_name if (not subcategory or subcategory.name == "Digər") else None
            merged = None
            if manual_value and not identification_no:
                merged = _merge_manual_animal(
                    request.user,
                    manual_value,
                    gender,
                    quantity,
                    weight,
                    price,
                    additional_info,
                    entry_date,
                )
            if merged == "deleted":
                add_crud_success_message(request, "Animal", "delete")
                return redirect(redirect_to)
            if merged:
                add_crud_success_message(request, "Animal", "update")
                return redirect(redirect_to)

            animal = Animal.objects.create(
                subcategory=subcategory,
                manual_name=manual_value,
                identification_no=identification_no,
                additional_info=additional_info,
                gender=gender,
                weight=weight,
                price=price,
                quantity=quantity,
                date=entry_date,
                created_by=request.user
            )

            # Automatic Expense Integration
            if price and float(price) > 0:
                try:
                    # 'Heyvan alışı' is the subcategory for animal purchases
                    expense_sub = ExpenseSubCategory.objects.get(name='Heyvan alışı')
                    Expense.objects.create(
                        title=f"Heyvan alışı: {subcategory.name if subcategory else manual_name}",
                        amount=price,
                        subcategory=expense_sub,
                        additional_info=additional_info,
                        created_by=request.user,
                        content_object=animal
                    )
                except ExpenseSubCategory.DoesNotExist:
                    # Fallback if the subcategory doesn't exist
                    Expense.objects.create(
                        title=f"Heyvan alışı: {subcategory.name if subcategory else manual_name}",
                        amount=price,
                        manual_name="Heyvan alışı (Digər)",
                        additional_info=additional_info,
                        created_by=request.user,
                        content_object=animal
                    )
        except AnimalSubCategory.DoesNotExist:
            messages.error(request, "Seçilmiş alt kateqoriya tapılmadı.")
        else:
            add_crud_success_message(request, "Animal", "create")
        return redirect(redirect_to)
    
    return redirect(redirect_to)

@login_required
def animal_update(request, pk):
    animal = get_object_or_404(Animal, pk=pk, created_by=request.user)
    if request.method == 'POST':
        subcategory_id = request.POST.get('subcategory')
        identification_no = request.POST.get('identification_no')
        quantity_raw = request.POST.get('quantity')
        additional_info = request.POST.get('additional_info')
        gender = request.POST.get('gender')
        weight = request.POST.get('weight')
        price = request.POST.get('price')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        date_raw = request.POST.get('date')
        entry_date = _parse_date(date_raw)
        
        # Backend Validation
        if not (subcategory_id or manual_name) or not gender:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            categories = _ordered_animal_categories().prefetch_related('subcategories')
            return render(request, 'animals/animal_form.html', {
                'form': AnimalForm(instance=animal),
                'animal': animal,
                'categories': categories,
                'subcategory_data': _build_subcategory_data(categories),
            })

        try:
            quantity = int(quantity_raw or "1")
        except (TypeError, ValueError):
            messages.error(request, "Miqdar düzgün deyil.")
            categories = _ordered_animal_categories().prefetch_related('subcategories')
            return render(request, 'animals/animal_form.html', {
                'form': AnimalForm(instance=animal),
                'animal': animal,
                'categories': categories,
                'subcategory_data': _build_subcategory_data(categories),
            })
        if quantity == 0:
            messages.error(request, "Miqdar 0 ola bilməz.")
            categories = _ordered_animal_categories().prefetch_related('subcategories')
            return render(request, 'animals/animal_form.html', {
                'form': AnimalForm(instance=animal),
                'animal': animal,
                'categories': categories,
                'subcategory_data': _build_subcategory_data(categories),
            })

        # Update animal object
        if abs(quantity) != 1:
            identification_no = None
        elif identification_no:
            if Animal.objects.filter(identification_no=identification_no).exclude(pk=animal.pk).exists():
                messages.error(request, "Bu identifikasiya nömrəsi artıq mövcuddur.")
                categories = _ordered_animal_categories().prefetch_related('subcategories')
                return render(request, 'animals/animal_form.html', {
                    'form': AnimalForm(instance=animal),
                    'animal': animal,
                    'categories': categories,
                    'subcategory_data': _build_subcategory_data(categories),
                })
        animal.identification_no = identification_no
        animal.quantity = quantity
        animal.additional_info = additional_info
        animal.gender = gender
        animal.date = entry_date
        if subcategory_id:
            subcategory = AnimalSubCategory.objects.get(id=subcategory_id)
            if subcategory.name == "Digər" and not manual_name:
                messages.error(request, 'Zəhmət olmasa, Digər üçün ad daxil edin.')
                categories = _ordered_animal_categories().prefetch_related('subcategories')
                return render(request, 'animals/animal_form.html', {
                    'form': AnimalForm(instance=animal),
                    'animal': animal,
                    'categories': categories,
                    'subcategory_data': _build_subcategory_data(categories),
                })
            animal.manual_name = manual_name if subcategory.name == "Digər" else None
        else:
            animal.manual_name = manual_name
        
        # Handle empty numeric fields
        animal.weight = weight if weight and weight.strip() else None
        animal.price = price if price and price.strip() else 0
        
        if subcategory_id:
            animal.subcategory = AnimalSubCategory.objects.get(id=subcategory_id)
        else:
            animal.subcategory = None
        
        animal.save()

        # Update linked Expense if exists
        animal_type = ContentType.objects.get_for_model(Animal)
        linked_expense = Expense.objects.filter(content_type=animal_type, object_id=animal.id).first()
        
        if linked_expense:
            if animal.price and float(animal.price) > 0:
                linked_expense.amount = animal.price
                linked_expense.title = f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}"
                linked_expense.additional_info = animal.additional_info
                linked_expense.save()
            else:
                linked_expense.delete()
        elif animal.price and float(animal.price) > 0:
            # Create new expense if price was previously 0 or null
            try:
                expense_sub = ExpenseSubCategory.objects.get(name='Heyvan alışı')
                Expense.objects.create(
                    title=f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}",
                    amount=animal.price,
                    subcategory=expense_sub,
                    additional_info=animal.additional_info,
                    created_by=request.user,
                    content_object=animal
                )
            except ExpenseSubCategory.DoesNotExist:
                Expense.objects.create(
                    title=f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}",
                    amount=animal.price,
                    manual_name="Heyvan alışı (Digər)",
                    additional_info=animal.additional_info,
                    created_by=request.user,
                    content_object=animal
                )

        add_crud_success_message(request, "Animal", "update")
        return redirect('animals:animal_list')
    
    categories = _ordered_animal_categories().prefetch_related('subcategories')
    return render(request, 'animals/animal_form.html', {
        'animal': animal,
        'categories': categories,
        'subcategory_data': _build_subcategory_data(categories),
    })

@login_required
def animal_delete(request, pk):
    animal = get_object_or_404(Animal, pk=pk, created_by=request.user)
    if request.method == 'POST':
        animal_type = ContentType.objects.get_for_model(Animal)
        Expense.objects.filter(content_type=animal_type, object_id=animal.id).delete()
        animal.delete()
        add_crud_success_message(request, "Animal", "delete")
    return redirect('animals:animal_list')

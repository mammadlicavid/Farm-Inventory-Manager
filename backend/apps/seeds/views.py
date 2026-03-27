from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from django.utils import timezone

from .models import Seed, SeedCategory, SeedItem
from .forms import SeedForm
from common.messages import add_crud_success_message
from common.text import normalize_manual_label
from common.category_order import (
    SEED_CATEGORY_ORDER,
    SEED_ITEM_ORDER,
    order_queryset_by_name_list,
)
from common.icons import get_seed_icon_for_seed
from expenses.models import Expense, ExpenseSubCategory
from incomes.models import Income

SEED_ITEM_TO_CATEGORY = {
    item.strip().lower(): category_name
    for category_name, items in SEED_ITEM_ORDER.items()
    for item in items
    if item.strip().lower() != "digər"
}

INCOME_SEED_CATEGORY_MAP = {
    "Taxıl toxumları": "Taxıl və Paxlalı Toxumları",
    "Paxlalı toxumları": "Taxıl və Paxlalı Toxumları",
    "Yem bitki toxumları": "Yem və Yağlı Bitki Toxumları",
    "Yağlı bitki toxumları": "Yem və Yağlı Bitki Toxumları",
    "Tərəvəz toxumları": "Tərəvəz və Bostan Toxumları",
    "Bostan toxumları": "Tərəvəz və Bostan Toxumları",
    "Meyvə toxumları": "Meyvə Toxumları",
}

LEGACY_SEED_CATEGORY_ALIASES = {
    "Taxıl və Paxlalı Toxumları": ["Taxıl toxumları", "Paxlalı toxumları"],
    "Yem və Yağlı Bitki Toxumları": ["Yem bitki toxumları", "Yağlı bitki toxumları"],
    "Tərəvəz və Bostan Toxumları": ["Tərəvəz toxumları", "Bostan toxumları"],
    "Meyvə Toxumları": ["Meyvə toxumları"],
}


def _seed_to_kg(value: Decimal, unit: str) -> Decimal:
    if unit == "ton":
        return value * Decimal("1000")
    if unit == "qram":
        return value / Decimal("1000")
    return value


def _seed_stock_kg(user, item, manual_name: str | None) -> Decimal:
    if item:
        qs = Seed.objects.filter(created_by=user, item=item)
    else:
        qs = Seed.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=manual_name,
        )
    total = Decimal("0")
    for seed in qs:
        total += _seed_to_kg(Decimal(seed.quantity), seed.unit)
    return total


def _parse_date(value: str | None):
    if not value:
        return timezone.now().date()
    try:
        return date.fromisoformat(value)
    except Exception:
        return timezone.now().date()


def _seed_category_name_for_item(item) -> str:
    if not item:
        return "Digər"
    try:
        category = item.category
    except SeedCategory.DoesNotExist:
        return "Digər"
    return category.name if category else "Digər"


def _ordered_seed_categories():
    _normalize_seed_catalog()
    return order_queryset_by_name_list(SeedCategory.objects.all(), SEED_CATEGORY_ORDER)


def _normalize_seed_catalog():
    legacy_categories = list(
        SeedCategory.objects.filter(name__in=LEGACY_SEED_CATEGORY_ALIASES.keys()).prefetch_related("items")
    )
    if not legacy_categories:
        return

    canonical_categories = {
        category.name: category
        for category in SeedCategory.objects.filter(name__in=SEED_CATEGORY_ORDER)
    }

    def get_category(name: str):
        category = canonical_categories.get(name)
        if category is None:
            category = SeedCategory.objects.create(name=name)
            canonical_categories[name] = category
        return category

    for legacy_category in legacy_categories:
        target_names = LEGACY_SEED_CATEGORY_ALIASES.get(legacy_category.name, [])
        for item in list(legacy_category.items.all()):
            item_name = (item.name or "").strip()
            lower_name = item_name.lower()

            if lower_name == "digər":
                for target_name in target_names:
                    target_category = get_category(target_name)
                    SeedItem.objects.get_or_create(category=target_category, name="Digər")
                item.delete()
                continue

            target_name = SEED_ITEM_TO_CATEGORY.get(lower_name)
            if not target_name:
                target_name = target_names[0] if target_names else legacy_category.name

            target_category = get_category(target_name)
            existing_item = SeedItem.objects.filter(category=target_category, name=item_name).exclude(pk=item.pk).first()
            if existing_item:
                item.delete()
                continue
            if item.category_id != target_category.id:
                item.category = target_category
                item.save(update_fields=["category"])

        legacy_category.refresh_from_db()
        if not legacy_category.items.exists():
            legacy_category.delete()


def _sync_seed_related_records(user, seed):
    quantity_val = Decimal(str(seed.quantity))
    seed_type = ContentType.objects.get_for_model(Seed)
    linked_income = Income.objects.filter(content_type=seed_type, object_id=seed.id).first()

    if quantity_val < 0:
        try:
            amount_val = abs(float(seed.price))
        except (TypeError, ValueError):
            amount_val = 0

        category_name = _seed_category_name_for_item(seed.item)
        income_category = INCOME_SEED_CATEGORY_MAP.get(category_name, "Digər")
        if linked_income:
            if amount_val > 0:
                linked_income.category = income_category
                linked_income.item_name = seed.item.name if seed.item else seed.manual_name
                linked_income.quantity = abs(quantity_val)
                linked_income.unit = "kq" if seed.unit == "kg" else seed.unit
                linked_income.amount = amount_val
                linked_income.additional_info = seed.additional_info
                linked_income.date = seed.date
                linked_income.save()
            else:
                linked_income.delete()
        elif amount_val > 0:
            Income.objects.create(
                category=income_category,
                item_name=seed.item.name if seed.item else seed.manual_name,
                quantity=abs(quantity_val),
                unit="kq" if seed.unit == "kg" else seed.unit,
                amount=amount_val,
                additional_info=seed.additional_info,
                date=seed.date,
                created_by=user,
                content_object=seed,
            )
    elif linked_income:
        linked_income.delete()

    linked_expense = Expense.objects.filter(content_type=seed_type, object_id=seed.id).first()
    try:
        price_val = float(seed.price or 0)
    except (TypeError, ValueError):
        price_val = 0

    if quantity_val > 0 and price_val > 0:
        expense_sub = ExpenseSubCategory.objects.filter(name__icontains='Toxum').first()
        if linked_expense:
            linked_expense.amount = seed.price
            linked_expense.title = f"Toxum alışı: {seed.item.name if seed.item else seed.manual_name}"
            linked_expense.additional_info = seed.additional_info
            linked_expense.subcategory = expense_sub
            linked_expense.manual_name = None if expense_sub else "Toxum alışı"
            linked_expense.save()
        else:
            Expense.objects.create(
                title=f"Toxum alışı: {seed.item.name if seed.item else seed.manual_name}",
                amount=seed.price,
                subcategory=expense_sub,
                manual_name=None if expense_sub else "Toxum alışı",
                additional_info=seed.additional_info,
                created_by=user,
                content_object=seed
            )
    elif linked_expense:
        linked_expense.delete()


def _merge_manual_seed(user, manual_name, quantity_val, unit, price, additional_info, entry_date):
    existing = (
        Seed.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"), manual_name__iexact=manual_name)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None

    total_kg = _seed_to_kg(Decimal(str(existing.quantity)), existing.unit) + _seed_to_kg(quantity_val, unit)
    if total_kg == 0:
        seed_type = ContentType.objects.get_for_model(Seed)
        Expense.objects.filter(content_type=seed_type, object_id=existing.id).delete()
        Income.objects.filter(content_type=seed_type, object_id=existing.id).delete()
        existing.delete()
        return "deleted"

    existing.item = None
    existing.manual_name = manual_name
    existing.quantity = total_kg
    existing.unit = "kg"
    existing.price = price
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.save()
    _sync_seed_related_records(user, existing)
    return existing

@login_required
def seed_list(request):
    query = (request.GET.get('q') or '').strip()
    seeds_qs = Seed.objects.filter(created_by=request.user).select_related('item', 'item__category')

    if query:
        seeds_qs = seeds_qs.filter(item__name__icontains=query) | \
                   seeds_qs.filter(item__category__name__icontains=query) | \
                   seeds_qs.filter(additional_info__icontains=query) | \
                   seeds_qs.filter(manual_name__icontains=query)

    seeds = list(seeds_qs)
    for seed in seeds:
        seed.icon_class = get_seed_icon_for_seed(seed)
        seed.display_category_name = _seed_category_name_for_item(seed.item)
        try:
            seed.price_display = abs(Decimal(seed.price))
        except Exception:
            seed.price_display = seed.price

    categories = _ordered_seed_categories()
    
    today = timezone.now().date()
    context = {
        'seeds': seeds,
        'categories': categories,
        'today': today,
        'yesterday': today - timedelta(days=1),
    }
    return render(request, 'seeds/seed_list.html', context)

@login_required
def get_seed_items(request):
    _normalize_seed_catalog()
    category_id = request.GET.get('category_id')
    category = SeedCategory.objects.filter(id=category_id).first()
    items_qs = SeedItem.objects.filter(category_id=category_id)
    if category:
        items_qs = order_queryset_by_name_list(
            items_qs,
            SEED_ITEM_ORDER.get(category.name, []),
        )
    items = items_qs.values('id', 'name')
    return JsonResponse(list(items), safe=False)

@login_required
def seed_create(request):
    redirect_to = request.POST.get('next') or 'seeds:seed_list'
    if request.method == 'POST':
        item_id = request.POST.get('item')
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        price = request.POST.get('price')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        additional_info = request.POST.get('additional_info')
        date_raw = request.POST.get('date')
        entry_date = _parse_date(date_raw)

        # Backend Validation
        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return redirect(redirect_to)

        # Handle empty numeric fields
        price = price if price and price.strip() else 0

        try:
            quantity_val = Decimal(str(quantity))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Miqdar düzgün deyil.")
            return redirect(redirect_to)
        
        try:
            item = None
            if item_id:
                item = SeedItem.objects.get(id=item_id)
                if item.name == "Digər" and not manual_name:
                    messages.error(request, "Zəhmət olmasa, Digər üçün ad daxil edin.")
                    return redirect(redirect_to)
            
            if quantity_val < 0:
                available_kg = _seed_stock_kg(
                    request.user,
                    item,
                    manual_name if (not item or item.name == "Digər") else None,
                )
                needed_kg = _seed_to_kg(abs(quantity_val), unit)
                if available_kg < needed_kg:
                    messages.error(request, "Stokda kifayət qədər toxum yoxdur.")
                    return redirect(redirect_to)

            manual_value = manual_name if (not item or item.name == "Digər") else None
            merged = _merge_manual_seed(request.user, manual_value, quantity_val, unit, price, additional_info, entry_date) if manual_value else None
            if merged == "deleted":
                add_crud_success_message(request, "Seed", "delete")
                return redirect(redirect_to)
            if merged:
                add_crud_success_message(request, "Seed", "update")
                return redirect(redirect_to)

            seed = Seed.objects.create(
                item=item,
                manual_name=manual_value,
                quantity=quantity,
                unit=unit,
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
                    seed.delete()
                    return redirect(redirect_to)

                category_name = _seed_category_name_for_item(item)
                income_category = INCOME_SEED_CATEGORY_MAP.get(category_name, "Digər")
                Income.objects.create(
                    category=income_category,
                    item_name=item.name if item else manual_name,
                    quantity=abs(quantity_val),
                    unit="kq" if unit == "kg" else unit,
                    amount=amount_val,
                    additional_info=additional_info,
                    date=entry_date,
                    created_by=request.user,
                    content_object=seed,
                )

            # Automatic Expense Integration
            if quantity_val > 0 and price and float(price) > 0:
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

        return redirect(redirect_to)
        
    return redirect(redirect_to)

@login_required
def seed_update(request, pk):
    seed = get_object_or_404(Seed, pk=pk, created_by=request.user)
    if request.method == 'POST':
        item_id = request.POST.get('item')
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        price = request.POST.get('price')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        additional_info = request.POST.get('additional_info')
        date_raw = request.POST.get('date')
        entry_date = _parse_date(date_raw)
        
        # Backend Validation
        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return render(request, 'seeds/seed_form.html', {
                'seed': seed,
                'categories': _ordered_seed_categories(),
            })

        try:
            quantity_val = Decimal(str(quantity))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Miqdar düzgün deyil.")
            return render(request, 'seeds/seed_form.html', {
                'seed': seed,
                'categories': _ordered_seed_categories(),
            })

        prev_quantity = Decimal(str(seed.quantity))
        prev_unit = seed.unit
        prev_item = seed.item
        prev_manual = seed.manual_name

        # Update seed object
        seed.quantity = quantity
        seed.unit = unit
        seed.additional_info = additional_info
        seed.date = entry_date
        if item_id:
            item = SeedItem.objects.get(id=item_id)
            if item.name == "Digər" and not manual_name:
                messages.error(request, 'Zəhmət olmasa, Digər üçün ad daxil edin.')
                return render(request, 'seeds/seed_form.html', {
                    'seed': seed,
                    'categories': _ordered_seed_categories(),
                })
            seed.manual_name = manual_name if item.name == "Digər" else None
        else:
            seed.manual_name = manual_name
        
        # Handle empty price
        seed.price = price if price and price.strip() else 0
        
        if item_id:
            seed.item = SeedItem.objects.get(id=item_id)
        else:
            seed.item = None
            
        # Prevent negative stock on update
        if quantity_val < 0:
            prev_total = _seed_to_kg(prev_quantity, prev_unit)
            available_kg = _seed_stock_kg(request.user, seed.item, seed.manual_name)
            if prev_item == seed.item and prev_manual == seed.manual_name:
                available_kg += prev_total
            needed_kg = _seed_to_kg(abs(quantity_val), unit)
            if available_kg < needed_kg:
                messages.error(request, "Stokda kifayət qədər toxum yoxdur.")
                return render(request, 'seeds/seed_form.html', {
                    'seed': seed,
                    'categories': _ordered_seed_categories(),
                })

        seed.save()

        seed_type = ContentType.objects.get_for_model(Seed)
        linked_income = Income.objects.filter(content_type=seed_type, object_id=seed.id).first()

        if quantity_val < 0:
            try:
                amount_val = abs(float(seed.price))
            except (TypeError, ValueError):
                amount_val = 0

            category_name = _seed_category_name_for_item(seed.item)
            income_category = INCOME_SEED_CATEGORY_MAP.get(category_name, "Digər")
            if linked_income:
                if amount_val > 0:
                    linked_income.category = income_category
                    linked_income.item_name = seed.item.name if seed.item else seed.manual_name
                    linked_income.quantity = abs(quantity_val)
                    linked_income.unit = "kq" if seed.unit == "kg" else seed.unit
                    linked_income.amount = amount_val
                    linked_income.additional_info = seed.additional_info
                    linked_income.date = seed.date
                    linked_income.save()
                else:
                    linked_income.delete()
            else:
                if amount_val > 0:
                    Income.objects.create(
                        category=income_category,
                        item_name=seed.item.name if seed.item else seed.manual_name,
                        quantity=abs(quantity_val),
                        unit="kq" if seed.unit == "kg" else seed.unit,
                        amount=amount_val,
                        additional_info=seed.additional_info,
                        date=seed.date,
                        created_by=request.user,
                        content_object=seed,
                    )
        else:
            if linked_income:
                linked_income.delete()

        # Update linked Expense if exists
        seed_type = ContentType.objects.get_for_model(Seed)
        linked_expense = Expense.objects.filter(content_type=seed_type, object_id=seed.id).first()
        
        if linked_expense:
            if quantity_val > 0 and seed.price and float(seed.price) > 0:
                linked_expense.amount = seed.price
                linked_expense.title = f"Toxum alışı: {seed.item.name if seed.item else seed.manual_name}"
                linked_expense.additional_info = seed.additional_info
                linked_expense.save()
            else:
                linked_expense.delete()
        elif quantity_val > 0 and seed.price and float(seed.price) > 0:
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
    
    categories = _ordered_seed_categories()
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
        Income.objects.filter(content_type=seed_type, object_id=seed.id).delete()
        seed.delete()
        add_crud_success_message(request, "Seed", "delete")
        return redirect('seeds:seed_list')
    return render(request, 'seeds/seed_confirm_delete.html', {'seed': seed})

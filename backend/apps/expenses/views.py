from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

from .models import Expense, ExpenseCategory, ExpenseSubCategory
from common.messages import add_crud_success_message
from common.icons import get_expense_icon
from common.formatting import format_currency
from common.text import normalize_manual_label
from animals.models import Animal
from farm_products.models import FarmProduct
from seeds.models import Seed
from tools.models import Tool

EXPENSE_FORM_CATALOG_CACHE_KEY = "expenses:form-catalog:v1"
EXPENSE_FORM_CATALOG_TTL = 300


def _build_subcategory_data(categories):
    return {
        str(cat.id): [{"id": sub.id, "name": sub.name} for sub in cat.subcategories.all()]
        for cat in categories
    }


def _build_subcategory_category_lookup(categories):
    lookup = {}
    for category in categories:
        for subcategory in category.subcategories.all():
            lookup[subcategory.name.lower()] = category.name
    return lookup

def _get_display_additional_info(expense: Expense) -> str:
    """
    Return the note to show in UI for 'Əlavə Məlumat'.

    Rules:
    - If the expense is linked to an inventory item that has `additional_info`,
      use that value.
    - Otherwise, use the Expense.additional_info unless it is an old
      auto-generated string starting with "Miqdar:" or "İdentifikasiya No:".
    """
    linked = getattr(expense, "prefetched_content_object", None)
    if linked is None:
        linked = getattr(expense, "content_object", None)
    if linked is not None and hasattr(linked, "additional_info"):
        note = getattr(linked, "additional_info") or ""
        return note.strip()

    raw = expense.additional_info or ""
    stripped = raw.strip()
    if stripped.startswith("Miqdar:") or stripped.startswith("Çəki:") or stripped.startswith("İdentifikasiya No:"):
        return ""
    return raw


def _attach_prefetched_expense_objects(expenses):
    if not expenses:
        return

    content_type_to_ids = {}
    for expense in expenses:
        if expense.content_type_id and expense.object_id:
            content_type_to_ids.setdefault(expense.content_type_id, set()).add(expense.object_id)

    if not content_type_to_ids:
        return

    content_types = {
        content_type.id: content_type
        for content_type in ContentType.objects.filter(id__in=content_type_to_ids.keys())
    }
    model_map = {
        ("animals", "animal"): Animal.objects.select_related("subcategory").only(
            "id", "additional_info", "subcategory__name"
        ),
        ("tools", "tool"): Tool.objects.select_related("item", "item__category").only(
            "id", "additional_info", "manual_name", "item__name", "item__category__name"
        ),
        ("seeds", "seed"): Seed.objects.select_related("item", "item__category").only(
            "id", "additional_info", "manual_name", "item__name", "item__category__name"
        ),
        ("farm_products", "farmproduct"): FarmProduct.objects.select_related("item", "item__category").only(
            "id", "additional_info", "manual_name", "item__name", "item__category__name"
        ),
    }
    loaded_objects = {}

    for content_type_id, object_ids in content_type_to_ids.items():
        content_type = content_types.get(content_type_id)
        if not content_type:
            continue
        key = (content_type.app_label, content_type.model)
        queryset = model_map.get(key)
        if queryset is None:
            continue
        loaded_objects[content_type_id] = {
            obj.pk: obj for obj in queryset.filter(pk__in=object_ids)
        }

    for expense in expenses:
        expense.prefetched_content_object = (
            loaded_objects.get(expense.content_type_id, {}).get(expense.object_id)
        )


def _expense_form_catalog():
    cached = cache.get(EXPENSE_FORM_CATALOG_CACHE_KEY)
    if cached is not None:
        return cached
    categories = list(
        ExpenseCategory.objects.exclude(name="Maliyyə və Digər")
        .prefetch_related('subcategories')
    )
    payload = {
        "categories": categories,
        "subcategory_data": _build_subcategory_data(categories),
        "subcategory_category_lookup": _build_subcategory_category_lookup(categories),
    }
    cache.set(EXPENSE_FORM_CATALOG_CACHE_KEY, payload, EXPENSE_FORM_CATALOG_TTL)
    return payload


def _merge_manual_expense(user, title, amount_val, additional_info):
    existing = (
        Expense.objects.filter(created_by=user, subcategory__isnull=True, manual_name__iexact=title)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None

    new_amount = float(existing.amount) + float(amount_val)
    if new_amount <= 0:
        existing.delete()
        return "deleted"

    existing.title = title
    existing.amount = new_amount
    existing.manual_name = title
    existing.additional_info = additional_info
    existing.save()
    return existing

@login_required
def expense_list(request):
    query = (request.GET.get("q") or "").strip()
    expenses_qs = Expense.objects.filter(created_by=request.user).select_related(
        'subcategory', 'subcategory__category'
    ).only(
        'id',
        'title',
        'amount',
        'manual_name',
        'additional_info',
        'date',
        'updated_at',
        'content_type_id',
        'object_id',
        'subcategory__id',
        'subcategory__name',
        'subcategory__category__id',
        'subcategory__category__name',
    )

    if query:
        expenses_qs = expenses_qs.filter(
            Q(subcategory__name__icontains=query)
            | Q(subcategory__category__name__icontains=query)
            | Q(additional_info__icontains=query)
            | Q(manual_name__icontains=query)
            | Q(title__icontains=query)
        )
    
    # Perform aggregations on QuerySet before converting to list
    total_amount = expenses_qs.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Weekly total calculation on QuerySet
    last_week = timezone.now().date() - timedelta(days=7)
    weekly_total = expenses_qs.filter(date__gte=last_week).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Convert to list for secondary processing (attaching display info)
    expenses = list(expenses_qs)
    _attach_prefetched_expense_objects(expenses)
    form_catalog = _expense_form_catalog()
    subcat_lookup = form_catalog["subcategory_category_lookup"]

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
            match_category_name = None
            if exp.manual_name:
                match_category_name = subcat_lookup.get(exp.manual_name.lower())
            if not match_category_name and exp.title:
                match_category_name = subcat_lookup.get(exp.title.lower())
            if match_category_name:
                exp.display_category_name = match_category_name
            else:
                exp.display_category_name = "Digər"
    
    context = {
        'expenses': expenses,
        'total_amount': total_amount,
        'weekly_total': weekly_total,
        'weekly_total_display': format_currency(weekly_total, 2),
        'categories': form_catalog["categories"],
        'subcategory_data': form_catalog["subcategory_data"],
        'today': timezone.now().date(),
        'yesterday': timezone.now().date() - timedelta(days=1),
    }
    return render(request, 'expenses/expense_list.html', context)

@login_required
def add_expense(request):
    redirect_to = request.POST.get('next') or 'expenses:expense_list'
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
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
            return redirect(redirect_to)

        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = 0
        if amount_val <= 0:
            messages.error(request, 'Məbləğ düzgün deyil.')
            return redirect(redirect_to)
        
        if not title:
            title = subcategory.name if subcategory else manual_name

        if not subcategory:
            merged = _merge_manual_expense(request.user, title, amount_val, additional_info)
            if merged == "deleted":
                add_crud_success_message(request, "Expense", "delete")
                return redirect(redirect_to)
            if merged:
                add_crud_success_message(request, "Expense", "update")
                return redirect(redirect_to)

        Expense.objects.create(
            title=title,
            amount=amount_val,
            subcategory=subcategory,
            manual_name=None if subcategory else title,
            additional_info=additional_info,
            created_by=request.user
        )
        add_crud_success_message(request, "Expense", "create")
        return redirect(redirect_to)
    
    return redirect(redirect_to)

@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, created_by=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        subcategory_id = request.POST.get('subcategory')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        additional_info = request.POST.get('additional_info')
        
        subcategory = None
        if subcategory_id:
            try:
                subcategory = ExpenseSubCategory.objects.get(id=subcategory_id)
            except ExpenseSubCategory.DoesNotExist:
                pass
        
        if not (subcategory or manual_name) or not amount:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            form_catalog = _expense_form_catalog()
            return render(request, 'expenses/expense_form.html', {
                'expense': expense,
                'categories': form_catalog["categories"],
                'subcategory_data': form_catalog["subcategory_data"],
            })

        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = 0
        if amount_val <= 0:
            messages.error(request, 'Məbləğ düzgün deyil.')
            form_catalog = _expense_form_catalog()
            return render(request, 'expenses/expense_form.html', {
                'expense': expense,
                'categories': form_catalog["categories"],
                'subcategory_data': form_catalog["subcategory_data"],
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
    form_catalog = _expense_form_catalog()
    return render(request, 'expenses/expense_form.html', {
        'expense': expense,
        'categories': form_catalog["categories"],
        'subcategory_data': form_catalog["subcategory_data"],
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

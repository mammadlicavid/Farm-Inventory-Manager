from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q, Sum
from hashlib import md5
from django.utils import timezone
from datetime import date, timedelta, time
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.cache import never_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Expense, ExpenseCategory, ExpenseSubCategory
from common.messages import add_crud_success_message
from common.icons import get_expense_icon
from common.formatting import format_currency
from common.text import normalize_manual_label
from common.view_cache import bust_dashboard_related_caches
from animals.models import Animal
from farm_products.models import FarmProduct
from seeds.models import Seed
from tools.models import Tool

EXPENSE_FORM_CATALOG_CACHE_KEY = "expenses:form-catalog:v1"
EXPENSE_FORM_CATALOG_TTL = 300
EXPENSE_LIST_CACHE_TTL = 30
EXPENSE_LIST_BUST_TTL = 60 * 60 * 24 * 30


def _expense_list_bust_key(user_id: int) -> str:
    return f"expenses:list-bust:v1:{user_id}"


def _expense_list_cache_bust_value(user_id: int) -> str:
    return str(cache.get(_expense_list_bust_key(user_id), "0"))


def _bust_expense_list_cache(user_id: int) -> None:
    cache.set(_expense_list_bust_key(user_id), timezone.now().isoformat(), EXPENSE_LIST_BUST_TTL)
    cache.delete(f"inventory:stocks-page:v3:user:{user_id}")
    bust_dashboard_related_caches(user_id)


def _redirect_with_refresh(target) -> object:
    url = resolve_url(target)
    parsed = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != "_ui"]
    query.append(("_ui", str(int(timezone.now().timestamp() * 1000))))
    refreshed_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
    return redirect(refreshed_url)


def _list_query_signature(query_dict) -> str:
    filtered = query_dict.copy()
    filtered.pop("_ui", None)
    return md5(filtered.urlencode().encode()).hexdigest()


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


def _parse_date(value: str | None):
    if not value:
        return timezone.localdate()
    try:
        return date.fromisoformat(value)
    except Exception:
        return timezone.localdate()


def _parse_time(value: str | None):
    if not value:
        return timezone.localtime().time().replace(second=0, microsecond=0)
    try:
        return time.fromisoformat(value)
    except Exception:
        return timezone.localtime().time().replace(second=0, microsecond=0)

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


def _merge_manual_expense(user, title, amount_val, additional_info, entry_date, entry_time):
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
    existing.date = entry_date
    existing.time = entry_time
    existing.save()
    return existing

@login_required
@never_cache
def expense_list(request):
    return redirect(f"{resolve_url('inventory:add_placeholder')}?form=expense")

@login_required
def add_expense(request):
    redirect_to = request.POST.get('next') or f"{resolve_url('inventory:add_placeholder')}?form=expense"
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        subcategory_id = request.POST.get('subcategory')
        additional_info = request.POST.get('additional_info')
        entry_date = _parse_date(request.POST.get("date"))
        entry_time = _parse_time(request.POST.get("time"))
        
        subcategory = None
        if subcategory_id:
            try:
                subcategory = ExpenseSubCategory.objects.get(id=subcategory_id)
            except ExpenseSubCategory.DoesNotExist:
                pass
        
        if not (subcategory or manual_name) or not amount:
            messages.error(request, _("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun."))
            return redirect(redirect_to)

        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = 0
        if amount_val <= 0:
            messages.error(request, _("Məbləğ düzgün deyil."))
            return redirect(redirect_to)
        
        if not title:
            title = subcategory.name if subcategory else manual_name

        if not subcategory:
            merged = _merge_manual_expense(request.user, title, amount_val, additional_info, entry_date, entry_time)
            if merged == "deleted":
                _bust_expense_list_cache(request.user.pk)
                add_crud_success_message(request, "Expense", "delete")
                return _redirect_with_refresh(redirect_to)
            if merged:
                _bust_expense_list_cache(request.user.pk)
                add_crud_success_message(request, "Expense", "update")
                return _redirect_with_refresh(redirect_to)

        Expense.objects.create(
            title=title,
            amount=amount_val,
            subcategory=subcategory,
            manual_name=None if subcategory else title,
            additional_info=additional_info,
            date=entry_date,
            time=entry_time,
            created_by=request.user
        )
        _bust_expense_list_cache(request.user.pk)
        add_crud_success_message(request, "Expense", "create")
        return _redirect_with_refresh(redirect_to)
    
    return redirect(redirect_to)

@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, created_by=request.user)
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    redirect_to = next_url or f"{resolve_url('inventory:add_placeholder')}?form=expense"
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        subcategory_id = request.POST.get('subcategory')
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        additional_info = request.POST.get('additional_info')
        entry_date = _parse_date(request.POST.get("date"))
        entry_time = _parse_time(request.POST.get("time"))
        
        subcategory = None
        if subcategory_id:
            try:
                subcategory = ExpenseSubCategory.objects.get(id=subcategory_id)
            except ExpenseSubCategory.DoesNotExist:
                pass
        
        if not (subcategory or manual_name) or not amount:
            messages.error(request, _("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun."))
            form_catalog = _expense_form_catalog()
            return render(request, 'expenses/expense_form.html', {
                'expense': expense,
                'categories': form_catalog["categories"],
                'subcategory_data': form_catalog["subcategory_data"],
                'next_url': next_url,
            })

        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = 0
        if amount_val <= 0:
            messages.error(request, _("Məbləğ düzgün deyil."))
            form_catalog = _expense_form_catalog()
            return render(request, 'expenses/expense_form.html', {
                'expense': expense,
                'categories': form_catalog["categories"],
                'subcategory_data': form_catalog["subcategory_data"],
                'next_url': next_url,
            })
            
        expense.title = title if title else (subcategory.name if subcategory else manual_name)
        expense.amount = amount_val
        expense.subcategory = subcategory
        expense.manual_name = None if subcategory else (title if title else manual_name)
        expense.additional_info = additional_info
        expense.date = entry_date
        expense.time = entry_time
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
            if hasattr(item, 'date'):
                item.date = entry_date
            if hasattr(item, 'time'):
                item.time = entry_time
            
            # Optionally update title/name if it changed? 
            # Usually inventory name is more specific, so we might keep it.
            # But we should at least sync the price.
            item.save()
        
        _bust_expense_list_cache(request.user.pk)
        add_crud_success_message(request, "Expense", "update")
        return _redirect_with_refresh(redirect_to)

    # Initial GET render: compute display_additional_info for textarea
    expense.display_additional_info = _get_display_additional_info(expense)
    form_catalog = _expense_form_catalog()
    return render(request, 'expenses/expense_form.html', {
        'expense': expense,
        'categories': form_catalog["categories"],
        'subcategory_data': form_catalog["subcategory_data"],
        'next_url': next_url,
    })

@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, created_by=request.user)
    redirect_to = request.POST.get("next") or f"{resolve_url('inventory:add_placeholder')}?form=expense"
    if request.method == 'POST':
        # Reverse Synchronization: Deleting expense deletes the linked item
        if expense.content_object:
            expense.content_object.delete()
        
        expense.delete()
        _bust_expense_list_cache(request.user.pk)
        add_crud_success_message(request, "Expense", "delete")
    return _redirect_with_refresh(redirect_to)

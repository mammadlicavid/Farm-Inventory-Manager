from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Q
from django.views.decorators.cache import never_cache
from hashlib import md5
import re
from datetime import date, timedelta, time
from django.utils import timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Animal, AnimalCategory, AnimalSubCategory
from .forms import AnimalForm
from common.messages import add_crud_success_message
from common.text import normalize_manual_label
from common.view_cache import bust_dashboard_related_caches
from common.zero_price_source import (
    ZERO_PRICE_SOURCE_CHOICES,
    get_zero_price_source_label,
    is_blank_or_zero_price,
    normalize_zero_price_source,
)
from common.category_order import (
    ANIMAL_CATEGORY_ORDER,
    ANIMAL_SUBCATEGORY_ORDER,
    order_queryset_by_name_list,
    sort_objects_by_name_list,
)
from common.icons import get_animal_icon_for_animal
from expenses.models import Expense, ExpenseSubCategory

ANIMAL_FORM_CATALOG_CACHE_KEY = "animals:form-catalog:v1"
ANIMAL_FORM_CATALOG_TTL = 3600
ANIMAL_LIST_CACHE_TTL = 180
ANIMAL_LIST_BUST_TTL = 60 * 60 * 24 * 30


def _animal_list_bust_key(user_id: int) -> str:
    return f"animals:list-bust:v1:{user_id}"


def _animal_list_cache_bust_value(user_id: int) -> str:
    return str(cache.get(_animal_list_bust_key(user_id), "0"))


def _bust_animal_list_cache(user_id: int) -> None:
    cache.set(_animal_list_bust_key(user_id), timezone.now().isoformat(), ANIMAL_LIST_BUST_TTL)
    cache.delete(f"inventory:stocks-page:v3:user:{user_id}")
    bust_dashboard_related_caches(user_id)


def _list_query_signature(query_dict) -> str:
    filtered = query_dict.copy()
    filtered.pop("_ui", None)
    return md5(filtered.urlencode().encode()).hexdigest()


def _redirect_with_refresh(target) -> object:
    url = resolve_url(target)
    parsed = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != "_ui"]
    query.append(("_ui", str(int(timezone.now().timestamp() * 1000))))
    refreshed_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
    return redirect(refreshed_url)


def _build_subcategory_data(categories):
    payload = {}
    for cat in categories:
        order_list = ANIMAL_SUBCATEGORY_ORDER.get(cat.name, [])
        subs = sort_objects_by_name_list(cat.subcategories.all(), order_list)
        payload[str(cat.id)] = [{"id": sub.id, "name": sub.name} for sub in subs]
    return payload


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


def _animal_form_context(animal):
    categories = _ordered_animal_categories().prefetch_related('subcategories')
    return {
        'animal': animal,
        'categories': categories,
        'subcategory_data': _build_subcategory_data(categories),
        'zero_price_source_choices': ZERO_PRICE_SOURCE_CHOICES,
    }


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
            linked_expense.date = animal.date
            linked_expense.time = animal.time
            linked_expense.save()
        else:
            Expense.objects.create(
                title=f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}",
                amount=animal.price,
                subcategory=expense_sub,
                manual_name=None if expense_sub else "Heyvan alışı (Digər)",
                additional_info=animal.additional_info,
                date=animal.date,
                time=animal.time,
                created_by=user,
                content_object=animal
            )
    elif linked_expense:
        linked_expense.delete()


def _merge_manual_animal(user, manual_name, gender, quantity, weight, price, zero_price_source, additional_info, entry_date, entry_time):
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
    existing.zero_price_source = zero_price_source
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.time = entry_time
    existing.save()
    _sync_animal_related_records(user, existing)
    return existing

@login_required
@never_cache
def animal_list(request):
    return redirect(f"{resolve_url('inventory:add_placeholder')}?type=animal")

@login_required
def animal_create(request):
    redirect_to = request.POST.get('next') or f"{resolve_url('inventory:add_placeholder')}?type=animal"
    if request.method == 'POST':
        subcategory_id = request.POST.get('subcategory')
        identification_no = request.POST.get('identification_no')
        quantity_raw = request.POST.get('quantity')
        additional_info = request.POST.get('additional_info')
        gender = request.POST.get('gender')
        weight = request.POST.get('weight')
        price = request.POST.get('price')
        zero_price_source = normalize_zero_price_source(request.POST.get('zero_price_source'))
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        date_raw = request.POST.get('date')
        entry_date = _parse_date(date_raw)
        entry_time = _parse_time(request.POST.get("time"))
        
        # Backend Validation
        if not (subcategory_id or manual_name) or not gender:
            messages.error(request, _("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun."))
            return redirect(redirect_to)

        try:
            quantity = int(quantity_raw or "1")
        except (TypeError, ValueError):
            messages.error(request, _("Miqdar düzgün deyil."))
            return redirect(redirect_to)
        if quantity == 0:
            messages.error(request, _("Miqdar 0 ola bilməz."))
            return redirect(redirect_to)

        # Handle empty numeric fields
        weight = weight if weight and weight.strip() else None
        price = price if price and price.strip() else 0
        if quantity > 0 and is_blank_or_zero_price(price) and not zero_price_source:
            messages.error(request, _("Məbləğ 0 olduqda bu stokun haradan gəldiyini seçin."))
            return redirect(redirect_to)
        if quantity <= 0 or not is_blank_or_zero_price(price):
            zero_price_source = None
        
        if not gender:
            gender = 'erkek'
            
        try:
            subcategory = None
            if subcategory_id:
                subcategory = AnimalSubCategory.objects.get(id=subcategory_id)
                if subcategory.name == "Digər" and not manual_name:
                    messages.error(request, _("Zəhmət olmasa, Digər üçün ad daxil edin."))
                    return redirect(redirect_to)

            if abs(quantity) != 1:
                identification_no = None
            elif identification_no:
                if Animal.objects.filter(identification_no=identification_no).exists():
                    messages.error(request, _("Bu identifikasiya nömrəsi artıq mövcuddur."))
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
                    zero_price_source,
                    additional_info,
                    entry_date,
                    entry_time,
                )
            if merged == "deleted":
                _bust_animal_list_cache(request.user.pk)
                add_crud_success_message(request, "Animal", "delete")
                return _redirect_with_refresh(redirect_to)
            if merged:
                _bust_animal_list_cache(request.user.pk)
                add_crud_success_message(request, "Animal", "update")
                return _redirect_with_refresh(redirect_to)

            animal = Animal.objects.create(
                subcategory=subcategory,
                manual_name=manual_value,
                identification_no=identification_no,
                additional_info=additional_info,
                gender=gender,
                weight=weight,
                price=price,
                zero_price_source=zero_price_source,
                quantity=quantity,
                date=entry_date,
                time=entry_time,
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
                        date=entry_date,
                        time=entry_time,
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
                        date=entry_date,
                        time=entry_time,
                        created_by=request.user,
                        content_object=animal
                    )
        except AnimalSubCategory.DoesNotExist:
            messages.error(request, _("Seçilmiş alt kateqoriya tapılmadı."))
        else:
            _bust_animal_list_cache(request.user.pk)
            add_crud_success_message(request, "Animal", "create")
        return _redirect_with_refresh(redirect_to)
    
    return redirect(redirect_to)

@login_required
def animal_update(request, pk):
    animal = get_object_or_404(Animal, pk=pk, created_by=request.user)
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    redirect_to = next_url or f"{resolve_url('inventory:add_placeholder')}?type=animal"
    if request.method == 'POST':
        subcategory_id = request.POST.get('subcategory')
        identification_no = request.POST.get('identification_no')
        quantity_raw = request.POST.get('quantity')
        additional_info = request.POST.get('additional_info')
        gender = request.POST.get('gender')
        weight = request.POST.get('weight')
        price = request.POST.get('price')
        zero_price_source = normalize_zero_price_source(request.POST.get('zero_price_source'))
        manual_name = normalize_manual_label(request.POST.get('manual_name'))
        date_raw = request.POST.get('date')
        entry_date = _parse_date(date_raw)
        entry_time = _parse_time(request.POST.get("time"))
        
        # Backend Validation
        if not (subcategory_id or manual_name) or not gender:
            messages.error(request, _("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun."))
            return render(request, 'animals/animal_form.html', _animal_form_context(animal))

        try:
            quantity = int(quantity_raw or "1")
        except (TypeError, ValueError):
            messages.error(request, _("Miqdar düzgün deyil."))
            return render(request, 'animals/animal_form.html', _animal_form_context(animal))
        if quantity == 0:
            messages.error(request, _("Miqdar 0 ola bilməz."))
            return render(request, 'animals/animal_form.html', _animal_form_context(animal))

        # Update animal object
        if abs(quantity) != 1:
            identification_no = None
        elif identification_no:
            if Animal.objects.filter(identification_no=identification_no).exclude(pk=animal.pk).exists():
                messages.error(request, _("Bu identifikasiya nömrəsi artıq mövcuddur."))
                return render(request, 'animals/animal_form.html', _animal_form_context(animal))
        animal.identification_no = identification_no
        animal.quantity = quantity
        animal.additional_info = additional_info
        animal.gender = gender
        animal.date = entry_date
        animal.time = entry_time
        if subcategory_id:
            subcategory = AnimalSubCategory.objects.get(id=subcategory_id)
            if subcategory.name == "Digər" and not manual_name:
                messages.error(request, _("Zəhmət olmasa, Digər üçün ad daxil edin."))
                return render(request, 'animals/animal_form.html', _animal_form_context(animal))
            animal.manual_name = manual_name if subcategory.name == "Digər" else None
        else:
            animal.manual_name = manual_name
        
        # Handle empty numeric fields
        animal.weight = weight if weight and weight.strip() else None
        animal.price = price if price and price.strip() else 0
        if quantity > 0 and is_blank_or_zero_price(price) and not zero_price_source:
            messages.error(request, _("Məbləğ 0 olduqda bu stokun haradan gəldiyini seçin."))
            return render(request, 'animals/animal_form.html', _animal_form_context(animal))
        animal.zero_price_source = zero_price_source if quantity > 0 and is_blank_or_zero_price(animal.price) else None
        
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
                linked_expense.date = animal.date
                linked_expense.time = animal.time
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
                    date=animal.date,
                    time=animal.time,
                    created_by=request.user,
                    content_object=animal
                )
            except ExpenseSubCategory.DoesNotExist:
                Expense.objects.create(
                    title=f"Heyvan alışı: {animal.subcategory.name if animal.subcategory else animal.manual_name}",
                    amount=animal.price,
                    manual_name="Heyvan alışı (Digər)",
                    additional_info=animal.additional_info,
                    date=animal.date,
                    time=animal.time,
                    created_by=request.user,
                    content_object=animal
                )

        _bust_animal_list_cache(request.user.pk)
        add_crud_success_message(request, "Animal", "update")
        return _redirect_with_refresh(redirect_to)
    
    context = _animal_form_context(animal)
    context["next_url"] = next_url
    return render(request, 'animals/animal_form.html', context)

@login_required
def animal_delete(request, pk):
    animal = get_object_or_404(Animal, pk=pk, created_by=request.user)
    redirect_to = request.POST.get("next") or f"{resolve_url('inventory:add_placeholder')}?type=animal"
    if request.method == 'POST':
        animal_type = ContentType.objects.get_for_model(Animal)
        Expense.objects.filter(content_type=animal_type, object_id=animal.id).delete()
        animal.delete()
        _bust_animal_list_cache(request.user.pk)
        add_crud_success_message(request, "Animal", "delete")
    return _redirect_with_refresh(redirect_to)

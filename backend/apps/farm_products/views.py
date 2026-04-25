from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.cache import cache
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta, time
from hashlib import md5
from django.utils import timezone
from django.views.decorators.cache import never_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import FarmProduct, FarmProductCategory, FarmProductItem
from common.messages import add_crud_success_message
from common.category_order import (
    FARM_PRODUCT_CATEGORY_ORDER,
    FARM_PRODUCT_ITEM_ORDER,
    order_queryset_by_name_list,
)
from common.icons import get_farm_product_icon_for_product
from common.text import normalize_manual_label
from common.view_cache import bust_dashboard_related_caches
from common.zero_price_source import (
    ZERO_PRICE_SOURCE_CHOICES,
    get_zero_price_source_label,
    is_blank_or_zero_price,
    normalize_zero_price_source,
)
from expenses.models import Expense, ExpenseCategory, ExpenseSubCategory
from incomes.models import Income

FARM_FORM_CATALOG_CACHE_KEY = "farm-products:form-catalog:v1"
FARM_FORM_CATALOG_TTL = 3600
FARM_LIST_CACHE_TTL = 180
FARM_LIST_BUST_TTL = 60 * 60 * 24 * 30


def _farm_list_bust_key(user_id: int) -> str:
    return f"farm-products:list-bust:v1:{user_id}"


def _farm_list_cache_bust_value(user_id: int) -> str:
    return str(cache.get(_farm_list_bust_key(user_id), "0"))


def _bust_farm_list_cache(user_id: int) -> None:
    cache.set(_farm_list_bust_key(user_id), timezone.now().isoformat(), FARM_LIST_BUST_TTL)
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


def _is_forage_item(name: str) -> bool:
    return (name or "").strip().lower() in {"yonca", "koronilla", "seradella"}


def _farm_base_unit(unit: str) -> str:
    if unit in {"kq", "ton", "qram"}:
        return "kq"
    if unit in {"litr", "ml"}:
        return "litr"
    return unit


def _farm_to_base(value: Decimal, unit: str, base_unit: str) -> Decimal:
    if base_unit == "kq":
        if unit == "ton":
            return value * Decimal("1000")
        if unit == "qram":
            return value / Decimal("1000")
        return value
    if base_unit == "litr":
        if unit == "ml":
            return value / Decimal("1000")
        return value
    return value


def _farm_form_catalog():
    cached = cache.get(FARM_FORM_CATALOG_CACHE_KEY)
    if cached is not None:
        return cached
    categories = list(
        order_queryset_by_name_list(
            FarmProductCategory.objects.all(),
            FARM_PRODUCT_CATEGORY_ORDER,
        )
    )
    item_map = {}
    for category in categories:
        items = list(
            order_queryset_by_name_list(
                FarmProductItem.objects.filter(category=category),
                FARM_PRODUCT_ITEM_ORDER.get(category.name, []),
            )
        )
        item_map[str(category.id)] = [
            {"id": item.id, "name": item.name, "unit": item.unit}
            for item in items
        ]
    payload = {"categories": categories, "item_map": item_map}
    cache.set(FARM_FORM_CATALOG_CACHE_KEY, payload, FARM_FORM_CATALOG_TTL)
    return payload


def _farm_form_context(product):
    catalog = _farm_form_catalog()
    return {
        "product": product,
        "categories": catalog["categories"],
        "category_item_map": catalog["item_map"],
        "zero_price_source_choices": ZERO_PRICE_SOURCE_CHOICES,
    }


def _farm_stock_base(user, item, manual_name: str | None, base_unit: str) -> Decimal:
    from django.db.models import Case, DecimalField, F, Sum, Value, When

    if item:
        qs = FarmProduct.objects.filter(created_by=user, item=item)
    else:
        qs = FarmProduct.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=manual_name,
        )

    if base_unit == "bağlama":
        return (
            qs.filter(unit="bağlama")
            .aggregate(total=Sum("quantity"))
            .get("total")
        ) or Decimal("0")
    elif base_unit == "kq":
        expr = Sum(
            Case(
                When(unit="ton", then=F("quantity") * Value(Decimal("1000"))),
                When(unit="qram", then=F("quantity") / Value(Decimal("1000"))),
                When(unit="kq", then=F("quantity")),
                output_field=DecimalField(max_digits=14, decimal_places=4),
            )
        )
        return (
            qs.filter(unit__in=["kq", "ton", "qram"])
            .aggregate(total=expr)
            .get("total")
        ) or Decimal("0")
    elif base_unit == "litr":
        expr = Sum(
            Case(
                When(unit="ml", then=F("quantity") / Value(Decimal("1000"))),
                When(unit="litr", then=F("quantity")),
                output_field=DecimalField(max_digits=14, decimal_places=4),
            )
        )
        return (
            qs.filter(unit__in=["litr", "ml"])
            .aggregate(total=expr)
            .get("total")
        ) or Decimal("0")
    else:
        return (
            qs.filter(unit=base_unit)
            .aggregate(total=Sum("quantity"))
            .get("total")
        ) or Decimal("0")


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


def _farm_expense_title(item_name: str | None) -> str:
    return f"Hazır məhsul alışı: {item_name or ''}".strip()


def _sync_farm_product_related_records(user, product):
    quantity_val = Decimal(str(product.quantity))
    product_type = ContentType.objects.get_for_model(FarmProduct)
    linked_income = Income.objects.filter(content_type=product_type, object_id=product.id).first()

    if quantity_val < 0:
        try:
            amount_val = abs(float(product.price))
        except (TypeError, ValueError):
            amount_val = 0

        category_name = product.item.category.name if product.item and product.item.category else "Digər"
        if linked_income:
            if amount_val > 0:
                linked_income.category = category_name
                linked_income.item_name = product.item.name if product.item else product.manual_name
                linked_income.quantity = abs(quantity_val)
                linked_income.unit = product.unit
                linked_income.amount = amount_val
                linked_income.additional_info = product.additional_info
                linked_income.date = product.date
                linked_income.time = product.time
                linked_income.save()
            else:
                linked_income.delete()
        elif amount_val > 0:
            Income.objects.create(
                category=category_name,
                item_name=product.item.name if product.item else product.manual_name,
                quantity=abs(quantity_val),
                unit=product.unit,
                amount=amount_val,
                additional_info=product.additional_info,
                date=product.date,
                time=product.time,
                created_by=user,
                content_object=product,
            )
    elif linked_income:
        linked_income.delete()

    linked_expense = Expense.objects.filter(content_type=product_type, object_id=product.id).first()
    try:
        price_val = float(product.price or 0)
    except (TypeError, ValueError):
        price_val = 0

    if quantity_val > 0 and price_val > 0:
        item_name = product.item.name if product.item else product.manual_name
        category_name = product.item.category.name if product.item and product.item.category else None
        subcat = _resolve_expense_subcategory(category_name)
        title = _farm_expense_title(item_name)
        if linked_expense:
            linked_expense.amount = product.price
            linked_expense.title = title
            linked_expense.additional_info = product.additional_info
            linked_expense.subcategory = subcat
            linked_expense.manual_name = None if subcat else title
            linked_expense.date = product.date
            linked_expense.time = product.time
            linked_expense.save()
        else:
            Expense.objects.create(
                title=title,
                amount=product.price,
                subcategory=subcat,
                manual_name=None if subcat else title,
                additional_info=product.additional_info,
                date=product.date,
                time=product.time,
                created_by=user,
                content_object=product,
            )
    elif linked_expense:
        linked_expense.delete()


def _merge_manual_farm_product(user, manual_name, quantity_val, unit, price, zero_price_source, additional_info, entry_date, entry_time):
    existing = (
        FarmProduct.objects.filter(created_by=user)
        .filter(Q(item__isnull=True) | Q(item__name__iexact="Digər"), manual_name__iexact=manual_name, unit=unit)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if not existing:
        return None

    total_qty = Decimal(str(existing.quantity)) + Decimal(str(quantity_val))
    if total_qty == 0:
        product_type = ContentType.objects.get_for_model(FarmProduct)
        Expense.objects.filter(content_type=product_type, object_id=existing.id).delete()
        Income.objects.filter(content_type=product_type, object_id=existing.id).delete()
        existing.delete()
        return "deleted"

    existing.item = None
    existing.manual_name = manual_name
    existing.quantity = total_qty
    existing.unit = unit
    existing.price = price
    existing.zero_price_source = zero_price_source
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.time = entry_time
    existing.save()
    _sync_farm_product_related_records(user, existing)
    return existing


@login_required
@never_cache
def farm_product_list(request):
    return redirect(f"{resolve_url('inventory:add_placeholder')}?type=farm")


@login_required
def get_farm_product_items(request):
    category_id = request.GET.get("category_id")
    category = None
    if category_id:
        category = FarmProductCategory.objects.filter(id=category_id).first()
        if category and category.name.startswith("Digər"):
            return JsonResponse([], safe=False)
    items_qs = FarmProductItem.objects.filter(category_id=category_id)
    if category:
        order_list = FARM_PRODUCT_ITEM_ORDER.get(category.name, [])
        items_qs = order_queryset_by_name_list(items_qs, order_list)
    items = items_qs.values("id", "name", "unit")
    return JsonResponse(list(items), safe=False)


@login_required
def farm_product_create(request):
    redirect_to = request.POST.get("next") or f"{resolve_url('inventory:add_placeholder')}?type=farm"
    if request.method == "POST":
        item_id = request.POST.get("item")
        quantity = request.POST.get("quantity")
        unit = request.POST.get("unit")
        price = request.POST.get("price")
        zero_price_source = normalize_zero_price_source(request.POST.get("zero_price_source"))
        manual_name = normalize_manual_label(request.POST.get("manual_name"))
        additional_info = request.POST.get("additional_info")
        date_raw = request.POST.get("date")
        entry_date = _parse_date(date_raw)
        entry_time = _parse_time(request.POST.get("time"))

        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, _("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun."))
            return redirect(redirect_to)

        price = price if price and price.strip() else 0
        try:
            quantity_val = Decimal(str(quantity))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, _("Miqdar düzgün deyil."))
            return redirect(redirect_to)
        if quantity_val > 0 and is_blank_or_zero_price(price) and not zero_price_source:
            messages.error(request, _("Məbləğ 0 olduqda bu stokun haradan gəldiyini seçin."))
            return redirect(redirect_to)
        if quantity_val <= 0 or not is_blank_or_zero_price(price):
            zero_price_source = None

        def allowed_units_for_item(item_obj):
            forage_items = {"yonca", "koronilla", "seradella"}
            if not item_obj or not item_obj.unit:
                return {"kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"}
            if (item_obj.name or "").strip().lower() in forage_items:
                return {"kq", "bağlama"}
            if item_obj.unit == "kq":
                return {"kq", "ton", "qram"}
            if item_obj.unit == "litr":
                return {"litr", "ml"}
            return {item_obj.unit}

        try:
            item = None
            if item_id:
                item = FarmProductItem.objects.get(id=item_id)

            effective_unit = unit
            effective_manual = manual_name if not item else None
            if item and item.name == "Digər":
                if not manual_name:
                    messages.error(request, _("Zəhmət olmasa, Digər üçün ad daxil edin."))
                    return redirect(redirect_to)
                effective_manual = manual_name
            if item:
                allowed_units = allowed_units_for_item(item)
                if unit not in allowed_units:
                    messages.error(request, _("Ölçü vahidi bu kateqoriya üçün uyğun deyil."))
                    return redirect(redirect_to)
                if item.unit and item.unit not in {"kq", "litr"}:
                    effective_unit = item.unit
                if item.unit and item.unit in {"kq", "litr"}:
                    effective_unit = unit
                if (item.name or "").strip().lower() in {"yonca", "koronilla", "seradella"}:
                    effective_unit = unit
                effective_manual = None if item.name != "Digər" else effective_manual

            if quantity_val < 0:
                base_unit = "bağlama" if (item and _is_forage_item(item.name) and effective_unit == "bağlama") else _farm_base_unit(effective_unit)
                available_base = _farm_stock_base(
                    request.user,
                    item,
                    effective_manual if (not item or item.name == "Digər") else None,
                    base_unit,
                )
                needed_base = _farm_to_base(abs(quantity_val), effective_unit, base_unit)
                if available_base < needed_base:
                    messages.error(request, _("Stokda kifayət qədər məhsul yoxdur."))
                    return redirect(redirect_to)

            merged = _merge_manual_farm_product(
                request.user,
                effective_manual,
                quantity_val,
                effective_unit,
                price,
                zero_price_source,
                additional_info,
                entry_date,
                entry_time,
            ) if effective_manual else None
            if merged == "deleted":
                _bust_farm_list_cache(request.user.pk)
                add_crud_success_message(request, "FarmProduct", "delete")
                return _redirect_with_refresh(redirect_to)
            if merged:
                _bust_farm_list_cache(request.user.pk)
                add_crud_success_message(request, "FarmProduct", "update")
                return _redirect_with_refresh(redirect_to)

            product = FarmProduct.objects.create(
                item=item,
                manual_name=effective_manual,
                quantity=quantity,
                unit=effective_unit,
                price=price,
                zero_price_source=zero_price_source,
                additional_info=additional_info,
                date=entry_date,
                time=entry_time,
                created_by=request.user,
            )

            if quantity_val < 0:
                try:
                    amount_val = abs(float(price))
                except (TypeError, ValueError):
                    amount_val = 0
                if amount_val <= 0:
                    messages.error(request, _("Gəlir üçün məbləğ daxil edin."))
                    product.delete()
                    return redirect(redirect_to)

                category_name = item.category.name if item and item.category else "Digər"
                Income.objects.create(
                    category=category_name,
                    item_name=item.name if item else effective_manual,
                    quantity=abs(quantity_val),
                    unit=effective_unit,
                    amount=amount_val,
                    additional_info=additional_info,
                    date=entry_date,
                    time=entry_time,
                    created_by=request.user,
                    content_object=product,
                )

            if quantity_val > 0 and price and float(price) > 0:
                item_name = item.name if item else manual_name
                category_name = item.category.name if item and item.category else None
                subcat = _resolve_expense_subcategory(category_name)
                title = _farm_expense_title(item_name)
                if subcat:
                    Expense.objects.create(
                        title=title,
                        amount=price,
                        subcategory=subcat,
                        additional_info=additional_info,
                        date=entry_date,
                        time=entry_time,
                        created_by=request.user,
                        content_object=product,
                    )
                else:
                    Expense.objects.create(
                        title=title,
                        amount=price,
                        manual_name=title,
                        additional_info=additional_info,
                        date=entry_date,
                        time=entry_time,
                        created_by=request.user,
                        content_object=product,
                    )
        except FarmProductItem.DoesNotExist:
            messages.error(request, _("Seçilmiş məhsul tapılmadı."))
        else:
            _bust_farm_list_cache(request.user.pk)
            add_crud_success_message(request, "FarmProduct", "create")

        return _redirect_with_refresh(redirect_to)

    return redirect(redirect_to)


@login_required
def farm_product_update(request, pk):
    product = get_object_or_404(FarmProduct, pk=pk, created_by=request.user)
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    redirect_to = next_url or f"{resolve_url('inventory:add_placeholder')}?type=farm"
    if request.method == "POST":
        item_id = request.POST.get("item")
        quantity = request.POST.get("quantity")
        unit = request.POST.get("unit")
        price = request.POST.get("price")
        zero_price_source = normalize_zero_price_source(request.POST.get("zero_price_source"))
        manual_name = normalize_manual_label(request.POST.get("manual_name"))
        additional_info = request.POST.get("additional_info")
        date_raw = request.POST.get("date")
        entry_date = _parse_date(date_raw)
        entry_time = _parse_time(request.POST.get("time"))

        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, _("Zəhmət olmasa, bütün məcburi xanaları (*) doldurun."))
            return render(
                request,
                "farm_products/farm_product_form.html",
                _farm_form_context(product),
            )

        price = price if price and price.strip() else 0
        try:
            quantity_val = Decimal(str(quantity))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, _("Miqdar düzgün deyil."))
            return render(
                request,
                "farm_products/farm_product_form.html",
                _farm_form_context(product),
            )
        if quantity_val > 0 and is_blank_or_zero_price(price) and not zero_price_source:
            messages.error(request, _("Məbləğ 0 olduqda bu stokun haradan gəldiyini seçin."))
            return render(
                request,
                "farm_products/farm_product_form.html",
                _farm_form_context(product),
            )

        def allowed_units_for_item(item_obj):
            forage_items = {"yonca", "koronilla", "seradella"}
            if not item_obj or not item_obj.unit:
                return {"kq", "ton", "qram", "litr", "ml", "ədəd", "dəstə", "bağlama"}
            if (item_obj.name or "").strip().lower() in forage_items:
                return {"kq", "bağlama"}
            if item_obj.unit == "kq":
                return {"kq", "ton", "qram"}
            if item_obj.unit == "litr":
                return {"litr", "ml"}
            return {item_obj.unit}

        prev_quantity = Decimal(str(product.quantity))
        prev_unit = product.unit
        prev_item = product.item
        prev_manual = product.manual_name

        product.quantity = quantity
        product.additional_info = additional_info
        product.price = price
        product.zero_price_source = zero_price_source if quantity_val > 0 and is_blank_or_zero_price(price) else None
        product.date = entry_date
        product.time = entry_time

        if item_id:
            item = FarmProductItem.objects.get(id=item_id)
            product.item = item
            if item.name == "Digər":
                if not manual_name:
                    messages.error(request, _("Zəhmət olmasa, Digər üçün ad daxil edin."))
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        _farm_form_context(product),
                    )
                product.manual_name = manual_name
                if unit not in allowed_units_for_item(item):
                    messages.error(request, _("Ölçü vahidi bu kateqoriya üçün uyğun deyil."))
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        _farm_form_context(product),
                    )
                product.unit = unit
            elif item.unit:
                if unit not in allowed_units_for_item(item):
                    messages.error(request, _("Ölçü vahidi bu kateqoriya üçün uyğun deyil."))
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        _farm_form_context(product),
                    )
                product.manual_name = None
                if item.unit in {"kq", "litr"} or (item.name or "").strip().lower() in {"yonca", "koronilla", "seradella"}:
                    product.unit = unit
                else:
                    product.unit = item.unit
            else:
                product.manual_name = None
                if unit not in allowed_units_for_item(item):
                    messages.error(request, _("Ölçü vahidi bu kateqoriya üçün uyğun deyil."))
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        _farm_form_context(product),
                    )
                product.unit = unit
        else:
            product.item = None
            product.manual_name = manual_name
            product.unit = unit

        if quantity_val < 0:
            new_item = product.item
            new_manual = product.manual_name
            new_unit = product.unit
            base_unit = "bağlama" if (new_item and _is_forage_item(new_item.name) and new_unit == "bağlama") else _farm_base_unit(new_unit)
            available_base = _farm_stock_base(
                request.user,
                new_item,
                new_manual if (not new_item or (new_item and new_item.name == "Digər")) else None,
                base_unit,
            )

            prev_add_back = Decimal("0")
            if prev_item == new_item and prev_manual == new_manual:
                if base_unit == "bağlama" and prev_unit == "bağlama":
                    prev_add_back = prev_quantity
                elif base_unit == "kq" and prev_unit in {"kq", "ton", "qram"}:
                    prev_add_back = _farm_to_base(prev_quantity, prev_unit, "kq")
                elif base_unit == "litr" and prev_unit in {"litr", "ml"}:
                    prev_add_back = _farm_to_base(prev_quantity, prev_unit, "litr")
                elif base_unit not in {"kq", "litr", "bağlama"} and prev_unit == base_unit:
                    prev_add_back = prev_quantity

            needed_base = _farm_to_base(abs(quantity_val), new_unit, base_unit)
            if available_base + prev_add_back < needed_base:
                messages.error(request, _("Stokda kifayət qədər məhsul yoxdur."))
                return render(
                    request,
                    "farm_products/farm_product_form.html",
                    _farm_form_context(product),
                )

        product.save()

        product_type = ContentType.objects.get_for_model(FarmProduct)
        linked_income = Income.objects.filter(content_type=product_type, object_id=product.id).first()

        if quantity_val < 0:
            try:
                amount_val = abs(float(product.price))
            except (TypeError, ValueError):
                amount_val = 0

            category_name = product.item.category.name if product.item and product.item.category else "Digər"
            if linked_income:
                if amount_val > 0:
                    linked_income.category = category_name
                    linked_income.item_name = product.item.name if product.item else product.manual_name
                    linked_income.quantity = abs(quantity_val)
                    linked_income.unit = product.unit
                    linked_income.amount = amount_val
                    linked_income.additional_info = product.additional_info
                    linked_income.date = product.date
                    linked_income.time = product.time
                    linked_income.save()
                else:
                    linked_income.delete()
            else:
                if amount_val > 0:
                    Income.objects.create(
                        category=category_name,
                        item_name=product.item.name if product.item else product.manual_name,
                        quantity=abs(quantity_val),
                        unit=product.unit,
                        amount=amount_val,
                        additional_info=product.additional_info,
                        date=product.date,
                        time=product.time,
                        created_by=request.user,
                        content_object=product,
                    )
        else:
            if linked_income:
                linked_income.delete()

        product_type = ContentType.objects.get_for_model(FarmProduct)
        linked_expense = Expense.objects.filter(content_type=product_type, object_id=product.id).first()

        if quantity_val > 0 and product.price and float(product.price) > 0:
            item_name = product.item.name if product.item else product.manual_name
            category_name = product.item.category.name if product.item and product.item.category else None
            subcat = _resolve_expense_subcategory(category_name)
            title = _farm_expense_title(item_name)

            if linked_expense:
                linked_expense.amount = product.price
                linked_expense.title = title
                linked_expense.additional_info = product.additional_info
                linked_expense.subcategory = subcat
                linked_expense.manual_name = None if subcat else title
                linked_expense.date = product.date
                linked_expense.time = product.time
                linked_expense.save()
            else:
                Expense.objects.create(
                    title=title,
                    amount=product.price,
                    subcategory=subcat,
                    manual_name=None if subcat else title,
                    additional_info=product.additional_info,
                    date=product.date,
                    time=product.time,
                    created_by=request.user,
                    content_object=product,
                )
        elif linked_expense:
            linked_expense.delete()

        _bust_farm_list_cache(request.user.pk)
        add_crud_success_message(request, "FarmProduct", "update")
        return _redirect_with_refresh(redirect_to)

    return render(
        request,
        "farm_products/farm_product_form.html",
        {**_farm_form_context(product), "next_url": next_url},
    )


@login_required
def farm_product_delete(request, pk):
    product = get_object_or_404(FarmProduct, pk=pk, created_by=request.user)
    redirect_to = request.POST.get("next") or f"{resolve_url('inventory:add_placeholder')}?type=farm"
    if request.method == "POST":
        product_type = ContentType.objects.get_for_model(FarmProduct)
        Expense.objects.filter(content_type=product_type, object_id=product.id).delete()
        Income.objects.filter(content_type=product_type, object_id=product.id).delete()
        product.delete()
        _bust_farm_list_cache(request.user.pk)
        add_crud_success_message(request, "FarmProduct", "delete")
        return _redirect_with_refresh(redirect_to)
    return render(request, "farm_products/farm_product_confirm_delete.html", {"product": product})


def _resolve_expense_subcategory(category_name: str | None):
    if not category_name:
        return None

    mapping = {
        "Süd və Süd Məhsulları": ("Heyvandarlıq", "Süd məhsulları"),
        "Yumurta": ("Heyvandarlıq", "Yumurta"),
        "Ət Məhsulları": ("Heyvandarlıq", "Ət"),
        "Bal və Arıçılıq": ("Heyvandarlıq", "Arıçılıq"),
        "Meyvə": ("Bitkiçilik", "Meyvə-Tərəvəz alışı"),
        "Tərəvəz": ("Bitkiçilik", "Meyvə-Tərəvəz alışı"),
        "Göyərti": ("Bitkiçilik", "Meyvə-Tərəvəz alışı"),
        "Bostan Məhsulları": ("Bitkiçilik", "Meyvə-Tərəvəz alışı"),
        "Taxıl Məhsulları": ("Bitkiçilik", "Taxıl alışı"),
        "Yem Bitkiləri": ("Bitkiçilik", "Yem bitkisi alışı"),
        "Gübrələr": ("Heyvandarlıq", "Gübrə"),
    }

    mapping_entry = mapping.get(category_name)
    if not mapping_entry:
        return None

    category_label, subcat_label = mapping_entry
    category = ExpenseCategory.objects.filter(name=category_label).first()
    if not category:
        return None

    return ExpenseSubCategory.objects.filter(category=category, name=subcat_label).first()

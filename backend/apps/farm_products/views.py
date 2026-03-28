from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.cache import cache
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from django.utils import timezone

from .models import FarmProduct, FarmProductCategory, FarmProductItem
from common.messages import add_crud_success_message
from common.category_order import (
    FARM_PRODUCT_CATEGORY_ORDER,
    FARM_PRODUCT_ITEM_ORDER,
    order_queryset_by_name_list,
)
from common.icons import get_farm_product_icon_for_product
from common.text import normalize_manual_label
from expenses.models import Expense, ExpenseCategory, ExpenseSubCategory
from incomes.models import Income

FARM_FORM_CATALOG_CACHE_KEY = "farm-products:form-catalog:v1"
FARM_FORM_CATALOG_TTL = 300


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
    }


def _farm_stock_base(user, item, manual_name: str | None, base_unit: str) -> Decimal:
    if item:
        qs = FarmProduct.objects.filter(created_by=user, item=item)
    else:
        qs = FarmProduct.objects.filter(created_by=user).filter(
            Q(item__isnull=True) | Q(item__name__iexact="Digər"),
            manual_name=manual_name,
        )
    total = Decimal("0")
    for product in qs:
        if base_unit == "bağlama":
            if product.unit != "bağlama":
                continue
            total += Decimal(product.quantity)
        elif base_unit == "kq":
            if product.unit not in {"kq", "ton", "qram"}:
                continue
            total += _farm_to_base(Decimal(product.quantity), product.unit, "kq")
        elif base_unit == "litr":
            if product.unit not in {"litr", "ml"}:
                continue
            total += _farm_to_base(Decimal(product.quantity), product.unit, "litr")
        else:
            if product.unit != base_unit:
                continue
            total += Decimal(product.quantity)
    return total


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
        title = f"{item_name} alışı"
        if linked_expense:
            linked_expense.amount = product.price
            linked_expense.title = title
            linked_expense.additional_info = product.additional_info
            linked_expense.subcategory = subcat
            linked_expense.manual_name = None if subcat else title
            linked_expense.save()
        else:
            Expense.objects.create(
                title=title,
                amount=product.price,
                subcategory=subcat,
                manual_name=None if subcat else title,
                additional_info=product.additional_info,
                created_by=user,
                content_object=product,
            )
    elif linked_expense:
        linked_expense.delete()


def _merge_manual_farm_product(user, manual_name, quantity_val, unit, price, additional_info, entry_date):
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
    existing.additional_info = additional_info
    existing.date = entry_date
    existing.save()
    _sync_farm_product_related_records(user, existing)
    return existing


@login_required
def farm_product_list(request):
    query = (request.GET.get("q") or "").strip()
    category_id = (request.GET.get("category") or "").strip()
    item_id = (request.GET.get("item") or "").strip()
    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()
    movement = (request.GET.get("movement") or "").strip()
    products_qs = FarmProduct.objects.filter(created_by=request.user).select_related(
        "item", "item__category"
    ).only(
        "id",
        "quantity",
        "unit",
        "price",
        "date",
        "manual_name",
        "additional_info",
        "updated_at",
        "item__id",
        "item__name",
        "item__unit",
        "item__category__id",
        "item__category__name",
    )

    if query:
        products_qs = products_qs.filter(
            Q(item__name__icontains=query)
            | Q(item__category__name__icontains=query)
            | Q(additional_info__icontains=query)
            | Q(manual_name__icontains=query)
        )

    selected_category = FarmProductCategory.objects.filter(pk=category_id).first() if category_id else None
    if selected_category:
        if (selected_category.name or "").strip().lower().startswith("digər"):
            products_qs = products_qs.filter(Q(item__category=selected_category) | Q(item__isnull=True))
        else:
            products_qs = products_qs.filter(item__category=selected_category)

    filtered_items = []
    if selected_category and not (selected_category.name or "").strip().lower().startswith("digər"):
        filtered_items = list(
            order_queryset_by_name_list(
                FarmProductItem.objects.filter(category=selected_category),
                FARM_PRODUCT_ITEM_ORDER.get(selected_category.name, []),
            )
        )

    if item_id:
        products_qs = products_qs.filter(item_id=item_id)

    date_from = _parse_filter_date(date_from_raw)
    if date_from:
        products_qs = products_qs.filter(date__gte=date_from)

    date_to = _parse_filter_date(date_to_raw)
    if date_to:
        products_qs = products_qs.filter(date__lte=date_to)

    if movement == "increase":
        products_qs = products_qs.filter(quantity__gt=0)
    elif movement == "decrease":
        products_qs = products_qs.filter(quantity__lt=0)

    products = list(products_qs)
    for product in products:
        product.icon_class = get_farm_product_icon_for_product(product)
        try:
            product.price_display = abs(Decimal(product.price))
        except Exception:
            product.price_display = product.price

    form_catalog = _farm_form_catalog()

    today = timezone.now().date()
    context = {
        "products": products,
        "categories": form_catalog["categories"],
        "category_item_map": form_catalog["item_map"],
        "filter_items": filtered_items,
        "selected_category": category_id,
        "selected_item": item_id,
        "selected_date_from": date_from_raw,
        "selected_date_to": date_to_raw,
        "selected_movement": movement,
        "today": today,
        "yesterday": today - timedelta(days=1),
    }
    return render(request, "farm_products/farm_product_list.html", context)


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
    redirect_to = request.POST.get("next") or "farm_products:product_list"
    if request.method == "POST":
        item_id = request.POST.get("item")
        quantity = request.POST.get("quantity")
        unit = request.POST.get("unit")
        price = request.POST.get("price")
        manual_name = normalize_manual_label(request.POST.get("manual_name"))
        additional_info = request.POST.get("additional_info")
        date_raw = request.POST.get("date")
        entry_date = _parse_date(date_raw)

        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, "Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")
            return redirect(redirect_to)

        price = price if price and price.strip() else 0
        try:
            quantity_val = Decimal(str(quantity))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Miqdar düzgün deyil.")
            return redirect(redirect_to)

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
                    messages.error(request, "Zəhmət olmasa, Digər üçün ad daxil edin.")
                    return redirect(redirect_to)
                effective_manual = manual_name
            if item:
                allowed_units = allowed_units_for_item(item)
                if unit not in allowed_units:
                    messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
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
                    messages.error(request, "Stokda kifayət qədər məhsul yoxdur.")
                    return redirect(redirect_to)

            merged = _merge_manual_farm_product(
                request.user,
                effective_manual,
                quantity_val,
                effective_unit,
                price,
                additional_info,
                entry_date,
            ) if effective_manual else None
            if merged == "deleted":
                add_crud_success_message(request, "FarmProduct", "delete")
                return redirect(redirect_to)
            if merged:
                add_crud_success_message(request, "FarmProduct", "update")
                return redirect(redirect_to)

            product = FarmProduct.objects.create(
                item=item,
                manual_name=effective_manual,
                quantity=quantity,
                unit=effective_unit,
                price=price,
                additional_info=additional_info,
                date=entry_date,
                created_by=request.user,
            )

            if quantity_val < 0:
                try:
                    amount_val = abs(float(price))
                except (TypeError, ValueError):
                    amount_val = 0
                if amount_val <= 0:
                    messages.error(request, "Gəlir üçün məbləğ daxil edin.")
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
                    created_by=request.user,
                    content_object=product,
                )

            if quantity_val > 0 and price and float(price) > 0:
                item_name = item.name if item else manual_name
                category_name = item.category.name if item and item.category else None
                subcat = _resolve_expense_subcategory(category_name)
                title = f"{item_name} alışı"
                if subcat:
                    Expense.objects.create(
                        title=title,
                        amount=price,
                        subcategory=subcat,
                        additional_info=additional_info,
                        created_by=request.user,
                        content_object=product,
                    )
                else:
                    Expense.objects.create(
                        title=title,
                        amount=price,
                        manual_name=title,
                        additional_info=additional_info,
                        created_by=request.user,
                        content_object=product,
                    )
        except FarmProductItem.DoesNotExist:
            messages.error(request, "Seçilmiş məhsul tapılmadı.")
        else:
            add_crud_success_message(request, "FarmProduct", "create")

        return redirect(redirect_to)

    return redirect(redirect_to)


@login_required
def farm_product_update(request, pk):
    product = get_object_or_404(FarmProduct, pk=pk, created_by=request.user)
    if request.method == "POST":
        item_id = request.POST.get("item")
        quantity = request.POST.get("quantity")
        unit = request.POST.get("unit")
        price = request.POST.get("price")
        manual_name = normalize_manual_label(request.POST.get("manual_name"))
        additional_info = request.POST.get("additional_info")
        date_raw = request.POST.get("date")
        entry_date = _parse_date(date_raw)

        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, "Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")
            return render(
                request,
                "farm_products/farm_product_form.html",
                _farm_form_context(product),
            )

        price = price if price and price.strip() else 0
        try:
            quantity_val = Decimal(str(quantity))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Miqdar düzgün deyil.")
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
        product.date = entry_date

        if item_id:
            item = FarmProductItem.objects.get(id=item_id)
            product.item = item
            if item.name == "Digər":
                if not manual_name:
                    messages.error(request, "Zəhmət olmasa, Digər üçün ad daxil edin.")
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        _farm_form_context(product),
                    )
                product.manual_name = manual_name
                if unit not in allowed_units_for_item(item):
                    messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        _farm_form_context(product),
                    )
                product.unit = unit
            elif item.unit:
                if unit not in allowed_units_for_item(item):
                    messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
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
                    messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
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
                messages.error(request, "Stokda kifayət qədər məhsul yoxdur.")
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
            title = f"{item_name} alışı"

            if linked_expense:
                linked_expense.amount = product.price
                linked_expense.title = title
                linked_expense.additional_info = product.additional_info
                linked_expense.subcategory = subcat
                linked_expense.manual_name = None if subcat else title
                linked_expense.save()
            else:
                Expense.objects.create(
                    title=title,
                    amount=product.price,
                    subcategory=subcat,
                    manual_name=None if subcat else title,
                    additional_info=product.additional_info,
                    created_by=request.user,
                    content_object=product,
                )
        elif linked_expense:
            linked_expense.delete()

        add_crud_success_message(request, "FarmProduct", "update")
        return redirect("farm_products:product_list")

    return render(
        request,
        "farm_products/farm_product_form.html",
        _farm_form_context(product),
    )


@login_required
def farm_product_delete(request, pk):
    product = get_object_or_404(FarmProduct, pk=pk, created_by=request.user)
    if request.method == "POST":
        product_type = ContentType.objects.get_for_model(FarmProduct)
        Expense.objects.filter(content_type=product_type, object_id=product.id).delete()
        Income.objects.filter(content_type=product_type, object_id=product.id).delete()
        product.delete()
        add_crud_success_message(request, "FarmProduct", "delete")
        return redirect("farm_products:product_list")
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

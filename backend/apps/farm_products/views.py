from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Case, IntegerField, When
from django.contrib.contenttypes.models import ContentType

from .models import FarmProduct, FarmProductCategory, FarmProductItem
from common.messages import add_crud_success_message
from common.icons import get_farm_product_icon_for_product
from expenses.models import Expense, ExpenseCategory, ExpenseSubCategory


@login_required
def farm_product_list(request):
    query = request.GET.get("q")
    products_qs = FarmProduct.objects.filter(created_by=request.user).select_related(
        "item", "item__category"
    )

    if query:
        products_qs = products_qs.filter(item__name__icontains=query) | \
            products_qs.filter(item__category__name__icontains=query) | \
            products_qs.filter(additional_info__icontains=query) | \
            products_qs.filter(manual_name__icontains=query)

    products = list(products_qs)
    for product in products:
        product.icon_class = get_farm_product_icon_for_product(product)

    category_order = Case(
        When(name__startswith="Digər", then=1),
        default=0,
        output_field=IntegerField(),
    )
    categories = FarmProductCategory.objects.all().order_by(category_order, "name")

    context = {
        "products": products,
        "categories": categories,
    }
    return render(request, "farm_products/farm_product_list.html", context)


@login_required
def get_farm_product_items(request):
    category_id = request.GET.get("category_id")
    if category_id:
        category = FarmProductCategory.objects.filter(id=category_id).first()
        if category and category.name.startswith("Digər"):
            return JsonResponse([], safe=False)
    items = FarmProductItem.objects.filter(category_id=category_id).values("id", "name", "unit")
    return JsonResponse(list(items), safe=False)


@login_required
def farm_product_create(request):
    if request.method == "POST":
        item_id = request.POST.get("item")
        quantity = request.POST.get("quantity")
        unit = request.POST.get("unit")
        price = request.POST.get("price")
        manual_name = request.POST.get("manual_name")
        additional_info = request.POST.get("additional_info")

        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, "Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")
            return redirect("farm_products:product_list")

        price = price if price and price.strip() else 0

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
                    return redirect("farm_products:product_list")
                effective_manual = manual_name
            if item:
                allowed_units = allowed_units_for_item(item)
                if unit not in allowed_units:
                    messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
                    return redirect("farm_products:product_list")
                if item.unit and item.unit not in {"kq", "litr"}:
                    effective_unit = item.unit
                if item.unit and item.unit in {"kq", "litr"}:
                    effective_unit = unit
                if (item.name or "").strip().lower() in {"yonca", "koronilla", "seradella"}:
                    effective_unit = unit
                effective_manual = None if item.name != "Digər" else effective_manual

            product = FarmProduct.objects.create(
                item=item,
                manual_name=effective_manual,
                quantity=quantity,
                unit=effective_unit,
                price=price,
                additional_info=additional_info,
                created_by=request.user,
            )

            if price and float(price) > 0:
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

        return redirect("farm_products:product_list")

    return redirect("farm_products:product_list")


@login_required
def farm_product_update(request, pk):
    product = get_object_or_404(FarmProduct, pk=pk, created_by=request.user)
    if request.method == "POST":
        item_id = request.POST.get("item")
        quantity = request.POST.get("quantity")
        unit = request.POST.get("unit")
        price = request.POST.get("price")
        manual_name = request.POST.get("manual_name")
        additional_info = request.POST.get("additional_info")

        if not (item_id or manual_name) or not quantity or not unit:
            messages.error(request, "Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.")
            return render(
                request,
                "farm_products/farm_product_form.html",
                {"product": product, "categories": FarmProductCategory.objects.all()},
            )

        price = price if price and price.strip() else 0

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

        product.quantity = quantity
        product.additional_info = additional_info
        product.price = price

        if item_id:
            item = FarmProductItem.objects.get(id=item_id)
            product.item = item
            if item.name == "Digər":
                if not manual_name:
                    messages.error(request, "Zəhmət olmasa, Digər üçün ad daxil edin.")
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        {"product": product, "categories": FarmProductCategory.objects.all()},
                    )
                product.manual_name = manual_name
                if unit not in allowed_units_for_item(item):
                    messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        {"product": product, "categories": FarmProductCategory.objects.all()},
                    )
                product.unit = unit
            elif item.unit:
                if unit not in allowed_units_for_item(item):
                    messages.error(request, "Ölçü vahidi bu kateqoriya üçün uyğun deyil.")
                    return render(
                        request,
                        "farm_products/farm_product_form.html",
                        {"product": product, "categories": FarmProductCategory.objects.all()},
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
                        {"product": product, "categories": FarmProductCategory.objects.all()},
                    )
                product.unit = unit
        else:
            product.item = None
            product.manual_name = manual_name
            product.unit = unit

        product.save()

        product_type = ContentType.objects.get_for_model(FarmProduct)
        linked_expense = Expense.objects.filter(content_type=product_type, object_id=product.id).first()

        if product.price and float(product.price) > 0:
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

    category_order = Case(
        When(name__startswith="Digər", then=1),
        default=0,
        output_field=IntegerField(),
    )
    categories = FarmProductCategory.objects.all().order_by(category_order, "name")
    return render(
        request,
        "farm_products/farm_product_form.html",
        {"product": product, "categories": categories},
    )


@login_required
def farm_product_delete(request, pk):
    product = get_object_or_404(FarmProduct, pk=pk, created_by=request.user)
    if request.method == "POST":
        product_type = ContentType.objects.get_for_model(FarmProduct)
        Expense.objects.filter(content_type=product_type, object_id=product.id).delete()
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

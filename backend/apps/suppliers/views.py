from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Supplier


def _normalize_phone(phone):
    return Supplier.normalize_phone(phone)


def _supplier_categories():
    return [choice[0] for choice in Supplier.CATEGORY_CHOICES]


def _form_supplier(form_data):
    return type("SupplierFormState", (), form_data)()


@login_required
def suppliers_list(request):
    suppliers = Supplier.objects.filter(created_by=request.user)

    search_query = (request.GET.get('q') or '').strip()
    selected_category = (request.GET.get('category') or '').strip()
    if search_query:
        normalized_search_query = _normalize_phone(search_query)
        suppliers = suppliers.filter(
            Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(phone__icontains=normalized_search_query)
        )
    if selected_category:
        suppliers = suppliers.filter(category=selected_category)
        
    context = {
        'suppliers': suppliers,
        'search_query': search_query,
        'selected_category': selected_category,
        'supplier_categories': _supplier_categories(),
    }
    return render(request, 'suppliers/suppliers.html', context)

@login_required
def supplier_add(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        category = (request.POST.get('category') or '').strip()
        manual_category = (request.POST.get('manual_category') or '').strip()
        location = (request.POST.get('location') or '').strip()
        rating = request.POST.get('rating', 5)
        phone = _normalize_phone(request.POST.get('phone'))
        additional_info = (request.POST.get('additional_info') or '').strip()
        last_order_date = (request.POST.get('last_order_date') or '').strip()

        if not category:
            messages.error(request, "Kateqoriya seçin.")
            return render(request, 'suppliers/suppliers_add.html', {
                'supplier': _form_supplier(request.POST),
                'supplier_categories': _supplier_categories(),
            })

        if category == "Digər" and not manual_category:
            messages.error(request, "Zəhmət olmasa, Digər üçün kateqoriya adı daxil edin.")
            return render(request, 'suppliers/suppliers_add.html', {
                'supplier': _form_supplier(request.POST),
                'supplier_categories': _supplier_categories(),
            })

        supplier = Supplier(
            name=name,
            category=category,
            manual_category=manual_category,
            location=location,
            rating=rating,
            phone=phone,
            additional_info=additional_info,
            created_by=request.user
        )
        if last_order_date:
            supplier.last_order_date = last_order_date
        
        supplier.save()
        messages.success(request, f"{name} sistemə əlavə edildi.")
        return redirect('suppliers_list')

    return render(request, 'suppliers/suppliers_add.html', {
        'supplier_categories': _supplier_categories(),
    })


@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk, created_by=request.user)
    if request.method == 'POST':
        supplier.name = (request.POST.get('name') or '').strip()
        supplier.category = (request.POST.get('category') or '').strip()
        supplier.manual_category = (request.POST.get('manual_category') or '').strip()
        supplier.location = (request.POST.get('location') or '').strip()
        supplier.rating = request.POST.get('rating', 5)
        supplier.phone = _normalize_phone(request.POST.get('phone'))
        supplier.additional_info = (request.POST.get('additional_info') or '').strip()
        last_order_date = (request.POST.get('last_order_date') or '').strip()
        if not supplier.category:
            messages.error(request, "Kateqoriya seçin.")
            return render(request, 'suppliers/suppliers_add.html', {
                'supplier': supplier,
                'is_edit': True,
                'supplier_categories': _supplier_categories(),
            })
        if supplier.category == "Digər" and not supplier.manual_category:
            messages.error(request, "Zəhmət olmasa, Digər üçün kateqoriya adı daxil edin.")
            return render(request, 'suppliers/suppliers_add.html', {
                'supplier': supplier,
                'is_edit': True,
                'supplier_categories': _supplier_categories(),
            })
        if last_order_date:
            supplier.last_order_date = last_order_date
        else:
            supplier.last_order_date = None
        supplier.save()
        messages.success(request, f"{supplier.name} yeniləndi.")
        return redirect('suppliers_list')

    return render(request, 'suppliers/suppliers_add.html', {
        'supplier': supplier,
        'is_edit': True,
        'supplier_categories': _supplier_categories(),
    })


@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk, created_by=request.user)
    supplier_name = supplier.name
    supplier.delete()
    messages.success(request, f"{supplier_name} silindi.")
    return redirect('suppliers_list')

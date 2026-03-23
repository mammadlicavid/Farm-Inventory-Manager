from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Supplier

@login_required
def suppliers_list(request):
    suppliers = Supplier.objects.filter(created_by=request.user)

    # Convert query parameters to handle potential search feature
    search_query = request.GET.get('q', '')
    if search_query:
        suppliers = suppliers.filter(name__icontains=search_query)
        
    context = {
        'suppliers': suppliers,
        'search_query': search_query,
    }
    return render(request, 'suppliers/suppliers.html', context)

@login_required
def supplier_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        location = request.POST.get('location')
        rating = request.POST.get('rating', 5)
        phone = request.POST.get('phone')
        is_favorite = request.POST.get('is_favorite') == 'on'
        last_order_date = request.POST.get('last_order_date')

        supplier = Supplier(
            name=name,
            category=category,
            location=location,
            rating=rating,
            phone=phone,
            is_favorite=is_favorite,
            created_by=request.user
        )
        if last_order_date:
            supplier.last_order_date = last_order_date
        
        supplier.save()
        messages.success(request, f"{name} sistemə əlavə edildi.")
        return redirect('suppliers_list')

    return render(request, 'suppliers/suppliers_add.html', {})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType

from .models import Animal, AnimalCategory, AnimalSubCategory
from .forms import AnimalForm
from common.messages import add_crud_success_message
from common.icons import get_animal_icon_for_animal
from expenses.models import Expense, ExpenseSubCategory

@login_required
def animal_list(request):
    query = request.GET.get('q')
    animals_qs = Animal.objects.filter(created_by=request.user).select_related('subcategory', 'subcategory__category')

    if query:
        animals_qs = animals_qs.filter(identification_no__icontains=query) | \
                     animals_qs.filter(additional_info__icontains=query) | \
                     animals_qs.filter(subcategory__name__icontains=query) | \
                     animals_qs.filter(manual_name__icontains=query)

    animals = list(animals_qs)
    for animal in animals:
        animal.icon_class = get_animal_icon_for_animal(animal)
        if hasattr(animal, 'subcategory') and animal.subcategory:
            animal.display_name = animal.subcategory.name
        else:
            animal.display_name = animal.manual_name
        
        animal.display_subtitle = f"({animal.identification_no})" if getattr(animal, 'identification_no', None) else ""

    categories = AnimalCategory.objects.all().prefetch_related('subcategories')
    
    context = {
        'animals': animals,
        'categories': categories,
    }
    return render(request, 'animals/animal_list.html', context)

@login_required
def animal_create(request):
    if request.method == 'POST':
        subcategory_id = request.POST.get('subcategory')
        identification_no = request.POST.get('identification_no')
        additional_info = request.POST.get('additional_info')
        gender = request.POST.get('gender')
        weight = request.POST.get('weight')
        price = request.POST.get('price')
        status = request.POST.get('status')
        manual_name = request.POST.get('manual_name')
        
        # Backend Validation
        if not (subcategory_id or manual_name) or not identification_no or not gender or not weight:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return redirect('animals:animal_list')

        # Handle empty numeric fields
        weight = weight if weight and weight.strip() else None
        price = price if price and price.strip() else 0
        
        # Ensure non-nullable fields have defaults if missing from form
        if not status:
            status = 'aktiv'
        if not gender:
            gender = 'erkek'
            
        try:
            subcategory = None
            if subcategory_id:
                subcategory = AnimalSubCategory.objects.get(id=subcategory_id)
            
            animal = Animal.objects.create(
                subcategory=subcategory,
                manual_name=manual_name if not subcategory else None,
                identification_no=identification_no,
                additional_info=additional_info,
                gender=gender,
                weight=weight,
                price=price,
                status=status,
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
        return redirect('animals:animal_list')
    
    return redirect('animals:animal_list')

@login_required
def animal_update(request, pk):
    animal = get_object_or_404(Animal, pk=pk, created_by=request.user)
    if request.method == 'POST':
        subcategory_id = request.POST.get('subcategory')
        identification_no = request.POST.get('identification_no')
        additional_info = request.POST.get('additional_info')
        gender = request.POST.get('gender')
        weight = request.POST.get('weight')
        price = request.POST.get('price')
        status = request.POST.get('status')
        manual_name = request.POST.get('manual_name')
        
        # Backend Validation
        if not (subcategory_id or manual_name) or not identification_no or not gender or not weight:
            messages.error(request, 'Zəhmət olmasa, bütün məcburi xanaları (*) doldurun.')
            return render(request, 'animals/animal_form.html', {
                'form': AnimalForm(instance=animal),
                'animal': animal,
                'categories': AnimalCategory.objects.all().prefetch_related('subcategories')
            })

        # Update animal object
        animal.identification_no = identification_no
        animal.additional_info = additional_info
        animal.gender = gender
        animal.manual_name = manual_name if not subcategory_id else None
        
        # Handle empty numeric fields
        animal.weight = weight if weight and weight.strip() else None
        animal.price = price if price and price.strip() else 0
        
        if status:
            animal.status = status
            
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
    
    categories = AnimalCategory.objects.all().prefetch_related('subcategories')
    return render(request, 'animals/animal_form.html', {
        'animal': animal,
        'categories': categories,
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

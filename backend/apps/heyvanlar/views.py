from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Animal
from .forms import AnimalForm

@login_required
def animal_list(request):
    query = request.GET.get('q')
    if query:
        animals = Animal.objects.filter(name__icontains=query)
    else:
        animals = Animal.objects.all()
    return render(request, 'heyvanlar/animal_list.html', {'animals': animals})

@login_required
def animal_create(request):
    if request.method == 'POST':
        form = AnimalForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('heyvanlar:animal_list')
    else:
        form = AnimalForm()
    return render(request, 'heyvanlar/animal_form.html', {'form': form})

@login_required
def animal_update(request, pk):
    animal = get_object_or_404(Animal, pk=pk)
    if request.method == 'POST':
        form = AnimalForm(request.POST, instance=animal)
        if form.is_valid():
            form.save()
            return redirect('heyvanlar:animal_list')
    else:
        form = AnimalForm(instance=animal)
    return render(request, 'heyvanlar/animal_form.html', {'form': form, 'animal': animal})

@login_required
def animal_delete(request, pk):
    animal = get_object_or_404(Animal, pk=pk)
    if request.method == 'POST':
        animal.delete()
        return redirect('heyvanlar:animal_list')
    return render(request, 'heyvanlar/animal_confirm_delete.html', {'animal': animal})

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Seed
from django.contrib.auth.decorators import login_required

from .forms import SeedForm

@login_required
def seed_list(request):
    query = request.GET.get('q')
    if query:
        seeds = Seed.objects.filter(name__icontains=query)
    else:
        seeds = Seed.objects.all()
    
    return render(request, 'toxum/seed_list.html', {'seeds': seeds})

@login_required
def seed_create(request):
    if request.method == 'POST':
        form = SeedForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('toxum:seed_list')
    else:
        form = SeedForm()
    return render(request, 'toxum/seed_form.html', {'form': form})

@login_required
def seed_update(request, pk):
    seed = get_object_or_404(Seed, pk=pk)
    if request.method == 'POST':
        form = SeedForm(request.POST, instance=seed)
        if form.is_valid():
            form.save()
            return redirect('toxum:seed_list')
    else:
        form = SeedForm(instance=seed)
    return render(request, 'toxum/seed_form.html', {'form': form, 'seed': seed})

@login_required
def seed_delete(request, pk):
    seed = get_object_or_404(Seed, pk=pk)
    if request.method == 'POST':
        seed.delete()
        return redirect('toxum:seed_list')
    return render(request, 'toxum/seed_confirm_delete.html', {'seed': seed})

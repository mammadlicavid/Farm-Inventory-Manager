from django.shortcuts import render, redirect, get_object_or_404
from .models import Alet
from .forms import AletForm
from django.contrib.auth.decorators import login_required

@login_required
def alet_list(request):
    query = request.GET.get('q')
    if query:
        alets = Alet.objects.filter(name__icontains=query)
    else:
        alets = Alet.objects.all()
    return render(request, 'alet/alet_list.html', {'alets': alets})

@login_required
def alet_create(request):
    if request.method == 'POST':
        form = AletForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            return redirect('alet:alet_list')
    else:
        form = AletForm()
    return render(request, 'alet/alet_form.html', {'form': form})

@login_required
def alet_update(request, pk):
    alet = get_object_or_404(Alet, pk=pk)
    if request.method == 'POST':
        form = AletForm(request.POST, instance=alet)
        if form.is_valid():
            form.save()
            return redirect('alet:alet_list')
    else:
        form = AletForm(instance=alet)
    return render(request, 'alet/alet_form.html', {'form': form, 'alet': alet})

@login_required
def alet_delete(request, pk):
    alet = get_object_or_404(Alet, pk=pk)
    if request.method == 'POST':
        alet.delete()
        return redirect('alet:alet_list')
    return render(request, 'alet/alet_confirm_delete.html', {'alet': alet})

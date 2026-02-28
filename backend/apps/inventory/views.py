from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

def home(request):
    return HttpResponse("Home page")

@login_required
def dashboard(request):
    return HttpResponse("Dashboard ✅ You are logged in.")

@login_required
def products_placeholder(request):
    return render(request, "common/placeholder.html")

@login_required
def add_product(request):
    return render(request, "inventory/add_product.html")

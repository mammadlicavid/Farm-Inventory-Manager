from django.urls import path
from . import views

urlpatterns = [
    path('', views.suppliers_list, name='suppliers_list'),
    path('add/', views.supplier_add, name='supplier_add'),
]

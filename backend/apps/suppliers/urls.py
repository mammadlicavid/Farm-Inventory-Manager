from django.urls import path
from . import views

urlpatterns = [
    path('', views.suppliers_list, name='suppliers_list'),
    path('add/', views.supplier_add, name='supplier_add'),
    path('edit/<int:pk>/', views.supplier_edit, name='supplier_edit'),
    path('delete/<int:pk>/', views.supplier_delete, name='supplier_delete'),
]

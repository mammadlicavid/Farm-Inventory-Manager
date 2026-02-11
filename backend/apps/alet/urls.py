from django.urls import path
from . import views

app_name = 'alet'

urlpatterns = [
    path('', views.alet_list, name='alet_list'),
    path('create/', views.alet_create, name='alet_create'),
    path('update/<int:pk>/', views.alet_update, name='alet_update'),
    path('delete/<int:pk>/', views.alet_delete, name='alet_delete'),
]

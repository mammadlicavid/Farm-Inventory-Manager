from django.urls import path
from . import views

app_name = 'animals'

urlpatterns = [
    path('', views.animal_list, name='animal_list'),
    path('create/', views.animal_create, name='animal_create'),
    path('update/<int:pk>/', views.animal_update, name='animal_update'),
    path('delete/<int:pk>/', views.animal_delete, name='animal_delete'),
]

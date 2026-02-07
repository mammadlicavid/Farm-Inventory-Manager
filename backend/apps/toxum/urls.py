from django.urls import path
from . import views

app_name = 'toxum'

urlpatterns = [
    path('', views.seed_list, name='seed_list'),
    path('create/', views.seed_create, name='seed_create'),
    path('update/<int:pk>/', views.seed_update, name='seed_update'),
    path('delete/<int:pk>/', views.seed_delete, name='seed_delete'),
]

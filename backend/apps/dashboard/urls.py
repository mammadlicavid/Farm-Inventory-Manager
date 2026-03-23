from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('quick-expense/', views.quick_expense, name='quick_expense'),
    path('quick-income/', views.quick_income, name='quick_income'),
]

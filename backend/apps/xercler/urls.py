from django.urls import path
from . import views

app_name = 'xercler'

urlpatterns = [
    path('', views.expense_list, name='expense_list'),
]

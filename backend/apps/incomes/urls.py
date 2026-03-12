from django.urls import path
from . import views

app_name = "incomes"

urlpatterns = [
    path("", views.income_list, name="income_list"),
    path("add/", views.add_income, name="add_income"),
    path("edit/<int:pk>/", views.edit_income, name="edit_income"),
    path("delete/<int:pk>/", views.delete_income, name="delete_income"),
]

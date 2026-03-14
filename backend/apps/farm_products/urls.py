from django.urls import path
from . import views

app_name = "farm_products"

urlpatterns = [
    path("", views.farm_product_list, name="product_list"),
    path("create/", views.farm_product_create, name="product_create"),
    path("items/", views.get_farm_product_items, name="get_items"),
    path("<int:pk>/update/", views.farm_product_update, name="product_update"),
    path("<int:pk>/delete/", views.farm_product_delete, name="product_delete"),
]

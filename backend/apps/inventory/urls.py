from django.urls import path
from .views import home, dashboard, products_placeholder, add_product

app_name = 'inventory'

urlpatterns = [
    path('products/', products_placeholder, name='products'),
    path('add/', add_product, name='add_placeholder'), # Keeping name for reverse resolution
]

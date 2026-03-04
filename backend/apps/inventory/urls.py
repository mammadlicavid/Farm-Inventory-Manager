from django.urls import path
from .views import home, dashboard, products_placeholder, add_product, update_product_quantity

app_name = 'inventory'

urlpatterns = [
    path('products/', products_placeholder, name='products'),
    path('products/update-quantity/', update_product_quantity, name='products_update_quantity'),
    path('add/', add_product, name='add_placeholder'), # Keeping name for reverse resolution
]

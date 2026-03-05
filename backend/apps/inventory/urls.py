from django.urls import path
from .views import home, dashboard, stocks_placeholder, add_product, update_stock_quantity

app_name = 'inventory'

urlpatterns = [
    path('stocks/', stocks_placeholder, name='stocks'),
    path('stocks/update-quantity/', update_stock_quantity, name='stocks_update_quantity'),
    path('add/', add_product, name='add_placeholder'), # Keeping name for reverse resolution
]

from django.urls import path

from .views import (
    add_product,
    barcode_builder,
    dashboard,
    get_or_create_barcode,
    home,
    lookup_scan_code,
    stocks_placeholder,
    update_stock_quantity,
)

app_name = 'inventory'

urlpatterns = [
    path('stocks/', stocks_placeholder, name='stocks'),
    path('stocks/update-quantity/', update_stock_quantity, name='stocks_update_quantity'),
    path('add-product/', add_product, name='add_placeholder'),
    path('add-product/barcode-builder/', barcode_builder, name='barcode_builder'),
    path('scan-lookup/', lookup_scan_code, name='scan_lookup'),
    path('barcode/', get_or_create_barcode, name='barcode'),
]

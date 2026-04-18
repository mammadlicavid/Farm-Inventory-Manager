from django.urls import path

from .views import (
    add_product,
    add_product_list_panel,
    barcode_builder,
    dashboard,
    get_or_create_barcode,
    home,
    lookup_scan_code,
    stocks_placeholder,
    transcribe_voice_input,
    update_stock_quantity,
)

app_name = 'inventory'

urlpatterns = [
    path('stocks/', stocks_placeholder, name='stocks'),
    path('stocks/update-quantity/', update_stock_quantity, name='stocks_update_quantity'),
    path('add-product/', add_product, name='add_placeholder'),
    path('add-product/list-panel/', add_product_list_panel, name='add_product_list_panel'),
    path('add-product/barcode-builder/', barcode_builder, name='barcode_builder'),
    path('add-product/voice-transcribe/', transcribe_voice_input, name='voice_transcribe'),
    path('scan-lookup/', lookup_scan_code, name='scan_lookup'),
    path('barcode/', get_or_create_barcode, name='barcode'),
]

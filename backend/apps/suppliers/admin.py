from django.contrib import admin
from .models import Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'location', 'rating', 'is_favorite', 'last_order_date')
    list_filter = ('category', 'is_favorite')
    search_fields = ('name', 'location', 'phone')

from django.contrib import admin
from .models import Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'location', 'rating', 'last_order_date')
    list_filter = ('category',)
    search_fields = ('name', 'location', 'phone')

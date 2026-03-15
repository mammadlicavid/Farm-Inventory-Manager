from django.contrib import admin
from .models import ScanItem

# Register your models here.

@admin.register(ScanItem)
class ScanItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "unit", "default_price", "is_active")
    search_fields = ("code", "name")
    list_filter = ("category", "is_active")
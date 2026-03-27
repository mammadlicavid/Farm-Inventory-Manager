from django.contrib import admin

from .models import ScanItem, UserBarcode

# Register your models here.

@admin.register(ScanItem)
class ScanItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "unit", "default_price", "is_active")
    search_fields = ("code", "name")
    list_filter = ("category", "is_active")


@admin.register(UserBarcode)
class UserBarcodeAdmin(admin.ModelAdmin):
    list_display = ("code", "form_type", "target_type", "label", "updated_at")
    search_fields = ("code", "label")
    list_filter = ("form_type", "target_type")

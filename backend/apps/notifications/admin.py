from django.contrib import admin
from .models import Notification, StockAlertRule


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'due_date', 'is_completed', 'created_by')
    list_filter = ('category', 'is_completed')
    search_fields = ('title',)


@admin.register(StockAlertRule)
class StockAlertRuleAdmin(admin.ModelAdmin):
    list_display = ("item_name", "source_type", "threshold", "unit", "is_active", "created_by")
    list_filter = ("source_type", "is_active")
    search_fields = ("item_name", "item_key")

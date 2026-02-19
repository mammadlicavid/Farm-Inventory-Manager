from django.contrib import admin
from .models import Tool, ToolCategory, ToolItem

@admin.register(ToolCategory)
class ToolCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(ToolItem)
class ToolItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)

@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity', 'price', 'get_category', 'created_at')
    search_fields = ('item__name',)
    list_filter = ('item__category', 'created_at')

    def get_category(self, obj):
        return obj.item.category
    get_category.short_description = 'Kateqoriya'

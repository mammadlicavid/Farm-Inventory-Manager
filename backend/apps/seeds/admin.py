from django.contrib import admin
from .models import Seed, SeedCategory, SeedItem

@admin.register(SeedCategory)
class SeedCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(SeedItem)
class SeedItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)

@admin.register(Seed)
class SeedAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity', 'price', 'unit', 'created_at')
    list_filter = ('item__category', 'unit')

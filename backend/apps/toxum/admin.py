from django.contrib import admin
from .models import Seed

@admin.register(Seed)
class SeedAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'price', 'unit', 'created_at')
    search_fields = ('name',)

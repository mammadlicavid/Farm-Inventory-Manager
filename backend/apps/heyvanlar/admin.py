from django.contrib import admin
from .models import Animal

@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'price', 'created_at')
    search_fields = ('name',)

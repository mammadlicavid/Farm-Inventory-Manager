from django.contrib import admin
from .models import Alet

@admin.register(Alet)
class AletAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'price', 'type', 'created_at')
    search_fields = ('name', 'type')
    list_filter = ('type', 'created_at')

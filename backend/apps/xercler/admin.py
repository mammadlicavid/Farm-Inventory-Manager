from django.contrib import admin
from .models import Expense

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'date', 'created_by')
    list_filter = ('category', 'date', 'created_by')
    search_fields = ('category', 'description')

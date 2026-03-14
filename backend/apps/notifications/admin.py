from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'due_date', 'is_completed', 'created_by')
    list_filter = ('category', 'is_completed')
    search_fields = ('title',)

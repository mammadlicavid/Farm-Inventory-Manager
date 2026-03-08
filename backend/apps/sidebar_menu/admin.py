from django.contrib import admin
from .models import UserSettings


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display  = ['user', 'language', 'timezone', 'unit', 'currency', 'email_notifications']
    list_filter   = ['language', 'unit', 'currency']
    search_fields = ['user__username', 'user__email']
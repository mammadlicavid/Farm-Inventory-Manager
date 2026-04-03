from django.contrib import admin
from .models import EmailVerification, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "birth_date", "updated_at")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("email", "purpose", "user", "expires_at", "verified_at", "created_at")
    search_fields = ("email", "user__username")
    list_filter = ("purpose", "verified_at")

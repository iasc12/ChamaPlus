from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "phone_number",
        "trial_expires_at",
        "access_active",
        "access_expires_at",
        "platform_access_paid",
    )

    list_filter = (
        "role",
        "access_active",
        "platform_access_paid",
    )

    search_fields = (
        "user__username",
        "user__email",
        "phone_number",
    )

from django.contrib import admin

from .models import Chama, Membership


@admin.register(Chama)
class ChamaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "treasurer",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "treasurer__username",
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "chama",
        "role",
        "is_active",
        "joined_at",
    )
    list_filter = (
        "role",
        "is_active",
        "chama",
    )
    search_fields = (
        "user__username",
        "chama__name",
    )

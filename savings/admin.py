from django.contrib import admin

from .models import Saving


@admin.register(Saving)
class SavingAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "chama",
        "amount",
        "date",
        "recorded_by",
        "created_at",
    )

    list_filter = (
        "chama",
        "date",
    )

    search_fields = (
        "member__username",
        "member__email",
        "chama__name",
        "recorded_by__username",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

from django.contrib import admin

from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "chama",
        "amount_requested",
        "amount_approved",
        "amount_repaid",
        "status",
        "application_date",
    )

    list_filter = (
        "status",
        "chama",
        "application_date",
    )

    search_fields = (
        "member__username",
        "member__email",
        "chama__name",
    )

    readonly_fields = (
        "application_date",
        "created_at",
        "updated_at",
    )

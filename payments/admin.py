from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "payment_type",
        "amount",
        "status",
        "phone_number",
        "mpesa_receipt_number",
        "confirmed_by",
        "confirmed_at",
        "created_at",
    )

    list_filter = (
        "payment_type",
        "status",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "phone_number",
        "transaction_reference",
        "mpesa_receipt_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

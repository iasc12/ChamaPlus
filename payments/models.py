from django.contrib.auth.models import User
from django.db import models


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        PLATFORM_ACCESS = "PLATFORM_ACCESS", "Platform Access"
        LOAN_REPAYMENT = "LOAN_REPAYMENT", "Loan Repayment"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Awaiting Confirmation"
        COMPLETED = "COMPLETED", "Confirmed"
        FAILED = "FAILED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    payment_type = models.CharField(
        max_length=30,
        choices=PaymentType.choices,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    checkout_request_id = models.CharField(
        max_length=100,
        blank=True,
    )

    merchant_request_id = models.CharField(
        max_length=100,
        blank=True,
    )

    mpesa_receipt_number = models.CharField(
        max_length=100,
        blank=True,
    )

    transaction_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="confirmed_payments",
        null=True,
        blank=True,
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.get_payment_type_display()} - "
            f"KSh {self.amount}"
        )

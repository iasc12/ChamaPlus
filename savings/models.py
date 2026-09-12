from django.contrib.auth.models import User
from django.db import models

from chamas.models import Chama


class Saving(models.Model):
    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name="savings",
    )

    member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="savings",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    recorded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="recorded_savings",
    )

    date = models.DateField()

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.member.username} - "
            f"{self.chama.name} - "
            f"KSh {self.amount}"
        )


class WithdrawalRequest(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name="withdrawal_requests",
    )

    member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="withdrawal_requests",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="reviewed_withdrawals",
        null=True,
        blank=True,
    )

    review_notes = models.TextField(blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"{self.member.username} - "
            f"KSh {self.amount} - "
            f"{self.get_status_display()}"
        )

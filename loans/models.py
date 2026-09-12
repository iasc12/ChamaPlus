from django.contrib.auth.models import User
from django.db import models

from chamas.models import Chama


class Loan(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        DECLINED = "DECLINED", "Declined"
        DISBURSED = "DISBURSED", "Disbursed"
        COMPLETED = "COMPLETED", "Completed"

    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name="loans",
    )

    member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="loans",
    )

    amount_requested = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    amount_approved = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    amount_repaid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    purpose = models.TextField()

    application_date = models.DateField(
        auto_now_add=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    disbursed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="reviewed_loans",
        null=True,
        blank=True,
    )

    review_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    @property
    def outstanding_balance(self):
        if self.amount_approved is None:
            return 0

        total_due = self.amount_approved + (
            self.amount_approved * self.interest_rate / 100
        )

        balance = total_due - self.amount_repaid

        return max(balance, 0)

    def __str__(self):
        return (
            f"{self.member.username} - "
            f"{self.chama.name} - "
            f"KSh {self.amount_requested}"
        )


class LoanApproval(models.Model):

    class ReviewerRole(models.TextChoices):
        CHAIRLADY = "CHAIRLADY", "Chairlady"
        SECRETARY = "SECRETARY", "Secretary"
        TREASURER = "TREASURER", "Treasurer"

    class Decision(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="loan_approvals",
    )

    reviewer_role = models.CharField(
        max_length=20,
        choices=ReviewerRole.choices,
    )

    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
        default=Decision.PENDING,
    )

    notes = models.TextField(
        blank=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["loan", "reviewer_role"],
                name="unique_loan_reviewer_role",
            ),
        ]
        ordering = ["reviewer_role"]

    def __str__(self):
        return (
            f"{self.loan.member.username} - "
            f"{self.get_reviewer_role_display()} - "
            f"{self.get_decision_display()}"
        )

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "System Administrator"
        TREASURER = "TREASURER", "Treasurer"
        MEMBER = "MEMBER", "Member"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    trial_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    trial_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    access_active = models.BooleanField(
        default=False,
    )

    access_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    platform_access_paid = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

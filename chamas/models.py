from django.contrib.auth.models import User
from django.db import models


class Chama(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    treasurer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="managed_chamas",
        null=True,
        blank=True,
    )

    members = models.ManyToManyField(
        User,
        through="Membership",
        related_name="chamas",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        CHAIRLADY = "CHAIRLADY", "Chairlady"
        SECRETARY = "SECRETARY", "Secretary"
        TREASURER = "TREASURER", "Treasurer"
        MEMBER = "MEMBER", "Member"

    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chama_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["chama", "user"],
                name="unique_chama_membership",
            )
        ]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.chama.name} - "
            f"{self.get_role_display()}"
        )

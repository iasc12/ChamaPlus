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

    list_filter = (
        "is_active",
    )

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

    def save_model(self, request, obj, form, change):
        """
        Keep Chama.treasurer synchronized with the active
        Treasurer Membership.

        The Membership role is the authoritative source.
        """

        super().save_model(request, obj, form, change)

        chama = obj.chama

        # Find the active Treasurer membership for this Chama.
        treasurer_membership = (
            Membership.objects
            .filter(
                chama=chama,
                role=Membership.Role.TREASURER,
                is_active=True,
            )
            .select_related("user")
            .first()
        )

        # Synchronize the Chama.treasurer field.
        new_treasurer = (
            treasurer_membership.user
            if treasurer_membership
            else None
        )

        if chama.treasurer_id != (
            new_treasurer.id if new_treasurer else None
        ):
            chama.treasurer = new_treasurer
            chama.save(
                update_fields=[
                    "treasurer",
                    "updated_at",
                ]
            )

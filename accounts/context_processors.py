from chamas.models import Membership


def active_chama_membership(request):
    if not request.user.is_authenticated:
        return {
            "active_membership": None,
        }

    membership = (
        Membership.objects
        .filter(
            user=request.user,
            is_active=True,
            chama__is_active=True,
        )
        .select_related("chama")
        .first()
    )

    return {
        "active_membership": membership,
    }

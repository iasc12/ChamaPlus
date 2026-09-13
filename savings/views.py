from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from chamas.models import Chama, Membership

from .models import Saving, WithdrawalRequest


def withdrawals_are_open():
    """
    Savings withdrawals remain closed until the Annual General Meeting.

    This is intentionally centralized so both the member withdrawal
    request and Treasurer approval logic use the same rule.
    """
    return False


def can_record_savings(user):
    """
    Only the Treasurer of the active Chama can record savings.
    """
    chama = Chama.objects.filter(is_active=True).first()

    if not chama:
        return False

    return Membership.objects.filter(
        chama=chama,
        user=user,
        role=Membership.Role.TREASURER,
        is_active=True,
    ).exists()


def is_treasurer(user, chama=None):
    """
    Check whether the user is the active Treasurer of the Chama.
    """
    if chama is None:
        chama = Chama.objects.filter(is_active=True).first()

    if not chama:
        return False

    return Membership.objects.filter(
        chama=chama,
        user=user,
        role=Membership.Role.TREASURER,
        is_active=True,
    ).exists()


def get_next_saturday():
    """
    Return the next Saturday.

    If today is Saturday, today's date is returned.
    """
    today = timezone.localdate()

    days_until_saturday = (5 - today.weekday()) % 7

    return today + timezone.timedelta(days=days_until_saturday)


def get_member_balance(user, chama):
    """
    Calculate the member's available savings balance.

    Savings are reduced by both approved and pending withdrawals.
    Pending withdrawals are reserved so that a member cannot submit
    multiple requests that exceed their available savings.
    """
    total_savings = (
        Saving.objects.filter(
            chama=chama,
            member=user,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    withdrawals_reserved = (
        WithdrawalRequest.objects.filter(
            chama=chama,
            member=user,
            status__in=[
                WithdrawalRequest.Status.PENDING,
                WithdrawalRequest.Status.APPROVED,
            ],
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    balance = total_savings - withdrawals_reserved

    return max(balance, Decimal("0.00"))


@login_required
def savings_dashboard(request):
    savings = (
        Saving.objects
        .filter(member=request.user)
        .select_related("chama", "recorded_by")
        .order_by("-date", "-created_at")
    )

    total_savings = (
        savings.aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    chama = Chama.objects.filter(is_active=True).first()

    available_balance = Decimal("0.00")

    if chama:
        available_balance = get_member_balance(
            request.user,
            chama,
        )

    next_saturday = get_next_saturday()


    withdrawal_requests = (
        WithdrawalRequest.objects
        .filter(member=request.user)
        .select_related("chama", "reviewed_by")
        .order_by("-requested_at")
    )

    return render(
        request,
        "savings/dashboard.html",
        {
            "savings": savings,
            "total_savings": total_savings,
            "available_balance": available_balance,
            "can_record": can_record_savings(request.user),
            "next_saturday": next_saturday,
            "withdrawal_requests": withdrawal_requests,
        },
    )


@login_required
def record_saving(request):
    if not can_record_savings(request.user):
        messages.error(
            request,
            "Only the Chama Treasurer can record savings.",
        )
        return redirect("savings")

    chama = Chama.objects.filter(is_active=True).first()

    if not chama:
        messages.error(
            request,
            "No active Chama has been created yet.",
        )
        return redirect("savings")

    memberships = (
        Membership.objects
        .filter(
            chama=chama,
            is_active=True,
        )
        .select_related("user")
        .order_by("user__username")
    )

    members = [membership.user for membership in memberships]

    today = timezone.localdate()

    # Current Monday-Sunday week.
    week_start = today - timezone.timedelta(days=today.weekday())
    week_end = week_start + timezone.timedelta(days=6)

    if request.method == "POST":
        member_id = request.POST.get("member")
        amount = request.POST.get("amount", "").strip()
        date = request.POST.get("date", "").strip()
        notes = request.POST.get("notes", "").strip()

        if not member_id or not amount or not date:
            messages.error(
                request,
                "Please select a member, enter the amount, and choose the date.",
            )

            return render(
                request,
                "savings/record.html",
                {
                    "members": members,
                    "today": today,
                    "chama": chama,
                    "week_start": week_start,
                    "week_end": week_end,
                },
            )

        membership = get_object_or_404(
            Membership,
            chama=chama,
            user_id=member_id,
            is_active=True,
        )

        member = membership.user

        try:
            amount_value = Decimal(amount)

            if amount_value <= 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError):
            messages.error(
                request,
                "Please enter a valid savings amount greater than zero.",
            )

            return render(
                request,
                "savings/record.html",
                {
                    "members": members,
                    "today": today,
                    "chama": chama,
                    "week_start": week_start,
                    "week_end": week_end,
                },
            )

        Saving.objects.create(
            chama=chama,
            member=member,
            amount=amount_value,
            date=date,
            notes=notes,
            recorded_by=request.user,
        )

        member_name = member.get_full_name() or member.username

        messages.success(
            request,
            f"KSh {amount_value:,.2f} savings recorded for {member_name}.",
        )

        return redirect("savings")

    return render(
        request,
        "savings/record.html",
        {
            "members": members,
            "today": today,
            "chama": chama,
            "week_start": week_start,
            "week_end": week_end,
        },
    )


@login_required
def request_withdrawal(request):
    """
    Display the savings withdrawal page for every active Chama member.

    Withdrawals remain closed until the Annual General Meeting.
    The page is intentionally accessible so members can see the
    current withdrawal status.
    """
    chama = Chama.objects.filter(is_active=True).first()

    if not chama:
        messages.error(
            request,
            "No active Chama has been created yet.",
        )
        return redirect("savings")

    membership = Membership.objects.filter(
        chama=chama,
        user=request.user,
        is_active=True,
    ).first()

    if not membership:
        messages.error(
            request,
            "You are not an active member of this Chama.",
        )
        return redirect("savings")

    available_balance = get_member_balance(
        request.user,
        chama,
    )

    withdrawals_open = withdrawals_are_open()

    if not withdrawals_open:
        return render(
            request,
            "savings/withdraw.html",
            {
                "chama": chama,
                "available_balance": available_balance,
                "withdrawals_open": False,
            },
        )

    # Withdrawals remain closed until the Annual General Meeting.
    withdrawals_open = False

    if not withdrawals_open:
        return render(
            request,
            "savings/withdraw.html",
            {
                "chama": chama,
                "available_balance": available_balance,
                "withdrawals_open": False,
            },
        )

    if request.method == "POST":
        amount = request.POST.get("amount", "").strip()
        reason = request.POST.get("reason", "").strip()

        try:
            amount_value = Decimal(amount)

            if amount_value <= 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError):
            messages.error(
                request,
                "Please enter a valid withdrawal amount greater than zero.",
            )

            return render(
                request,
                "savings/withdraw.html",
                {
                    "chama": chama,
                    "available_balance": available_balance,
                    "withdrawals_open": True,
                },
            )

        if amount_value > available_balance:
            messages.error(
                request,
                (
                    f"Withdrawal amount cannot exceed your available "
                    f"savings balance of KSh {available_balance:,.2f}."
                ),
            )

            return render(
                request,
                "savings/withdraw.html",
                {
                    "chama": chama,
                    "available_balance": available_balance,
                    "withdrawals_open": True,
                },
            )

        WithdrawalRequest.objects.create(
            chama=chama,
            member=request.user,
            amount=amount_value,
            reason=reason,
        )

        messages.success(
            request,
            (
                f"Your withdrawal request of KSh "
                f"{amount_value:,.2f} has been submitted."
            ),
        )

        return redirect("withdrawal_history")

    return render(
        request,
        "savings/withdraw.html",
        {
            "chama": chama,
            "available_balance": available_balance,
            "withdrawals_open": True,
        },
    )


@login_required
def withdrawal_history(request):
    requests = (
        WithdrawalRequest.objects
        .filter(member=request.user)
        .select_related("chama", "reviewed_by")
        .order_by("-requested_at")
    )

    return render(
        request,
        "savings/withdrawal_history.html",
        {
            "withdrawal_requests": requests,
        },
    )


@login_required
def manage_withdrawals(request):
    """
    Treasurer-only withdrawal management.
    """
    chama = Chama.objects.filter(is_active=True).first()

    if not chama:
        messages.error(
            request,
            "No active Chama has been created yet.",
        )
        return redirect("dashboard")

    if not is_treasurer(request.user, chama):
        messages.error(
            request,
            "Only the Chama Treasurer can manage withdrawal requests.",
        )
        return redirect("dashboard")

    withdrawal_requests = (
        WithdrawalRequest.objects
        .filter(chama=chama)
        .select_related("member", "reviewed_by")
        .order_by("-requested_at")
    )

    return render(
        request,
        "savings/manage_withdrawals.html",
        {
            "chama": chama,
            "withdrawal_requests": withdrawal_requests,
        },
    )


@login_required
def approve_withdrawal(request, withdrawal_id):
    """
    Treasurer approves a pending withdrawal.

    The balance is checked again immediately before approval.
    """
    chama = Chama.objects.filter(is_active=True).first()

    if not chama or not is_treasurer(request.user, chama):
        messages.error(
            request,
            "Only the Chama Treasurer can approve withdrawals.",
        )
        return redirect("dashboard")

    withdrawal = get_object_or_404(
        WithdrawalRequest.objects.select_related("member"),
        id=withdrawal_id,
        chama=chama,
    )

    if request.method != "POST":
        return redirect("manage_withdrawals")

    if not withdrawals_are_open():
        messages.error(
            request,
            "Savings withdrawals cannot be approved until after the Annual General Meeting.",
        )
        return redirect("manage_withdrawals")

    if withdrawal.status != WithdrawalRequest.Status.PENDING:
        messages.error(
            request,
            "This withdrawal request has already been reviewed.",
        )
        return redirect("manage_withdrawals")

    available_balance = get_member_balance(
        withdrawal.member,
        chama,
    )

    if withdrawal.amount > available_balance:
        withdrawal.status = WithdrawalRequest.Status.REJECTED
        withdrawal.reviewed_by = request.user
        withdrawal.reviewed_at = timezone.now()
        withdrawal.review_notes = (
            "Rejected because the member no longer has sufficient "
            "available savings."
        )
        withdrawal.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "review_notes",
            ]
        )

        messages.error(
            request,
            "Withdrawal rejected because the member has insufficient available savings.",
        )

        return redirect("manage_withdrawals")

    withdrawal.status = WithdrawalRequest.Status.APPROVED
    withdrawal.reviewed_by = request.user
    withdrawal.reviewed_at = timezone.now()
    withdrawal.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    messages.success(
        request,
        (
            f"Withdrawal of KSh {withdrawal.amount:,.2f} "
            f"approved for {withdrawal.member.get_full_name() or withdrawal.member.username}."
        ),
    )

    return redirect("manage_withdrawals")


@login_required
def reject_withdrawal(request, withdrawal_id):
    """
    Treasurer rejects a pending withdrawal.
    """
    chama = Chama.objects.filter(is_active=True).first()

    if not chama or not is_treasurer(request.user, chama):
        messages.error(
            request,
            "Only the Chama Treasurer can reject withdrawals.",
        )
        return redirect("dashboard")

    withdrawal = get_object_or_404(
        WithdrawalRequest,
        id=withdrawal_id,
        chama=chama,
    )

    if request.method != "POST":
        return redirect("manage_withdrawals")

    if withdrawal.status != WithdrawalRequest.Status.PENDING:
        messages.error(
            request,
            "This withdrawal request has already been reviewed.",
        )
        return redirect("manage_withdrawals")

    review_notes = request.POST.get("review_notes", "").strip()

    withdrawal.status = WithdrawalRequest.Status.REJECTED
    withdrawal.reviewed_by = request.user
    withdrawal.reviewed_at = timezone.now()
    withdrawal.review_notes = review_notes

    withdrawal.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
        ]
    )

    messages.success(
        request,
        "Withdrawal request rejected.",
    )

    return redirect("manage_withdrawals")

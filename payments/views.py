from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Payment


def is_system_admin(user):
    if user.is_superuser:
        return True

    if hasattr(user, "profile"):
        return user.profile.role == "ADMIN"

    return False


@login_required
def payment(request):
    profile = request.user.profile

    if profile.access_active:
        return redirect("dashboard")

    pending_payment = Payment.objects.filter(
        user=request.user,
        payment_type=Payment.PaymentType.PLATFORM_ACCESS,
        status=Payment.Status.PENDING,
    ).order_by("-created_at").first()

    if request.method == "POST":

        if pending_payment:
            messages.info(
                request,
                "You already have a payment awaiting administrator confirmation.",
            )
            return redirect("payment")

        phone_number = request.POST.get("phone_number", "").strip()
        transaction_reference = request.POST.get(
            "transaction_reference",
            "",
        ).strip()
        notes = request.POST.get("notes", "").strip()

        if not phone_number or not transaction_reference:
            messages.error(
                request,
                "Please enter the phone number used to pay and the M-Pesa transaction reference.",
            )
            return render(
                request,
                "payments/payment.html",
                {
                    "pending_payment": pending_payment,
                },
            )

        Payment.objects.create(
            user=request.user,
            payment_type=Payment.PaymentType.PLATFORM_ACCESS,
            amount=20,
            status=Payment.Status.PENDING,
            phone_number=phone_number,
            transaction_reference=transaction_reference,
            notes=notes,
        )

        messages.success(
            request,
            "Your payment has been submitted and is awaiting administrator confirmation.",
        )

        return redirect("payment")

    return render(
        request,
        "payments/payment.html",
        {
            "pending_payment": pending_payment,
        },
    )


@login_required
def payment_approvals(request):
    if not is_system_admin(request.user):
        messages.error(
            request,
            "Only the system administrator can approve payments.",
        )
        return redirect("dashboard")

    pending_payments = (
        Payment.objects
        .filter(
            payment_type=Payment.PaymentType.PLATFORM_ACCESS,
            status=Payment.Status.PENDING,
        )
        .select_related(
            "user",
            "user__profile",
        )
        .order_by("-created_at")
    )

    completed_count = Payment.objects.filter(
        payment_type=Payment.PaymentType.PLATFORM_ACCESS,
        status=Payment.Status.COMPLETED,
    ).count()

    denied_count = Payment.objects.filter(
        payment_type=Payment.PaymentType.PLATFORM_ACCESS,
        status=Payment.Status.FAILED,
    ).count()

    return render(
        request,
        "payments/approvals.html",
        {
            "pending_payments": pending_payments,
            "completed_count": completed_count,
            "denied_count": denied_count,
        },
    )


@login_required
def approve_payment(request, payment_id):
    if not is_system_admin(request.user):
        messages.error(
            request,
            "Only the system administrator can approve payments.",
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("payment_approvals")

    payment_record = get_object_or_404(
        Payment.objects.select_related(
            "user",
            "user__profile",
        ),
        id=payment_id,
        payment_type=Payment.PaymentType.PLATFORM_ACCESS,
    )

    if payment_record.status != Payment.Status.PENDING:
        messages.warning(
            request,
            "This payment has already been processed.",
        )
        return redirect("payment_approvals")

    payment_record.status = Payment.Status.COMPLETED
    payment_record.confirmed_by = request.user
    payment_record.confirmed_at = timezone.now()

    payment_record.save(
        update_fields=[
            "status",
            "confirmed_by",
            "confirmed_at",
            "updated_at",
        ]
    )

    profile = payment_record.user.profile
    profile.access_active = True
    profile.platform_access_paid = True

    profile.save(
        update_fields=[
            "access_active",
            "platform_access_paid",
            "updated_at",
        ]
    )

    messages.success(
        request,
        f"Payment from {payment_record.user.username} has been approved.",
    )

    return redirect("payment_approvals")


@login_required
def deny_payment(request, payment_id):
    if not is_system_admin(request.user):
        messages.error(
            request,
            "Only the system administrator can deny payments.",
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("payment_approvals")

    payment_record = get_object_or_404(
        Payment.objects.select_related(
            "user",
            "user__profile",
        ),
        id=payment_id,
        payment_type=Payment.PaymentType.PLATFORM_ACCESS,
    )

    if payment_record.status != Payment.Status.PENDING:
        messages.warning(
            request,
            "This payment has already been processed.",
        )
        return redirect("payment_approvals")

    payment_record.status = Payment.Status.FAILED
    payment_record.confirmed_by = request.user
    payment_record.confirmed_at = timezone.now()

    payment_record.save(
        update_fields=[
            "status",
            "confirmed_by",
            "confirmed_at",
            "updated_at",
        ]
    )

    messages.warning(
        request,
        f"Payment from {payment_record.user.username} has been denied.",
    )

    return redirect("payment_approvals")

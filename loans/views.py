from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from chamas.models import Chama, Membership
from savings.models import Saving

from .models import Loan, LoanApproval


COMMITTEE_ROLES = [
    Membership.Role.CHAIRLADY,
    Membership.Role.SECRETARY,
    Membership.Role.TREASURER,
]


def get_active_chama():
    return Chama.objects.filter(is_active=True).first()


def get_membership(user, chama):
    return Membership.objects.filter(
        chama=chama,
        user=user,
        is_active=True,
    ).first()


def get_savings_total(user, chama):
    return (
        Saving.objects
        .filter(
            chama=chama,
            member=user,
        )
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )


def get_first_saving(user, chama):
    return (
        Saving.objects
        .filter(
            chama=chama,
            member=user,
        )
        .order_by("date", "created_at")
        .first()
    )


def get_loan_eligibility(user, chama):
    savings_total = get_savings_total(user, chama)
    first_saving = get_first_saving(user, chama)

    today = timezone.localdate()

    eligible_after = None
    eligible = False

    if first_saving:
        eligible_after = first_saving.date + timedelta(days=180)
        eligible = today >= eligible_after

    maximum_loan = savings_total * Decimal("2")

    return {
        "savings_total": savings_total,
        "first_saving": first_saving,
        "eligible_after": eligible_after,
        "eligible": eligible,
        "maximum_loan": maximum_loan,
    }


def create_loan_approvals(loan):
    """
    Create one approval record for every active committee officer.

    Every loan requires decisions from:
    - Chairlady
    - Secretary
    - Treasurer
    """

    committee_memberships = (
        Membership.objects
        .filter(
            chama=loan.chama,
            role__in=COMMITTEE_ROLES,
            is_active=True,
        )
        .select_related("user")
    )

    for membership in committee_memberships:
        LoanApproval.objects.get_or_create(
            loan=loan,
            reviewer=membership.user,
            reviewer_role=membership.role,
        )


def update_loan_status(loan):
    """
    Recalculate the overall loan status.

    Any rejection immediately rejects the loan.

    Approval happens only after all three required committee
    officers have approved.
    """

    approvals = loan.approvals.all()

    required_roles = {
        LoanApproval.ReviewerRole.CHAIRLADY,
        LoanApproval.ReviewerRole.SECRETARY,
        LoanApproval.ReviewerRole.TREASURER,
    }

    approval_roles = set(
        approvals.values_list(
            "reviewer_role",
            flat=True,
        )
    )

    if not required_roles.issubset(approval_roles):
        loan.status = Loan.Status.PENDING
        loan.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )
        return

    if approvals.filter(
        decision=LoanApproval.Decision.REJECTED
    ).exists():

        loan.status = Loan.Status.DECLINED

        loan.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return

    approved_roles = set(
        approvals.filter(
            decision=LoanApproval.Decision.APPROVED
        ).values_list(
            "reviewer_role",
            flat=True,
        )
    )

    if required_roles.issubset(approved_roles):

        loan.status = Loan.Status.APPROVED
        loan.amount_approved = loan.amount_requested
        loan.approved_at = timezone.now()

        loan.save(
            update_fields=[
                "status",
                "amount_approved",
                "approved_at",
                "updated_at",
            ]
        )

        return

    loan.status = Loan.Status.PENDING

    loan.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )


@login_required
def loan_dashboard(request):

    chama = get_active_chama()

    if not chama:
        messages.error(
            request,
            "No active Chama has been created yet.",
        )
        return redirect("dashboard")

    membership = get_membership(
        request.user,
        chama,
    )

    if not membership:
        messages.error(
            request,
            "You are not an active member of this Chama.",
        )
        return redirect("dashboard")

    eligibility = get_loan_eligibility(
        request.user,
        chama,
    )

    loans = (
        Loan.objects
        .filter(
            chama=chama,
            member=request.user,
        )
        .prefetch_related("approvals")
        .order_by("-created_at")
    )

    active_loan = loans.filter(
        status__in=[
            Loan.Status.PENDING,
            Loan.Status.APPROVED,
            Loan.Status.DISBURSED,
        ]
    ).first()

    return render(
        request,
        "loans/dashboard.html",
        {
            "chama": chama,
            "membership": membership,
            "savings_total": eligibility["savings_total"],
            "first_saving": eligibility["first_saving"],
            "eligible_after": eligibility["eligible_after"],
            "eligible": eligibility["eligible"],
            "maximum_loan": eligibility["maximum_loan"],
            "loans": loans,
            "active_loan": active_loan,
        },
    )


@login_required
def apply_for_loan(request):

    chama = get_active_chama()

    if not chama:
        messages.error(
            request,
            "No active Chama has been created yet.",
        )
        return redirect("dashboard")

    membership = get_membership(
        request.user,
        chama,
    )

    if not membership:
        messages.error(
            request,
            "You are not an active member of this Chama.",
        )
        return redirect("loans")

    eligibility = get_loan_eligibility(
        request.user,
        chama,
    )

    savings_total = eligibility["savings_total"]
    maximum_loan = eligibility["maximum_loan"]
    eligible = eligibility["eligible"]
    eligible_after = eligibility["eligible_after"]

    active_loan = Loan.objects.filter(
        chama=chama,
        member=request.user,
        status__in=[
            Loan.Status.PENDING,
            Loan.Status.APPROVED,
            Loan.Status.DISBURSED,
        ],
    ).exists()

    if not eligible:
        messages.error(
            request,
            "You must have at least six months of savings before applying for a loan.",
        )
        return redirect("loans")

    if maximum_loan <= 0:
        messages.error(
            request,
            "You do not have enough savings to qualify for a loan.",
        )
        return redirect("loans")

    if active_loan:
        messages.error(
            request,
            "You already have an active loan application or loan.",
        )
        return redirect("loans")

    if request.method == "POST":

        amount = request.POST.get(
            "amount",
            "",
        ).strip()

        purpose = request.POST.get(
            "purpose",
            "",
        ).strip()

        if not amount or not purpose:

            messages.error(
                request,
                "Please enter the loan amount and purpose.",
            )

            return render(
                request,
                "loans/apply.html",
                {
                    "chama": chama,
                    "savings_total": savings_total,
                    "maximum_loan": maximum_loan,
                    "eligible_after": eligible_after,
                },
            )

        try:
            amount_requested = Decimal(amount)

        except (InvalidOperation, ValueError):

            messages.error(
                request,
                "Please enter a valid loan amount.",
            )

            return render(
                request,
                "loans/apply.html",
                {
                    "chama": chama,
                    "savings_total": savings_total,
                    "maximum_loan": maximum_loan,
                    "eligible_after": eligible_after,
                },
            )

        if amount_requested <= 0:

            messages.error(
                request,
                "Loan amount must be greater than zero.",
            )

            return render(
                request,
                "loans/apply.html",
                {
                    "chama": chama,
                    "savings_total": savings_total,
                    "maximum_loan": maximum_loan,
                    "eligible_after": eligible_after,
                },
            )

        if amount_requested > maximum_loan:

            messages.error(
                request,
                f"Your maximum eligible loan is KSh {maximum_loan:,.2f}.",
            )

            return render(
                request,
                "loans/apply.html",
                {
                    "chama": chama,
                    "savings_total": savings_total,
                    "maximum_loan": maximum_loan,
                    "eligible_after": eligible_after,
                },
            )

        loan = Loan.objects.create(
            chama=chama,
            member=request.user,
            amount_requested=amount_requested,
            purpose=purpose,
            status=Loan.Status.PENDING,
        )

        create_loan_approvals(loan)

        messages.success(
            request,
            "Your loan application has been submitted and is awaiting all three committee decisions.",
        )

        return redirect("loans")

    return render(
        request,
        "loans/apply.html",
        {
            "chama": chama,
            "savings_total": savings_total,
            "maximum_loan": maximum_loan,
            "eligible_after": eligible_after,
        },
    )


@login_required
def review_loans(request):

    chama = get_active_chama()

    if not chama:
        messages.error(
            request,
            "No active Chama has been created yet.",
        )
        return redirect("dashboard")

    membership = get_membership(
        request.user,
        chama,
    )

    if not membership or membership.role not in COMMITTEE_ROLES:
        messages.error(
            request,
            "Only Chama committee members can review loans.",
        )
        return redirect("dashboard")

    loans = (
        Loan.objects
        .filter(
            chama=chama,
            status=Loan.Status.PENDING,
            approvals__reviewer=request.user,
            approvals__reviewer_role=membership.role,
            approvals__decision=LoanApproval.Decision.PENDING,
        )
        .select_related("member")
        .prefetch_related("approvals")
        .distinct()
        .order_by("-created_at")
    )

    return render(
        request,
        "loans/review_list.html",
        {
            "chama": chama,
            "membership": membership,
            "loans": loans,
        },
    )


@login_required
def review_loan(request, loan_id):

    chama = get_active_chama()

    if not chama:
        messages.error(
            request,
            "No active Chama has been created yet.",
        )
        return redirect("dashboard")

    membership = get_membership(
        request.user,
        chama,
    )

    if not membership or membership.role not in COMMITTEE_ROLES:
        messages.error(
            request,
            "Only Chama committee members can review loans.",
        )
        return redirect("dashboard")

    loan = get_object_or_404(
        Loan.objects
        .select_related(
            "member",
            "chama",
        )
        .prefetch_related(
            "approvals__reviewer",
        ),
        id=loan_id,
        chama=chama,
    )

    if loan.member_id == request.user.id:
        messages.error(
            request,
            "You cannot review your own loan application.",
        )
        return redirect("review_loans")

    approval = loan.approvals.filter(
        reviewer=request.user,
        reviewer_role=membership.role,
    ).first()

    if not approval:
        messages.error(
            request,
            "You are not assigned to review this loan.",
        )
        return redirect("review_loans")

    if loan.status != Loan.Status.PENDING:
        messages.error(
            request,
            "This loan is no longer awaiting committee review.",
        )
        return redirect("review_loans")

    if request.method == "POST":

        decision = request.POST.get(
            "decision",
            "",
        ).strip().upper()

        notes = request.POST.get(
            "notes",
            "",
        ).strip()

        if decision not in [
            LoanApproval.Decision.APPROVED,
            LoanApproval.Decision.REJECTED,
        ]:
            messages.error(
                request,
                "Please choose Approve or Reject.",
            )
            return redirect(
                "review_loan",
                loan_id=loan.id,
            )

        if approval.decision != LoanApproval.Decision.PENDING:
            messages.error(
                request,
                "You have already reviewed this loan.",
            )
            return redirect("review_loans")

        approval.decision = decision
        approval.notes = notes
        approval.reviewed_at = timezone.now()

        approval.save(
            update_fields=[
                "decision",
                "notes",
                "reviewed_at",
                "updated_at",
            ]
        )

        update_loan_status(loan)
        loan.refresh_from_db()

        if decision == LoanApproval.Decision.REJECTED:

            messages.error(
                request,
                "Your rejection has been recorded. The loan application has been rejected.",
            )

        elif loan.status == Loan.Status.APPROVED:

            messages.success(
                request,
                "All three committee officers have approved the loan. The loan is now approved.",
            )

        else:

            remaining = loan.approvals.filter(
                decision=LoanApproval.Decision.PENDING,
            ).count()

            messages.success(
                request,
                f"Your approval has been recorded. {remaining} committee decision(s) remain.",
            )

        return redirect("review_loans")

    return render(
        request,
        "loans/review.html",
        {
            "chama": chama,
            "loan": loan,
            "approval": approval,
            "approvals": loan.approvals.all(),
            "membership": membership,
        },
    )

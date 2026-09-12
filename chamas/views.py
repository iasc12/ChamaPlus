from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from loans.models import Loan, LoanApproval
from savings.models import Saving

from .models import Chama, Membership


def is_system_admin(user):
    if user.is_superuser:
        return True

    if hasattr(user, "profile"):
        return user.profile.role == "ADMIN"

    return False


def is_committee_member(user, chama):
    """
    A Chama committee member is a Chairlady, Secretary or Treasurer.
    All committee members are also full Chama members.
    """
    return Membership.objects.filter(
        chama=chama,
        user=user,
        role__in=[
            Membership.Role.CHAIRLADY,
            Membership.Role.SECRETARY,
            Membership.Role.TREASURER,
        ],
        is_active=True,
    ).exists()


def is_treasurer(user, chama):
    """
    Kept for existing Treasurer-specific functionality.
    """
    return Membership.objects.filter(
        chama=chama,
        user=user,
        role=Membership.Role.TREASURER,
        is_active=True,
    ).exists()


@login_required
def chama_management(request):
    if not is_system_admin(request.user):
        messages.error(
            request,
            "Only the system administrator can manage the Chama.",
        )
        return redirect("dashboard")

    chama = Chama.objects.first()

    if not chama:
        messages.error(
            request,
            "No Chama has been created yet.",
        )
        return redirect("dashboard")

    if request.method == "POST":
        role = request.POST.get("role", "").strip()
        user_id = request.POST.get("user_id", "").strip()

        valid_roles = {
            Membership.Role.CHAIRLADY,
            Membership.Role.SECRETARY,
            Membership.Role.TREASURER,
            Membership.Role.MEMBER,
        }

        if role not in valid_roles:
            messages.error(
                request,
                "Please select a valid Chama role.",
            )
            return redirect("chama_management")

        if not user_id:
            messages.error(
                request,
                "Please select a person.",
            )
            return redirect("chama_management")

        user = get_object_or_404(
            User,
            id=user_id,
            is_active=True,
        )

        # Assigning ordinary Member role.
        if role == Membership.Role.MEMBER:

            membership, created = Membership.objects.get_or_create(
                chama=chama,
                user=user,
                defaults={
                    "role": Membership.Role.MEMBER,
                    "is_active": True,
                },
            )

            if not created:
                membership.role = Membership.Role.MEMBER
                membership.is_active = True
                membership.save(
                    update_fields=[
                        "role",
                        "is_active",
                    ]
                )

            # Keep the legacy treasurer field synchronized.
            if chama.treasurer_id == user.id:
                chama.treasurer = None
                chama.save(
                    update_fields=[
                        "treasurer",
                        "updated_at",
                    ]
                )

            messages.success(
                request,
                f"{user.username} is now an ordinary Chama member.",
            )

            return redirect("chama_management")

        # Only one person can hold each committee position.
        current_holder = (
            Membership.objects
            .filter(
                chama=chama,
                role=role,
                is_active=True,
            )
            .exclude(user=user)
            .select_related("user")
            .first()
        )

        if current_holder:
            current_holder.role = Membership.Role.MEMBER
            current_holder.save(
                update_fields=["role"]
            )

        # Find the selected person's existing Chama membership.
        membership = (
            Membership.objects
            .filter(
                chama=chama,
                user=user,
            )
            .first()
        )

        if membership:
            membership.role = role
            membership.is_active = True
            membership.save(
                update_fields=[
                    "role",
                    "is_active",
                ]
            )
        else:
            Membership.objects.create(
                chama=chama,
                user=user,
                role=role,
                is_active=True,
            )

        # Keep Chama.treasurer synchronized.
        if role == Membership.Role.TREASURER:

            chama.treasurer = user

            chama.save(
                update_fields=[
                    "treasurer",
                    "updated_at",
                ]
            )

        elif chama.treasurer_id == user.id:

            chama.treasurer = None

            chama.save(
                update_fields=[
                    "treasurer",
                    "updated_at",
                ]
            )

        role_name = dict(Membership.Role.choices)[role]

        messages.success(
            request,
            f"{user.username} is now the {role_name.lower()}.",
        )

        return redirect("chama_management")

    memberships = (
        Membership.objects
        .filter(
            chama=chama,
            is_active=True,
        )
        .select_related(
            "user",
            "user__profile",
        )
        .order_by(
            "role",
            "user__username",
        )
    )

    users = (
        User.objects
        .filter(is_active=True)
        .order_by("username")
    )

    chairlady = memberships.filter(
        role=Membership.Role.CHAIRLADY
    ).first()

    secretary = memberships.filter(
        role=Membership.Role.SECRETARY
    ).first()

    treasurer = memberships.filter(
        role=Membership.Role.TREASURER
    ).first()

    return render(
        request,
        "chamas/management.html",
        {
            "chama": chama,
            "members": memberships,
            "users": users,
            "chairlady": chairlady,
            "secretary": secretary,
            "treasurer": treasurer,
        },
    )


@login_required
def create_treasurer(request):
    if not is_system_admin(request.user):
        messages.error(
            request,
            "Only the system administrator can manage the Chama committee.",
        )
        return redirect("dashboard")

    chama = Chama.objects.first()

    if not chama:
        messages.error(
            request,
            "No Chama has been created yet.",
        )
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        if not username:
            messages.error(
                request,
                "Please enter a username.",
            )

            return render(
                request,
                "chamas/create_treasurer.html",
                {"chama": chama},
            )

        user = get_object_or_404(
            User,
            username=username,
        )

        membership, created = Membership.objects.get_or_create(
            chama=chama,
            user=user,
            defaults={
                "role": Membership.Role.TREASURER,
                "is_active": True,
            },
        )

        if not created:

            membership.role = Membership.Role.TREASURER
            membership.is_active = True

            membership.save(
                update_fields=[
                    "role",
                    "is_active",
                ]
            )

        if hasattr(user, "profile"):

            user.profile.role = "TREASURER"

            user.profile.save(
                update_fields=[
                    "role",
                    "updated_at",
                ]
            )

        chama.treasurer = user

        chama.save(
            update_fields=[
                "treasurer",
                "updated_at",
            ]
        )

        messages.success(
            request,
            f"{user.username} is now the Chama treasurer.",
        )

        return redirect("chama_management")

    return render(
        request,
        "chamas/create_treasurer.html",
        {
            "chama": chama,
        },
    )


@login_required
def treasurer_dashboard(request):
    chama = Chama.objects.first()

    if not chama:
        messages.error(
            request,
            "No Chama has been created yet.",
        )
        return redirect("dashboard")

    if not is_committee_member(request.user, chama):
        messages.error(
            request,
            "Only Chama committee members can access this dashboard.",
        )
        return redirect("dashboard")

    today = timezone.localdate()
    month_start = today.replace(day=1)

    total_savings = (
        Saving.objects
        .filter(chama=chama)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    monthly_savings = (
        Saving.objects
        .filter(
            chama=chama,
            date__gte=month_start,
            date__lte=today,
        )
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    member_count = Membership.objects.filter(
        chama=chama,
        is_active=True,
    ).count()

    active_loans = Loan.objects.filter(
        chama=chama,
        status__in=[
            Loan.Status.APPROVED,
            Loan.Status.DISBURSED,
        ],
    ).count()

    pending_loans = Loan.objects.filter(
        chama=chama,
        status=Loan.Status.PENDING,
    ).count()

    pending_reviews = LoanApproval.objects.filter(
        loan__chama=chama,
        reviewer=request.user,
        decision=LoanApproval.Decision.PENDING,
        loan__status=Loan.Status.PENDING,
    ).count()

    recent_savings = (
        Saving.objects
        .filter(chama=chama)
        .select_related(
            "member",
            "recorded_by",
        )
        .order_by(
            "-date",
            "-created_at",
        )[:8]
    )

    current_membership = Membership.objects.filter(
        chama=chama,
        user=request.user,
        is_active=True,
    ).first()

    return render(
        request,
        "chamas/treasurer_dashboard.html",
        {
            "chama": chama,
            "member_count": member_count,
            "total_savings": total_savings,
            "monthly_savings": monthly_savings,
            "active_loans": active_loans,
            "pending_loans": pending_loans,
            "pending_reviews": pending_reviews,
            "recent_savings": recent_savings,
            "committee_role": (
                current_membership.get_role_display()
                if current_membership
                else "Committee"
            ),
        },
    )


@login_required
def chama_members(request):
    chama = Chama.objects.first()

    if not chama:
        messages.error(
            request,
            "No Chama has been created yet.",
        )
        return redirect("dashboard")

    if not is_committee_member(request.user, chama):
        messages.error(
            request,
            "Only Chama committee members can access the members page.",
        )
        return redirect("dashboard")

    members = (
        Membership.objects
        .filter(
            chama=chama,
            is_active=True,
        )
        .select_related(
            "user",
            "user__profile",
        )
        .annotate(
            total_savings=Sum(
                "user__savings__amount",
                filter=Q(
                    user__savings__chama=chama,
                ),
            ),
            savings_count=Count(
                "user__savings",
                filter=Q(
                    user__savings__chama=chama,
                ),
                distinct=True,
            ),
        )
        .order_by(
            "role",
            "user__username",
        )
    )

    return render(
        request,
        "chamas/members.html",
        {
            "chama": chama,
            "members": members,
        },
    )


@login_required
def treasurer_loans(request):
    chama = Chama.objects.first()

    if not chama:
        messages.error(
            request,
            "No Chama has been created yet.",
        )
        return redirect("dashboard")

    if not is_committee_member(request.user, chama):
        messages.error(
            request,
            "Only Chama committee members can access loan management.",
        )
        return redirect("dashboard")

    loans = (
        Loan.objects
        .filter(chama=chama)
        .select_related(
            "member",
            "member__profile",
            "reviewed_by",
        )
        .order_by(
            "-application_date",
            "-created_at",
        )
    )

    pending_count = loans.filter(
        status=Loan.Status.PENDING
    ).count()

    approved_count = loans.filter(
        status=Loan.Status.APPROVED
    ).count()

    disbursed_count = loans.filter(
        status=Loan.Status.DISBURSED
    ).count()

    completed_count = loans.filter(
        status=Loan.Status.COMPLETED
    ).count()

    return render(
        request,
        "chamas/treasurer_loans.html",
        {
            "chama": chama,
            "loans": loans,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "disbursed_count": disbursed_count,
            "completed_count": completed_count,
        },
    )


@login_required
def review_loan(request, loan_id):
    chama = Chama.objects.first()

    if not chama:
        messages.error(
            request,
            "No Chama has been created yet.",
        )
        return redirect("dashboard")

    if not is_committee_member(request.user, chama):
        messages.error(
            request,
            "Only Chama committee members can review loans.",
        )
        return redirect("dashboard")

    loan = get_object_or_404(
        Loan.objects.select_related(
            "member",
            "member__profile",
        ),
        id=loan_id,
        chama=chama,
    )

    # Nobody can review their own loan.
    is_own_loan = loan.member_id == request.user.id

    if is_own_loan:
        messages.error(
            request,
            "You cannot review or approve your own loan application.",
        )
        return redirect("treasurer_loans")

    savings_total = (
        Saving.objects
        .filter(
            chama=chama,
            member=loan.member,
        )
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    maximum_loan = savings_total * Decimal("2")

    if request.method == "POST":

        decision = request.POST.get("decision")

        approved_amount = request.POST.get(
            "amount_approved",
            "",
        ).strip()

        interest_rate = request.POST.get(
            "interest_rate",
            "0",
        ).strip()

        review_notes = request.POST.get(
            "review_notes",
            "",
        ).strip()

        if loan.status != Loan.Status.PENDING:
            messages.error(
                request,
                "This loan has already been reviewed.",
            )
            return redirect(
                "review_loan",
                loan_id=loan.id,
            )

        if decision == "DECLINE":

            if not review_notes:
                messages.error(
                    request,
                    "Please provide a reason for declining the loan.",
                )

                return render(
                    request,
                    "chamas/review_loan.html",
                    {
                        "chama": chama,
                        "loan": loan,
                        "savings_total": savings_total,
                        "maximum_loan": maximum_loan,
                    },
                )

            loan.status = Loan.Status.DECLINED
            loan.reviewed_by = request.user
            loan.review_notes = review_notes
            loan.approved_at = None
            loan.amount_approved = None
            loan.interest_rate = Decimal("0")

            loan.save(
                update_fields=[
                    "status",
                    "reviewed_by",
                    "review_notes",
                    "approved_at",
                    "amount_approved",
                    "interest_rate",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                f"Loan application from {loan.member.username} has been declined.",
            )

            return redirect("treasurer_loans")

        if decision == "APPROVE":

            if not approved_amount:
                messages.error(
                    request,
                    "Please enter the approved loan amount.",
                )

                return render(
                    request,
                    "chamas/review_loan.html",
                    {
                        "chama": chama,
                        "loan": loan,
                        "savings_total": savings_total,
                        "maximum_loan": maximum_loan,
                    },
                )

            try:
                approved_value = Decimal(approved_amount)
                interest_value = Decimal(
                    interest_rate or "0"
                )

            except (InvalidOperation, ValueError):
                messages.error(
                    request,
                    "Please enter valid numeric values.",
                )

                return render(
                    request,
                    "chamas/review_loan.html",
                    {
                        "chama": chama,
                        "loan": loan,
                        "savings_total": savings_total,
                        "maximum_loan": maximum_loan,
                    },
                )

            if approved_value <= 0:
                messages.error(
                    request,
                    "Approved amount must be greater than zero.",
                )

                return render(
                    request,
                    "chamas/review_loan.html",
                    {
                        "chama": chama,
                        "loan": loan,
                        "savings_total": savings_total,
                        "maximum_loan": maximum_loan,
                    },
                )

            if approved_value > maximum_loan:
                messages.error(
                    request,
                    f"Approved amount cannot exceed KSh {maximum_loan:,.2f}.",
                )

                return render(
                    request,
                    "chamas/review_loan.html",
                    {
                        "chama": chama,
                        "loan": loan,
                        "savings_total": savings_total,
                        "maximum_loan": maximum_loan,
                    },
                )

            if interest_value < 0 or interest_value > 100:
                messages.error(
                    request,
                    "Interest rate must be between 0% and 100%.",
                )

                return render(
                    request,
                    "chamas/review_loan.html",
                    {
                        "chama": chama,
                        "loan": loan,
                        "savings_total": savings_total,
                        "maximum_loan": maximum_loan,
                    },
                )

            loan.status = Loan.Status.APPROVED
            loan.amount_approved = approved_value
            loan.interest_rate = interest_value
            loan.reviewed_by = request.user
            loan.review_notes = review_notes
            loan.approved_at = timezone.now()

            loan.save(
                update_fields=[
                    "status",
                    "amount_approved",
                    "interest_rate",
                    "reviewed_by",
                    "review_notes",
                    "approved_at",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                f"Loan for {loan.member.username} has been approved.",
            )

            return redirect("treasurer_loans")

        messages.error(
            request,
            "Please choose Approve or Decline.",
        )

    return render(
        request,
        "chamas/review_loan.html",
        {
            "chama": chama,
            "loan": loan,
            "savings_total": savings_total,
            "maximum_loan": maximum_loan,
        },
    )

@login_required
def chairlady_dashboard(request):
    chama = Chama.objects.first()

    if not chama:
        messages.error(
            request,
            "No Chama has been created yet.",
        )
        return redirect("dashboard")

    membership = Membership.objects.filter(
        chama=chama,
        user=request.user,
        role=Membership.Role.CHAIRLADY,
        is_active=True,
    ).first()

    if not membership:
        messages.error(
            request,
            "You are not assigned as the Chairlady of this Chama.",
        )
        return redirect("dashboard")

    member_count = Membership.objects.filter(
        chama=chama,
        is_active=True,
    ).count()

    pending_loans = Loan.objects.filter(
        chama=chama,
        status=Loan.Status.PENDING,
    ).count()

    pending_reviews = LoanApproval.objects.filter(
        loan__chama=chama,
        reviewer=request.user,
        decision=LoanApproval.Decision.PENDING,
        loan__status=Loan.Status.PENDING,
    ).count()

    total_savings = (
        Saving.objects
        .filter(chama=chama)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    return render(
        request,
        "chamas/chairlady_dashboard.html",
        {
            "chama": chama,
            "membership": membership,
            "member_count": member_count,
            "pending_loans": pending_loans,
            "pending_reviews": pending_reviews,
            "total_savings": total_savings,
        },
    )


@login_required
def secretary_dashboard(request):
    chama = Chama.objects.first()

    if not chama:
        messages.error(
            request,
            "No Chama has been created yet.",
        )
        return redirect("dashboard")

    membership = Membership.objects.filter(
        chama=chama,
        user=request.user,
        role=Membership.Role.SECRETARY,
        is_active=True,
    ).first()

    if not membership:
        messages.error(
            request,
            "You are not assigned as the Secretary of this Chama.",
        )
        return redirect("dashboard")

    member_count = Membership.objects.filter(
        chama=chama,
        is_active=True,
    ).count()

    pending_loans = Loan.objects.filter(
        chama=chama,
        status=Loan.Status.PENDING,
    ).count()

    pending_reviews = LoanApproval.objects.filter(
        loan__chama=chama,
        reviewer=request.user,
        decision=LoanApproval.Decision.PENDING,
        loan__status=Loan.Status.PENDING,
    ).count()

    recent_savings = (
        Saving.objects
        .filter(chama=chama)
        .select_related("member", "recorded_by")
        .order_by("-date", "-created_at")[:8]
    )

    return render(
        request,
        "chamas/secretary_dashboard.html",
        {
            "chama": chama,
            "membership": membership,
            "member_count": member_count,
            "pending_loans": pending_loans,
            "pending_reviews": pending_reviews,
            "recent_savings": recent_savings,
        },
    )

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.utils import timezone

from chamas.models import Membership

from .models import UserProfile


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")
        phone_number = request.POST.get("phone_number", "").strip()

        if not username or not email or not password:
            messages.error(
                request,
                "Please complete all required fields.",
            )
            return render(
                request,
                "accounts/register.html",
            )

        if password != password_confirm:
            messages.error(
                request,
                "Passwords do not match.",
            )
            return render(
                request,
                "accounts/register.html",
            )

        if User.objects.filter(username=username).exists():
            messages.error(
                request,
                "That username is already in use.",
            )
            return render(
                request,
                "accounts/register.html",
            )

        if User.objects.filter(email=email).exists():
            messages.error(
                request,
                "That email address is already registered.",
            )
            return render(
                request,
                "accounts/register.html",
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        now = timezone.now()

        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.MEMBER,
            phone_number=phone_number,
            trial_started_at=now,
            trial_expires_at=now + timedelta(days=14),
            access_active=True,
        )

        login(request, user)

        messages.success(
            request,
            "Welcome to ChamaPlus! Your 14-day free trial has started.",
        )

        return redirect("subscription")

    return render(
        request,
        "accounts/register.html",
    )


def user_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        messages.error(
            request,
            "Invalid username or password.",
        )

    return render(
        request,
        "accounts/login.html",
    )


@login_required
def user_logout(request):
    logout(request)

    return redirect("login")


@login_required
def profile(request):
    chama_membership = (
        Membership.objects
        .filter(
            user=request.user,
            is_active=True,
        )
        .select_related("chama")
        .first()
    )

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": request.user.profile,
            "chama_membership": chama_membership,
        },
    )

@login_required
def edit_profile(request):
    user = request.user
    profile = user.profile

    chama_membership = (
        Membership.objects
        .filter(
            user=user,
            is_active=True,
            chama__is_active=True,
        )
        .select_related("chama")
        .first()
    )

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()

        if not email:
            messages.error(request, "Email address is required.")
            return render(
                request,
                "accounts/edit_profile.html",
                {
                    "profile": profile,
                    "chama_membership": chama_membership,
                },
            )

        if (
            User.objects
            .filter(email=email)
            .exclude(pk=user.pk)
            .exists()
        ):
            messages.error(
                request,
                "That email address is already registered.",
            )
            return render(
                request,
                "accounts/edit_profile.html",
                {
                    "profile": profile,
                    "chama_membership": chama_membership,
                },
            )

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        profile.phone_number = phone_number
        profile.save()

        messages.success(
            request,
            "Your account has been updated successfully.",
        )

        return redirect("profile")

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "profile": profile,
            "chama_membership": chama_membership,
        },
    )

@login_required
def subscription(request):
    profile = request.user.profile

    return render(
        request,
        "accounts/subscription.html",
        {
            "profile": profile,
        },
    )


@login_required
def dashboard(request):
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

    if (
        membership
        and membership.role == Membership.Role.TREASURER
    ):
        from chamas.views import treasurer_dashboard

        return treasurer_dashboard(request)

    return render(
        request,
        "dashboard.html",
    )


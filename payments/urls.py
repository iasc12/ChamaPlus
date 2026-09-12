from django.urls import path

from . import views


urlpatterns = [
    path("", views.payment, name="payment"),

    path(
        "approvals/",
        views.payment_approvals,
        name="payment_approvals",
    ),

    path(
        "approvals/<int:payment_id>/approve/",
        views.approve_payment,
        name="approve_payment",
    ),

    path(
        "approvals/<int:payment_id>/deny/",
        views.deny_payment,
        name="deny_payment",
    ),
]

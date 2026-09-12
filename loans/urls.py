from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.loan_dashboard,
        name="loans",
    ),
    path(
        "apply/",
        views.apply_for_loan,
        name="apply_for_loan",
    ),
    path(
        "review/",
        views.review_loans,
        name="review_loans",
    ),
    path(
        "review/<int:loan_id>/",
        views.review_loan,
        name="review_loan",
    ),
]

from django.urls import path

from . import views

urlpatterns = [
    path("", views.savings_dashboard, name="savings"),
    path("record/", views.record_saving, name="record_saving"),

    path(
        "withdraw/",
        views.request_withdrawal,
        name="request_withdrawal",
    ),
    path(
        "withdrawals/",
        views.withdrawal_history,
        name="withdrawal_history",
    ),
    path(
        "withdrawals/manage/",
        views.manage_withdrawals,
        name="manage_withdrawals",
    ),
    path(
        "withdrawals/<int:withdrawal_id>/approve/",
        views.approve_withdrawal,
        name="approve_withdrawal",
    ),
    path(
        "withdrawals/<int:withdrawal_id>/reject/",
        views.reject_withdrawal,
        name="reject_withdrawal",
    ),
]

from django.urls import path

from . import views


urlpatterns = [
    path(
        "management/",
        views.chama_management,
        name="chama_management",
    ),
    path(
        "management/treasurer/create/",
        views.create_treasurer,
        name="create_treasurer",
    ),
    path(
        "chairlady/",
        views.chairlady_dashboard,
        name="chairlady_dashboard",
    ),
    path(
        "secretary/",
        views.secretary_dashboard,
        name="secretary_dashboard",
    ),
    path(
        "treasurer/",
        views.treasurer_dashboard,
        name="treasurer_dashboard",
    ),
    path(
        "treasurer/members/",
        views.chama_members,
        name="chama_members",
    ),
    path(
        "treasurer/loans/",
        views.treasurer_loans,
        name="treasurer_loans",
    ),
]

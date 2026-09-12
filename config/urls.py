from django.contrib import admin
from django.urls import include, path

from accounts.views import dashboard


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("accounts/", include("accounts.urls")),
    path("payment/", include("payments.urls")),
    path("savings/", include("savings.urls")),
    path("chama/", include("chamas.urls")),
    path("loans/", include("loans.urls")),
]

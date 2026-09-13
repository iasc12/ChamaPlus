from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def service_worker(request):
    path = Path(settings.BASE_DIR) / "static" / "pwa" / "service-worker.js"

    return HttpResponse(
        path.read_text(encoding="utf-8"),
        content_type="application/javascript",
    )

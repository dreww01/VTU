import logging
from datetime import UTC, datetime

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse
from django.urls import include, path

logger = logging.getLogger(__name__)


def health_check(request: HttpRequest) -> JsonResponse:
    """
    Dedicated, lightweight system health check endpoint to monitor database connectivity
    and service availability.
    """
    db_status = "connected"
    overall_status = "ok"
    status_code = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError as exc:
        logger.error("Health check failed due to database error: %s", exc)
        db_status = "disconnected"
        overall_status = "error"
        status_code = 503
    except Exception as exc:
        logger.error("Health check failed due to unexpected error: %s", exc)
        db_status = "error"
        overall_status = "error"
        status_code = 503

    payload = {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "database": db_status,
    }
    return JsonResponse(payload, status=status_code)


urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("api/health/", health_check, name="api_health_check"),
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("wallet/", include("wallet.urls")),
    path("transactions/", include("transactions.urls")),
]

# Serve media files (in production, use a proper file server like nginx or S3)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files when DEBUG=False (for staging/testing)
if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

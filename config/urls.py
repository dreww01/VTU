from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    """Health check endpoint for Docker/load balancer health checks."""
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path("health/", health_check, name="health_check"),
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

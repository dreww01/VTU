# transactions/providers/__init__.py

from django.conf import settings

from .vtpass import VTPassClient

# Singleton VTPassClient instance for connection reuse
_vtpass_client: VTPassClient | None = None


def get_vtpass_client() -> VTPassClient:
    """
    Get or create a singleton VTPassClient instance.

    Using a singleton ensures the httpx connection pool is shared
    across all requests, reducing connection overhead.
    """
    global _vtpass_client

    if _vtpass_client is not None:
        return _vtpass_client

    base_url = getattr(settings, "VTPASS_BASE_URL", "https://sandbox.vtpass.com/api").rstrip("/")
    api_key = getattr(settings, "VTPASS_API_KEY", None)
    secret_key = getattr(settings, "VTPASS_SECRET_KEY", None)

    if not api_key or not secret_key:
        raise RuntimeError("VTPASS_API_KEY and VTPASS_SECRET_KEY must be set in settings.py")

    _vtpass_client = VTPassClient(
        base_url=base_url,
        api_key=api_key,
        secret_key=secret_key,
    )

    return _vtpass_client

# transactions/providers/__init__.py

from django.conf import settings

from .vtpass import VTPassClient


def get_vtpass_client() -> VTPassClient:

    base_url = getattr(settings, "VTPASS_BASE_URL", "https://sandbox.vtpass.com/api").rstrip("/")
    api_key = getattr(settings, "VTPASS_API_KEY", None)
    secret_key = getattr(settings, "VTPASS_SECRET_KEY", None)

    if not api_key or not secret_key:
        raise RuntimeError("VTPASS_API_KEY and VTPASS_SECRET_KEY must be set in settings.py")

    return VTPassClient(
        base_url=base_url,
        api_key=api_key,
        secret_key=secret_key,
    )

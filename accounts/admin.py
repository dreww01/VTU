from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Controls how UserProfile appears in the Django admin.
    """
    # ONLY use fields that actually exist on UserProfile
    list_display = ("user", "full_name", "phone_number", "created_at")

    # Again, only filter by real fields
    list_filter = ("created_at",)

    search_fields = ("user__username", "user__email", "full_name", "phone_number")

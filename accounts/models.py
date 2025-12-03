from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .validators import validate_avatar_size


class UserProfile(models.Model):
    """
    Stores extra information about a user that doesn't belong directly on the
    core User model (AUTH_USER_MODEL).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,     # supports custom user models
        on_delete=models.CASCADE,     # delete profile if user is deleted
        related_name="profile",       # access via user.profile
    )

    # NEW: store first & last name (to tally with auth.User)
    first_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="First name (kept in sync with the User table where possible).",
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Last name (kept in sync with the User table where possible).",
    )

    # Display full name in UI (auto-built from first + last)
    full_name = models.CharField(
        max_length=300,
        blank=True,
        help_text="Full name for display on the dashboard.",
    )

    # Existing phone number field
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Optional phone number for contact or account recovery.",
    )

    # Avatar image for profile picture
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        help_text="Optional profile picture for this account.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this profile was first created.",
    )

    # Future fields (you can uncomment later):
    # is_verified = models.BooleanField(default=False)
    # bvn = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        """
        Human-readable representation, used in Django admin & shell.
        """
        return self.full_name or self.get_username_display()

    def get_username_display(self):
        """
        Safely get a display name for the related user.
        Works whether your user model has 'username', 'email', or something else.
        """
        try:
            return getattr(self.user, "username", str(self.user))
        except Exception:
            return str(self.user)

    def sync_from_user(self):
        """
        Helper to copy name data from the linked User object into the profile.
        """
        u = self.user
        self.first_name = getattr(u, "first_name", "") or ""
        self.last_name = getattr(u, "last_name", "") or ""
        # Build full_name from first + last
        full = f"{self.first_name} {self.last_name}".strip()
        if full:
            self.full_name = full

    def save(self, *args, **kwargs):
        """
        Ensure full_name is always consistent with first_name + last_name.
        """
        # If full_name wasn't manually set, rebuild from first/last
        if (self.first_name or self.last_name) and not self.full_name:
            self.full_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)

    # NEW: upload avatar + size validation
    avatar = models.ImageField(
    upload_to="avatars/",
    blank=True,
    null=True,
    validators=[validate_avatar_size],   # ✓ file-size validation
    help_text="Max size: 2MB",
)



@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal that runs every time a User is saved.

    - Ensure a profile exists for this user.
    - Sync first_name, last_name, and full_name from the User model.
    """
    profile, _ = UserProfile.objects.get_or_create(user=instance)
    profile.sync_from_user()
    profile.save()


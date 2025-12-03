from django.core.exceptions import ValidationError

def validate_avatar_size(value):
    max_size_mb = 2  # Best practice: 2MB
    limit = max_size_mb * 1024 * 1024  # convert to bytes

    if value.size > limit:
        raise ValidationError(f"Avatar file too large. Max size is {max_size_mb}MB.")

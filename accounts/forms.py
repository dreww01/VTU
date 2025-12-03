from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import UserProfile
import re


class RegisterForm(forms.ModelForm):
    first_name = forms.CharField(
        required=True,
        label="First Name"
    )

    last_name = forms.CharField(
        required=True,
        label="Last Name"
    )

    email = forms.EmailField(
        required=True,
        label="Email Address",
        help_text="Required. Must be unique."
    )

    # ✅ Nigerian phone number (extra form field, stored in UserProfile)
    phone_number = forms.CharField(
        required=True,
        label="Phone Number",
        help_text="Nigerian number only (e.g. 08031234567 or +2348031234567).",
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. 0803 123 4567"
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        help_text="Minimum 8 characters with strong password rules."
    )

    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
        ]  # phone_number & password_confirm are extra form fields, not User fields

    def clean_username(self):
        username = self.cleaned_data.get("username")

        if not username:
            raise ValidationError("Username is required.")

        # Normalize to lowercase (industry standard)
        username = username.lower()

        # Save normalized version back so the form uses it
        self.cleaned_data["username"] = username

        # Validate format: must start with letter, then letters/numbers/underscore (3–20 chars)
        if not re.match(r"^[a-z][a-z0-9_]{2,19}$", username):
            raise ValidationError(
                "Enter a valid username."
            )

        # Ensure uniqueness (case insensitive)
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")

        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean_phone_number(self):
        """
        Accepts:
        - 11-digit Nigerian numbers starting with 0 (e.g. 08031234567)
        - +234 and 234 formats (e.g. +2348031234567, 2348031234567)
        Normalizes to 11-digit 0XXXXXXXXXX format for storage.
        """
        raw = self.cleaned_data.get("phone_number", "").strip()

        # Remove spaces, dashes, etc.
        digits = re.sub(r"\D", "", raw)

        national = None

        if digits.startswith("0") and len(digits) == 11:
            # Already in 0XXXXXXXXXX format
            national = digits
        elif digits.startswith("234") and len(digits) == 13:
            # 2348031234567 -> 08031234567
            national = "0" + digits[3:]
        else:
            raise ValidationError(
                "Enter a valid Nigerian number (e.g. 08031234567 or +2348031234567)."
            )

        # Enforce 2nd digit is 7, 8, or 9 (Nigerian mobile ranges)
        if national[1] not in ["7", "8", "9"]:
            raise ValidationError("Only Nigerian mobile numbers are allowed.")

        return national  # we store normalized national format

    def clean_password(self):
        password = self.cleaned_data.get("password")

        if not password:
            raise ValidationError("Password is required.")

        try:
            validate_password(password)
        except ValidationError as e:
            raise ValidationError(e.messages)

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        """
        Save user + hash password + save name + save email,
        then sync into UserProfile (name + phone).
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

            # Sync into UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.first_name = user.first_name
            profile.last_name = user.last_name
            profile.phone_number = self.cleaned_data.get("phone_number")
            # full_name will be built in profile.save() (from your model logic)
            profile.save()

        return user


class ProfileForm(forms.ModelForm):
    """
    Form for updating the UserProfile.
    Fields must match real model fields exactly.
    """
    class Meta:
        model = UserProfile
        fields = ["first_name", "last_name", "phone_number", "avatar"]

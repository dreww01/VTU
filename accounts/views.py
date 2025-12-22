# # Import necessary modules for authentication and authorization
# # - render: renders an HTML page based on a template
# # - redirect: redirects to another page
# # - authenticate: checks if a username and password combination is valid
# # - login: logs a user in
# # - logout: logs a user out
# # - login_required: a decorator that checks if a user is logged in
# # - LoginRequiredMixin: a mixin class that checks if a user is logged in
# # - View: a base class for views
# # - User: a model for users


# Import necessary modules for authentication and authorization
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib.auth.models import User
from .forms import RegisterForm
from django.contrib.auth.forms import AuthenticationForm

# for password reset
import secrets
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings

# PASSWORD RESET CONFIRM
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import get_user_model
import logging

from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm

from .models import UserProfile

# FORMS
from .forms import RegisterForm, ProfileForm

# from wallet app
from wallet.models import Wallet

from decimal import Decimal, InvalidOperation

# Rate limiting
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited




# Configure logging
logger = logging.getLogger(__name__)

# Registration view
@ratelimit(key='ip', rate=settings.RATELIMIT_REGISTER, method='POST', block=False)
def register_view(request):
    """
    Handles user registration using RegisterForm.
    - Secure user registration flow.
    - Password hashed, confirmed, and stored.
    - Rate limited to prevent abuse.
    """
    # Check if rate limited
    if getattr(request, 'limited', False):
        logger.warning(f"Rate limit exceeded for registration from IP: {request.META.get('REMOTE_ADDR')}")
        messages.error(request, "Too many registration attempts. Please wait a minute before trying again.")
        return render(request, 'accounts/register.html', {'form': RegisterForm()})

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "You have successfully registered and logged in.")
            logger.info(f"New user registered: {user.username}")
            return redirect('dashboard')
        else:
            messages.error(request, "Registration failed. Please check the form.")
            logger.error(f"Registration failed: {form.errors}")
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

# Logout view
@login_required
def logout_view(request):
    """
    Handles user logout.
    - POST: Logs the user out and redirects to login page
    """
    if request.method == 'POST':
        username = request.user.username
        logout(request)
        messages.success(request, f"Goodbye {username}! You have been successfully logged out.")
        logger.info(f"User logged out: {username}")
        return redirect('login')
    
    # If GET request, redirect to dashboard
    return redirect('dashboard')


# Login view
@ratelimit(key='ip', rate=settings.RATELIMIT_LOGIN, method='POST', block=False)
def login_view(request):
    """
    Handles user login.
    - Authenticates the user with proper validation and logging.
    - Rate limited to prevent brute force attacks.
    """
    # Check if rate limited
    if getattr(request, 'limited', False):
        logger.warning(f"Rate limit exceeded for login from IP: {request.META.get('REMOTE_ADDR')}")
        messages.error(request, "Too many login attempts. Please wait a minute before trying again.")
        return render(request, 'accounts/login.html', {'form': AuthenticationForm()})

    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Clear all messages if user just logged out
    if request.session.get('just_logged_out'):
        storage = messages.get_messages(request)
        list(storage)  # This consumes/clears all messages
        del request.session['just_logged_out']  # Remove the flag
    
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "You are now logged in.")
            logger.info(f"User logged in: {user.username}")
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            messages.error(request, "Invalid credentials. Please try again.")
            logger.warning(f"Login failed for user: {request.POST.get('username')}")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})



# Set up logger
logger = logging.getLogger(__name__)

MAX_FUND_LIMIT = Decimal('100000.00')  # Limit set to 100,000 Naira

@login_required
def dashboard_view(request):
    balance = Decimal('0.00')  # Default value in case of failure
    transactions = []  # Default value if no transactions are found

    try:
        # Use select_related to avoid extra query for user
        wallet = Wallet.objects.select_related('user').get(user=request.user)

        # Ensure the wallet balance is valid (strict validation)
        if wallet.balance is None or not isinstance(wallet.balance, (int, float, Decimal)):
            # Log error if balance is not a valid type or is None
            logger.error(f"Invalid or None balance for user {request.user.username}, resetting to ₦0.00")
            wallet.balance = Decimal('0.00')  # Reset to default value in case of invalid balance
            wallet.save()  # Save the reset balance in the database

        # Safely convert to Decimal and check for InvalidOperation
        try:
            balance = Decimal(wallet.balance)
        except InvalidOperation:
            logger.error(f"Invalid balance value for user {request.user.username}: {wallet.balance}")
            balance = Decimal('0.00')  # Fallback to 0 if invalid value

        # Fetch the latest transactions (latest 5) with only needed fields
        transactions = wallet.transaction_set.only(
            'id', 'reference', 'transaction_type', 'amount', 'status', 'timestamp', 'description'
        ).order_by('-timestamp')[:5]

    except Wallet.DoesNotExist:
        # Handle case where the wallet does not exist (should not happen since wallet is created on signup)
        logger.error(f"Wallet does not exist for user {request.user.username}")

    # Pass both balance and transactions in a single context dictionary
    return render(request, 'accounts/dashboard.html', {
        'wallet_balance': balance,
        'recent_transactions': transactions,
    })





# Password reset view (step 1: send reset code to email)
@ratelimit(key='ip', rate=settings.RATELIMIT_PASSWORD_RESET, method='POST', block=False)
def send_reset_code(request):
    """
    Sends a password reset code to the user's email address.
    - Validates the email address and sends a secure 6-digit reset code.
    - Rate limited to prevent email enumeration and abuse.
    """
    # Check if rate limited
    if getattr(request, 'limited', False):
        logger.warning(f"Rate limit exceeded for password reset from IP: {request.META.get('REMOTE_ADDR')}")
        messages.error(request, "Too many password reset requests. Please wait a minute before trying again.")
        return render(request, 'accounts/password_reset.html')

    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
            logger.warning(f"Password reset attempted for non-existent email: {email}")
            return redirect('password_reset')

        # Generate a secure 6-digit code
        reset_code = secrets.randbelow(1000000)
        reset_code = str(reset_code).zfill(6)

        # Save the reset code in the session
        request.session['reset_code'] = reset_code
        request.session['reset_email'] = email

        # Send the reset code via email
        subject = "Your Password Reset Code"
        message = f"Your password reset code is: {reset_code}"
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            messages.success(request, 'A 6-digit reset code has been sent to your email.')
            logger.info(f"Password reset code sent to: {email}")
        except Exception as e:
            messages.error(request, 'Failed to send reset code. Please try again.')
            logger.error(f"Failed to send reset code to {email}: {str(e)}")
            return redirect('password_reset')

        return redirect('password_reset_confirm')

    return render(request, 'accounts/password_reset.html')


# Password reset view

def password_reset_confirm(request):
    """
    Step 2 of password reset:
    - First POST with 'reset_code' -> verify 6-digit code
    - Then POST without 'reset_code' (from set_new_password form) -> save new password
    """
    email = request.session.get('reset_email')
    stored_code = request.session.get('reset_code')

    # No active reset session
    if not email or not stored_code:
        messages.error(request, 'Invalid or expired reset session. Please start over.')
        logger.warning("Password reset accessed without valid session")
        return redirect('password_reset')

    # POST: either verifying code OR setting new password
    if request.method == 'POST':

        # ── PHASE 1: VERIFY CODE ────────────────────────────────
        if 'reset_code' in request.POST:
            entered_code = (request.POST.get('reset_code') or "").strip()

            # Basic format check: must be exactly 6 digits
            if not entered_code.isdigit() or len(entered_code) != 6:
                logger.warning(
                    f"Invalid reset code format for email {email}: {entered_code}"
                )
                return render(
                    request,
                    "accounts/password_reset_confirm.html",
                    {"reset_code_error": "Enter the 6-digit code we sent to your email."},
                )

            # Check against stored code
            if entered_code != stored_code:
                logger.warning(f"Incorrect reset code entered for email: {email}")
                return render(
                    request,
                    "accounts/password_reset_confirm.html",
                    {"reset_code_error": "The reset code is incorrect. Please try again."},
                )

            # Code is correct → mark verified and show password form
            request.session["code_verified"] = True
            logger.info(f"Reset code verified for email: {email}")

            try:
                user = get_user_model().objects.get(email=email)
            except get_user_model().DoesNotExist:
                messages.error(request, "User not found. Please try again.")
                logger.error(f"User not found for email: {email}")
                for key in ("reset_code", "reset_email", "code_verified"):
                    request.session.pop(key, None)
                return redirect("password_reset")

            form = SetPasswordForm(user=user)
            return render(request, "accounts/set_new_password.html", {"form": form})

        # ── PHASE 2: SET NEW PASSWORD ───────────────────────────
        else:
            # Must have verified code first
            if not request.session.get("code_verified"):
                messages.error(request, "Please verify your reset code first.")
                logger.warning(
                    f"Password set attempted without code verification for: {email}"
                )
                return redirect("password_reset_confirm")

            try:
                user = get_user_model().objects.get(email=email)
            except get_user_model().DoesNotExist:
                messages.error(request, "User not found. Please try again.")
                logger.error(f"User not found for email: {email}")
                for key in ("reset_code", "reset_email", "code_verified"):
                    request.session.pop(key, None)
                return redirect("password_reset")

            form = SetPasswordForm(user=user, data=request.POST)
            if form.is_valid():
                form.save()

                # Clear session after success
                for key in ("reset_code", "reset_email", "code_verified"):
                    request.session.pop(key, None)

                messages.success(
                    request, "Your password has been successfully reset! Please log in."
                )
                logger.info(f"Password successfully reset for user: {user.username}")
                return redirect("login")

            # Form has errors (password rules / mismatch)
            logger.error(f"Password reset form errors for {email}: {form.errors}")
            messages.error(request, "Please correct the errors below.")
            return render(request, "accounts/set_new_password.html", {"form": form})

    # GET: show the code verification form
    return render(request, "accounts/password_reset_confirm.html")



@login_required
def profile_view(request):
    """
    Show and update the logged-in user's profile.
    - GET  -> display the form with existing profile data
    - POST -> validate and save the form, then show success message
    """
    # Ensure the user has a profile (signal SHOULD already create it, but this is a safe guard)
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Bind submitted data + files (for avatar upload) to the form
        form = ProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():

            # SYNC UserProfile → User
            request.user.first_name = profile.first_name
            request.user.last_name  = profile.last_name
            request.user.save()

            form.save()
            # This will be picked up by your layout and also trigger the popup modal
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
        else:
            # Form has errors; we re-render the template with error messages
            messages.error(request, "Please correct the errors below.")
    else:
        # Initial GET – show the form with current profile data
        form = ProfileForm(instance=profile)

    context = {
        "form": form,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def vtu_services_view(request):
    """
    VTU Services Hub - Shows all available VTU services.
    - Airtime purchase
    - Data bundles
    - Electricity/TV bills
    """
    try:
        wallet = Wallet.objects.get(user=request.user)
        balance = Decimal(wallet.balance)
    except Wallet.DoesNotExist:
        logger.error(f"Wallet does not exist for user {request.user.username}")
        balance = Decimal('0.00')

    return render(request, 'accounts/vtu_services.html', {
        'wallet_balance': balance,
    })

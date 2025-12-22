from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from transactions.models import Transaction


class FraudCheckError(Exception):
    """Raised when transaction fails fraud checks"""

    pass


def is_user_verified(user):
    """
    Check if user has completed KYC verification.
    For now, returns False (all users are unverified).
    Later: check user.profile.kyc_verified or similar.
    """
    # TODO: When I add KYC, replace this with:
    # return hasattr(user, 'profile') and user.profile.kyc_verified
    return False


def get_transaction_limits(user):
    """
    Get transaction limits based on user verification status.
    Returns dict with: single_limit, daily_limit, hourly_count
    """
    is_verified = is_user_verified(user)

    if is_verified:
        # Verified users - higher limits
        return {
            "single_limit": Decimal(getattr(settings, "VERIFIED_SINGLE_LIMIT", 50000)),
            "daily_limit": Decimal(getattr(settings, "VERIFIED_DAILY_LIMIT", 200000)),
            "hourly_count": getattr(settings, "VERIFIED_HOURLY_COUNT", 20),
        }
    else:
        # Unverified users - lower limits
        return {
            "single_limit": Decimal(getattr(settings, "UNVERIFIED_SINGLE_LIMIT", 5000)),
            "daily_limit": Decimal(getattr(settings, "UNVERIFIED_DAILY_LIMIT", 20000)),
            "hourly_count": getattr(settings, "UNVERIFIED_HOURLY_COUNT", 5),
        }


def check_transaction_limits(user, amount):
    """
    Check if user is within transaction limits.
    Raises FraudCheckError if limits exceeded.
    """
    limits = get_transaction_limits(user)

    # Check 1: Single transaction limit
    if amount > limits["single_limit"]:
        if is_user_verified(user):
            raise FraudCheckError(
                f"Transaction amount exceeds single transaction limit of NGN {limits['single_limit']:,.2f}"
            )
        else:
            raise FraudCheckError(
                f"Unverified users can only transact up to NGN {limits['single_limit']:,.2f} per transaction. "
                f"Complete KYC verification for higher limits."
            )

    # Check 2: Daily transaction limit
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_total = Transaction.objects.filter(
        wallet__user=user,
        transaction_type="purchase",
        status="completed",
        timestamp__gte=today_start,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    if today_total + amount > limits["daily_limit"]:
        remaining = limits["daily_limit"] - today_total
        if is_user_verified(user):
            raise FraudCheckError(
                f"Daily transaction limit of NGN {limits['daily_limit']:,.2f} exceeded. "
                f"You have NGN {remaining:,.2f} remaining today."
            )
        else:
            raise FraudCheckError(
                f"Daily limit of NGN {limits['daily_limit']:,.2f} exceeded. "
                f"You have NGN {remaining:,.2f} remaining. "
                f"Complete KYC verification for higher limits."
            )

    # Check 3: Hourly transaction count (prevent rapid-fire)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    hourly_count = Transaction.objects.filter(
        wallet__user=user, transaction_type="purchase", timestamp__gte=one_hour_ago
    ).count()

    if hourly_count >= limits["hourly_count"]:
        raise FraudCheckError(
            f"Too many transactions in the last hour ({hourly_count}/{limits['hourly_count']}). "
            f"Please wait before trying again."
        )

    return True


def check_suspicious_activity(user):
    """
    Check for suspicious patterns that might indicate fraud.
    """
    # Check 1: Too many failed transactions in 24 hours
    last_24h = timezone.now() - timedelta(hours=24)
    failed_count = Transaction.objects.filter(
        wallet__user=user, status="failed", timestamp__gte=last_24h
    ).count()

    if failed_count > 5:
        raise FraudCheckError(
            "Too many failed transactions in the last 24 hours. "
            "Please contact support if you need assistance."
        )

    # Check 2: Account age (prevent new account abuse)
    account_age = timezone.now() - user.date_joined
    if account_age < timedelta(minutes=5):
        # Account created less than 5 minutes ago
        limits = get_transaction_limits(user)
        if limits["single_limit"] > Decimal("1000"):
            raise FraudCheckError(
                "New accounts have temporary transaction limits. "
                "Please wait a few minutes before making large transactions."
            )

    return True


def run_fraud_checks(user, amount):
    """
    Run all fraud checks before processing transaction.
    Raises FraudCheckError if any check fails.
    Returns True if all checks pass.

    Can be disabled via admin panel for testing.
    """
    # Check if fraud checks are enabled
    from transactions.models import AppSettings

    settings = AppSettings.get_settings()

    # Always check maintenance mode (even if fraud checks are off)
    check_maintenance_mode()

    if not settings.fraud_checks_enabled:
        # Fraud checks disabled - skip all other checks
        return True

    # Run all fraud checks
    check_transaction_limits(user, amount)
    check_suspicious_activity(user)
    return True


def get_user_limits_info(user):
    """
    Get formatted information about user's current limits.
    Useful for displaying to users.
    """
    limits = get_transaction_limits(user)
    is_verified = is_user_verified(user)

    # Calculate used limits today
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_total = Transaction.objects.filter(
        wallet__user=user,
        transaction_type="purchase",
        status="completed",
        timestamp__gte=today_start,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    daily_remaining = limits["daily_limit"] - today_total

    return {
        "is_verified": is_verified,
        "single_limit": limits["single_limit"],
        "daily_limit": limits["daily_limit"],
        "daily_used": today_total,
        "daily_remaining": max(Decimal("0"), daily_remaining),
        "hourly_count_limit": limits["hourly_count"],
    }


def check_maintenance_mode():
    """
    Check if app is in maintenance mode.
    Raises FraudCheckError if maintenance mode is active.
    """
    from transactions.models import AppSettings

    settings = AppSettings.get_settings()

    if settings.maintenance_mode:
        raise FraudCheckError(
            "System is currently under maintenance. "
            "Please try again later. We apologize for the inconvenience."
        )

    return True

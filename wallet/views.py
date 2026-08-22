# wallet/views.py
import hashlib
import hmac
import json
import logging
import os
from decimal import Decimal, InvalidOperation

import httpx
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Rate limiting
from django_ratelimit.decorators import ratelimit

from transactions.models import Transaction
from wallet.models import Wallet

logger = logging.getLogger(__name__)

# Paystack Configuration
MAX_FUND_LIMIT = Decimal("100000.00")  # ₦100,000 max per deposit


def get_paystack_secret_key() -> str:
    """Get Paystack secret key from settings or environment."""
    return getattr(settings, "PAYSTACK_SECRET_KEY", None) or os.environ.get("PAYSTACK_SECRET_KEY", "") or ""


def get_paystack_public_key() -> str:
    """Get Paystack public key from settings or environment."""
    return getattr(settings, "PAYSTACK_PUBLIC_KEY", None) or os.environ.get("PAYSTACK_PUBLIC_KEY", "") or ""


# Shared httpx client for Paystack API calls (connection pooling)
_paystack_client: httpx.Client | None = None


def get_paystack_client() -> httpx.Client:
    """Get or create a shared httpx client for Paystack API calls."""
    global _paystack_client
    secret_key = get_paystack_secret_key()
    if _paystack_client is None or _paystack_client.is_closed:
        _paystack_client = httpx.Client(
            base_url="https://api.paystack.co",
            headers={
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0,
            ),
        )
    return _paystack_client


# ============================================
# WALLET FUNDING (Paystack Integration)
# ============================================


@login_required
def fund_wallet(request):
    """Display wallet funding page with Paystack integration."""
    if request.method == "POST":
        return HttpResponseBadRequest("Use JavaScript to initialize payment")

    context = {
        "paystack_public_key": get_paystack_public_key(),
        "email": request.user.email,
    }
    return render(request, "wallet/fund_wallet.html", context)


@login_required
def verify_payment(request, reference):
    """Verify Paystack payment and credit user wallet."""
    try:
        # Call Paystack API to verify transaction using shared client
        client = get_paystack_client()
        response = client.get(f"/transaction/verify/{reference}")
        data = response.json()

        logger.info(
            "Paystack verification response for ref %s: status=%s", reference, data.get("status")
        )

        # Check if verification was successful
        if data["status"] and data["data"]["status"] == "success":
            amount = Decimal(data["data"]["amount"]) / 100  # Convert kobo to naira
            logger.info(
                "Payment verified: ref=%s, amount=N%s, user=%s",
                reference,
                amount,
                request.user.username,
            )

            # Validate amount
            if amount > MAX_FUND_LIMIT:
                messages.error(request, f"Amount cannot exceed N{MAX_FUND_LIMIT:,}")
                return redirect("fund_wallet")

            with transaction.atomic():
                # Lock wallet to prevent race conditions
                wallet = Wallet.objects.select_for_update().get(user=request.user)

                # Check if transaction already processed (idempotency)
                if Transaction.objects.filter(reference=reference).exists():
                    logger.info(
                        "Duplicate payment attempt: ref=%s, user=%s",
                        reference,
                        request.user.username,
                    )
                    messages.info(request, "This payment has already been processed")
                    return redirect("wallet_info")

                # Credit wallet
                wallet.deposit(amount=amount, description="Paystack Deposit", reference=reference)

                logger.info(
                    "Wallet credited: user=%s, amount=N%s, new_balance=N%s",
                    request.user.username,
                    amount,
                    wallet.balance,
                )

            messages.success(request, f"Successfully funded wallet with N{amount:,.2f}")
            return redirect("dashboard")

        else:
            logger.warning("Payment verification failed: ref=%s, response=%s", reference, data)
            messages.error(request, "Payment verification failed")
            return redirect("fund_wallet")

    except httpx.ConnectTimeout:
        logger.error(
            "Paystack connection timeout: ref=%s, user=%s", reference, request.user.username
        )
        messages.error(request, "Connection to payment server timed out. Please try again.")
        return redirect("fund_wallet")

    except httpx.ReadTimeout:
        logger.error("Paystack read timeout: ref=%s, user=%s", reference, request.user.username)
        messages.error(request, "Payment server took too long to respond. Please try again.")
        return redirect("fund_wallet")

    except httpx.HTTPError as e:
        logger.error(
            "Paystack network error: ref=%s, user=%s, error=%s",
            reference,
            request.user.username,
            str(e),
        )
        messages.error(request, "Could not verify payment. Please contact support.")
        return redirect("fund_wallet")

    except Wallet.DoesNotExist:
        logger.error("Wallet not found during payment verification: user=%s", request.user.username)
        messages.error(request, "Wallet not found")
        return redirect("fund_wallet")

    except Exception:
        logger.exception(
            "Unexpected error during payment verification: ref=%s, user=%s",
            reference,
            request.user.username,
        )
        messages.error(request, "Error processing payment. Please contact support.")
        return redirect("fund_wallet")


@csrf_exempt
@require_POST
@ratelimit(key="ip", rate=settings.RATELIMIT_WEBHOOK, method="POST", block=True)
def paystack_webhook(request):
    """
    Handle Paystack webhook notifications.
    Rate limited to prevent DDoS attacks.
    """
    secret_key = get_paystack_secret_key()
    if not secret_key:
        logger.error("PAYSTACK_SECRET_KEY is not configured")
        return HttpResponse(status=400)

    signature = request.headers.get("x-paystack-signature")
    if not signature:
        logger.warning("Missing x-paystack-signature header")
        return HttpResponse(status=400)

    payload = request.body
    computed_sig = hmac.new(
        secret_key.encode("utf-8"),
        payload,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature, computed_sig):
        logger.warning(
            "Invalid Paystack webhook signature from IP: %s",
            request.META.get("REMOTE_ADDR"),
        )
        return HttpResponse(status=400)

    # Process event
    try:
        event = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        logger.warning("Invalid JSON payload in Paystack webhook")
        return HttpResponse(status=400)

    if not isinstance(event, dict):
        logger.warning("Invalid payload structure in Paystack webhook")
        return HttpResponse(status=400)

    if event.get("event") == "charge.success":
        data = event.get("data")
        if not isinstance(data, dict):
            logger.warning("Invalid data dictionary in Paystack charge.success webhook")
            return HttpResponse(status=400)

        reference = data.get("reference")
        customer = data.get("customer")
        email = customer.get("email") if isinstance(customer, dict) else None
        amount_in_kobo = data.get("amount")

        if not reference or not email or amount_in_kobo is None:
            logger.warning(
                "Missing required fields in charge.success webhook: ref=%s, email=%s, amount=%s",
                reference,
                email,
                amount_in_kobo,
            )
            return HttpResponse(status=400)

        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning("Customer not found for email: %s", email)
            return HttpResponse("Customer not found", status=404)
        except User.MultipleObjectsReturned:
            logger.error("Multiple user accounts found for email %s; cannot determine recipient wallet for ref %s", email, reference)
            return HttpResponse("Multiple accounts associated with email", status=400)

        try:
            with transaction.atomic():
                try:
                    wallet = Wallet.objects.select_for_update().get(user=user)
                except Wallet.DoesNotExist:
                    logger.error("Wallet not found for user: %s", user.username)
                    return HttpResponse("Wallet not found", status=404)

                # Check if transaction already processed (idempotency)
                if Transaction.objects.filter(reference=reference).exists():
                    logger.info(
                        "Duplicate payment attempt (idempotency notice): ref=%s, user=%s",
                        reference,
                        user.username,
                    )
                    return HttpResponse(status=200)

                # Convert Paystack amount from kobo to naira
                naira_amount = Decimal(str(amount_in_kobo)) / Decimal("100")

                # Credit wallet
                wallet.deposit(
                    amount=naira_amount,
                    description="Paystack Webhook Deposit",
                    reference=reference,
                )

                logger.info(
                    "Wallet credited via webhook: user=%s, amount=N%s, new_balance=N%s, ref=%s",
                    user.username,
                    naira_amount,
                    wallet.balance,
                    reference,
                )
        except (ValueError, InvalidOperation) as e:
            logger.error(
                "Invalid amount or deposit error: ref=%s, user=%s, error=%s",
                reference,
                user.username,
                str(e),
            )
            return HttpResponse(status=400)
        except Exception:
            logger.exception(
                "Unexpected error during webhook wallet credit: ref=%s, user=%s",
                reference,
                user.username,
            )
            return HttpResponse(status=500)

    return HttpResponse(status=200)


# ============================================
# WALLET INFO
# ============================================


@login_required
def wallet_info(request):
    """Display user's wallet balance and recent transactions."""
    wallet = Wallet.objects.select_related("user").get(user=request.user)
    recent_transactions = (
        Transaction.objects.filter(wallet=wallet)
        .only("id", "reference", "transaction_type", "amount", "status", "timestamp", "description")
        .order_by("-timestamp")[:10]
    )  # Last 10 transactions

    return render(
        request,
        "wallet/wallet_info.html",
        {"wallet": wallet, "recent_transactions": recent_transactions},
    )


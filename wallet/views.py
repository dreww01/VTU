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

User = get_user_model()
logger = logging.getLogger(__name__)

# Paystack Configuration
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY")
MAX_FUND_LIMIT = Decimal("100000.00")  # ₦100,000 max per deposit

# Shared httpx client for Paystack API calls (connection pooling)
_paystack_client: httpx.Client | None = None


def get_paystack_client() -> httpx.Client:
    """Get or create a shared httpx client for Paystack API calls."""
    global _paystack_client
    if _paystack_client is None or _paystack_client.is_closed:
        _paystack_client = httpx.Client(
            base_url="https://api.paystack.co",
            headers={
                "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
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
        "paystack_public_key": PAYSTACK_PUBLIC_KEY,
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
    secret_key = (
        getattr(settings, "PAYSTACK_SECRET_KEY", None)
        or os.environ.get("PAYSTACK_SECRET_KEY")
        or PAYSTACK_SECRET_KEY
    )
    if not secret_key:
        logger.error("PAYSTACK_SECRET_KEY is not configured")
        return HttpResponse(status=500)

    signature = request.headers.get("x-paystack-signature")
    if not signature:
        logger.warning(
            f"Missing or empty Paystack webhook signature from IP: {request.META.get('REMOTE_ADDR')}"
        )
        return HttpResponse(status=400)

    secret = secret_key.encode("utf-8")
    payload = request.body

    # Verify webhook signature using constant-time comparison
    computed_sig = hmac.new(secret, payload, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(signature, computed_sig):
        logger.warning(
            f"Invalid Paystack webhook signature from IP: {request.META.get('REMOTE_ADDR')}"
        )
        return HttpResponse(status=400)

    # Process event
    try:
        event = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Invalid JSON payload in Paystack webhook: {e}")
        return HttpResponseBadRequest("Invalid JSON payload")

    if event.get("event") == "charge.success":
        data = event.get("data") or {}
        reference = data.get("reference")
        customer = data.get("customer") or {}
        email = customer.get("email") if isinstance(customer, dict) else None
        amount_in_kobo = data.get("amount")

        if not email or not reference or amount_in_kobo is None:
            logger.error(
                f"Missing required fields in charge.success webhook: email={email}, ref={reference}, amount={amount_in_kobo}"
            )
            return HttpResponseBadRequest("Missing required webhook data")

        logger.info(f"Paystack webhook received: charge.success for ref={reference}, email={email}")

        user = User.objects.filter(email=email).first()
        if not user:
            logger.warning(f"Paystack webhook: User with email '{email}' not found.")
            return HttpResponse("Customer not found", status=404)

        try:
            naira_amount = Decimal(str(amount_in_kobo)) / Decimal(100)
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.error(f"Paystack webhook: Invalid amount '{amount_in_kobo}': {e}")
            return HttpResponseBadRequest("Invalid amount")

        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=user)

                if Transaction.objects.filter(reference=reference).exists():
                    logger.info(
                        f"Duplicate webhook payment attempt (idempotent skip): ref={reference}, user={user.username}"
                    )
                    return HttpResponse(status=200)

                wallet.deposit(
                    amount=naira_amount,
                    description="Paystack Webhook Deposit",
                    reference=reference,
                )
                logger.info(
                    f"Paystack webhook processed: Credited ₦{naira_amount} to {user.username} (ref: {reference})"
                )
        except Wallet.DoesNotExist:
            logger.error(f"Paystack webhook: Wallet not found for user '{user.username}'.")
            return HttpResponse("Wallet not found", status=404)
        except ValueError as e:
            logger.error(f"Paystack webhook: Deposit failed for {user.username}: {e}")
            return HttpResponseBadRequest(str(e))

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

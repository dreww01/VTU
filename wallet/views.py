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
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        logger.warning(
            f"Missing Paystack webhook signature from IP: {request.META.get('REMOTE_ADDR')}"
        )
        return HttpResponse(status=400)

    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", None) or os.environ.get("PAYSTACK_SECRET_KEY") or ""
    if not secret_key:
        logger.error("PAYSTACK_SECRET_KEY is not configured")
        return HttpResponse(status=400)

    payload = request.body
    computed_sig = hmac.new(secret_key.encode("utf-8"), payload, hashlib.sha512).hexdigest()

    # Timing-safe comparison to prevent timing attacks
    if not hmac.compare_digest(signature, computed_sig):
        logger.warning(
            f"Invalid Paystack webhook signature from IP: {request.META.get('REMOTE_ADDR')}"
        )
        return HttpResponse(status=400)

    # Process event
    try:
        event = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Invalid JSON payload received in Paystack webhook")
        return HttpResponse(status=400)

    if event.get("event") == "charge.success":
        event_data = event.get("data", {})
        customer = event_data.get("customer", {}) if isinstance(event_data, dict) else {}
        customer_email = customer.get("email") if isinstance(customer, dict) else None
        reference = event_data.get("reference") if isinstance(event_data, dict) else None
        amount_in_kobo = event_data.get("amount") if isinstance(event_data, dict) else None

        if not reference or not customer_email or amount_in_kobo is None:
            logger.warning(
                "Missing required fields in charge.success webhook payload: ref=%s, email=%s, amount=%s",
                reference,
                customer_email,
                amount_in_kobo,
            )
            return HttpResponse(status=400)

        logger.info("Paystack webhook received: charge.success for ref=%s, email=%s", reference, customer_email)

        user = User.objects.filter(email__iexact=customer_email).first()
        if not user:
            logger.error("User with email %s not found for Paystack webhook ref=%s", customer_email, reference)
            return HttpResponse("User not found", status=404)

        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=user)

                # Check if transaction already processed (idempotency)
                if Transaction.objects.filter(reference=reference).exists():
                    logger.info("Idempotency notice: Transaction with reference %s already processed", reference)
                    return HttpResponse(status=200)

                # Convert Paystack amount from kobo to naira
                naira_amount = Decimal(str(amount_in_kobo)) / Decimal("100")

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
        except Wallet.DoesNotExist:
            logger.error("Wallet not found for user %s during Paystack webhook ref=%s", user.username, reference)
            return HttpResponse("Wallet not found", status=404)
        except (ValueError, InvalidOperation) as e:
            logger.error(
                "Error processing deposit for user %s, ref=%s: %s",
                user.username,
                reference,
                e,
            )
            return HttpResponse(status=400)

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

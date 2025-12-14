# transactions/views.py
from decimal import Decimal, InvalidOperation
import logging
import hashlib
import hmac

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from wallet.models import Wallet
from transactions.models import Transaction
from transactions.services.airtime import (
    purchase_airtime,
    InsufficientBalanceError,
    InvalidNetworkError,
)
from transactions.services.electricity import (
    purchase_electricity,
    DISCO_SERVICE_ID_MAP,
    MeterVerificationError,
)
from transactions.services.fraud_check import FraudCheckError
from transactions.providers.exceptions import VTPassError
from transactions.services.data import purchase_data, DATA_PLANS

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger('transactions')


def send_purchase_email(user, transaction):
    subject = "Nova VTU Purchase Confirmation"
    html_message = render_to_string('emails/purchase_confirmation.html', {'user': user, 'transaction': transaction})
    message = strip_tags(html_message)  # Plain text fallback

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
    )


# ============================================
# VTPASS WEBHOOK (NEW - Added for auto-updates)
# ============================================

def verify_vtpass_signature(payload, signature):
    """
    Verify webhook came from VTPass using HMAC-SHA512.
    Only if you have VTPASS_SECRET_KEY configured.
    """
    if not hasattr(settings, 'VTPASS_SECRET_KEY') or not settings.VTPASS_SECRET_KEY:
        # If no secret key configured, skip verification (not recommended for production)
        return True
    
    secret = settings.VTPASS_SECRET_KEY.encode('utf-8')
    expected_signature = hmac.new(
        secret,
        payload.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


@csrf_exempt
@require_POST
def vtpass_webhook(request):
    """
    VTPass webhook endpoint - receives transaction status updates.
    Give this URL to VTPass: https://yourdomain.com/transactions/webhook/vtpass/
    """
    try:
        # Get signature if VTPass sends it
        signature = request.headers.get('X-VTPass-Signature', '')
        
        # Verify signature (optional - only if you have secret key)
        if signature and not verify_vtpass_signature(request.body.decode('utf-8'), signature):
            logger.warning('Invalid VTPass webhook signature')
            return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=401)
        
        # Parse webhook data (VTPass might send as POST data or JSON)
        import json
        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()
        
        logger.info(f'VTPass webhook received: {data}')
        
        # Get transaction reference
        reference = data.get('request_id') or data.get('requestId') or data.get('reference')
        status = (data.get('status') or '').lower()
        
        if not reference:
            logger.error(f'Webhook missing reference: {data}')
            return JsonResponse({'status': 'error', 'message': 'Missing reference'}, status=400)
        
        # Find transaction
        try:
            tx = Transaction.objects.get(reference=reference)
        except Transaction.DoesNotExist:
            logger.warning(f'Webhook for unknown transaction: {reference}')
            return JsonResponse({'status': 'error', 'message': 'Transaction not found'}, status=404)
        
        # Store old status for logging
        old_status = tx.status
        
        # Update transaction status based on VTPass response
        if status in ['delivered', 'success', 'successful']:
            tx.status = 'completed'
            
            # Extract token for electricity if available
            token = data.get('token') or data.get('purchased_code')
            if token and not tx.token:
                tx.token = str(token).replace("Token :", "").strip()
        
        elif status in ['failed', 'reversed']:
            tx.status = 'failed'
        
        else:
            tx.status = 'pending'
        
        # Save transaction
        tx.save()
        
        logger.info(f'Webhook updated {reference}: {old_status} -> {tx.status}')
        
        # Send email notification if status changed to completed or failed
        if old_status != tx.status and tx.status in ['completed', 'failed']:
            try:
                send_purchase_email(tx.wallet.user, tx)
            except Exception as e:
                logger.error(f'Failed to send email for {reference}: {e}')
        
        return JsonResponse({'status': 'success', 'message': 'Transaction updated'})
    
    except Exception as e:
        logger.error(f'Webhook error: {str(e)}', exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Internal error'}, status=500)


# ============================================
# TRANSACTION HISTORY
# ============================================

@login_required
def transaction_history(request):
    """Display transaction history with filtering and pagination."""

    # Get filter parameter
    transaction_type_filter = request.GET.get("transaction_type", "")

    # Get all user transactions
    transactions_qs = Transaction.objects.filter(wallet__user=request.user)

    # Apply filter if specified
    if transaction_type_filter:
        transactions_qs = transactions_qs.filter(transaction_type=transaction_type_filter)

    # Order by most recent first
    transactions_qs = transactions_qs.order_by("-timestamp")

    # Pagination - 20 transactions per page
    paginator = Paginator(transactions_qs, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "transactions": page_obj,  # Paginated transactions
        "transaction_type_filter": transaction_type_filter,
        "total_count": transactions_qs.count(),  # Total transactions
    }

    return render(request, "transactions/transaction_history.html", context)


# ============================================
# VTU SERVICES (Airtime, Data, Electricity)
# ============================================

@login_required
def buy_airtime(request):
    if request.method == "POST":
        network = (request.POST.get("network") or "").strip()  # mtn, glo, airtel, 9mobile
        phone = (request.POST.get("phone") or "").strip()
        amount_raw = (request.POST.get("amount") or "").strip()

        # Basic form validation
        if not network or not phone or not amount_raw:
            messages.error(request, "All fields are required.")
            return redirect("buy_airtime")

        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, TypeError):
            messages.error(request, "Enter a valid amount.")
            return redirect("buy_airtime")

        if amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("buy_airtime")

        try:
            # Core business logic (creates Transaction + calls VTPass)
            tx, vtpass_resp = purchase_airtime(
                user=request.user,
                network=network,
                phone=phone,
                amount=amount,
            )

        except InsufficientBalanceError:
            messages.error(request, "Insufficient wallet balance.")
            return redirect("buy_airtime")

        except InvalidNetworkError as e:
            messages.error(request, str(e))
            return redirect("buy_airtime")
        
        except FraudCheckError as e:
            messages.error(request, str(e))
            return redirect("buy_airtime")

        except VTPassError as e:
            messages.error(request, f"VTU provider error: {e}")
            return redirect("buy_airtime")

        except Exception as e:
            messages.error(request, f"Unexpected error: {e}")
            return redirect("buy_airtime")

        # Handle status messaging based on Transaction.status
        status = tx.status

        if status == "completed":

            # Send the purchase confirmation email after the transaction is completed
            send_purchase_email(request.user, tx)

            messages.success(
                request,
                f"₦{amount:,.2f} {network.upper()} airtime sent to {phone}.",
            )
            return redirect("airtime_receipt", reference=tx.reference)

        elif status == "pending":
            messages.warning(
                request,
                "Airtime purchase is pending confirmation from network. "
                "You can check the status in your transaction history.",
            )
            return redirect("transaction_history")

        else:  # failed or anything else
            resp_desc = (
                vtpass_resp.get("response_description")
                or vtpass_resp.get("message")
                or "Airtime purchase failed."
            )
            messages.error(
                request,
                f"Airtime purchase failed: {resp_desc}",
            )
            return redirect("buy_airtime")

    # GET: render form, optionally show balance
    wallet = Wallet.objects.filter(user=request.user).first()
    context = {"wallet": wallet}
    return render(request, "transactions/buy_airtime.html", context)


@login_required
def buy_data(request):

    available_networks = ["mtn", "airtel", "glo", "9mobile"]

    if request.method == "POST":
        network = (request.POST.get("network") or "").lower().strip()
        phone = (request.POST.get("phone") or "").strip()
        plan_code = (request.POST.get("plan") or "").strip()

        if not network or not phone or not plan_code:
            messages.error(request, "All fields are required.")
            return redirect("buy_data")

        try:
            tx, vtpass_resp = purchase_data(
                user=request.user,
                network=network,
                phone=phone,
                variation_code=plan_code,
            )

        except InsufficientBalanceError:
            messages.error(request, "Insufficient wallet balance.")
            return redirect("buy_data")

        except InvalidNetworkError as e:
            messages.error(request, str(e))
            return redirect("buy_data")
        
        except FraudCheckError as e:
            messages.error(request, str(e))
            return redirect("buy_data")

        except Exception as e:
            messages.error(request, f"Unexpected error: {e}")
            return redirect("buy_data")

        status = tx.status

        if status == "completed":

            # Send the purchase confirmation email after the transaction is completed
            send_purchase_email(request.user, tx)

            messages.success(
                request,
                f"{network.upper()} data purchase successful for {phone}.",
            )
            return redirect("data_receipt", reference=tx.reference)

        elif status == "pending":
            messages.warning(
                request,
                "Data purchase is pending confirmation from network. "
                "You can check the status in your transaction history.",
            )
            return redirect("dashboard")

        else:
            resp_desc = (
                vtpass_resp.get("response_description")
                or vtpass_resp.get("message")
                or "Data purchase failed."
            )
            messages.error(
                request,
                f"Data purchase failed: {resp_desc}",
            )
            return redirect("buy_data")

    # GET: render form
    selected_network = request.GET.get("network", "mtn").lower()
    if selected_network not in available_networks:
        selected_network = "mtn"

    # Flatten plans for template
    flat_plans = []
    for net_key, plans in DATA_PLANS.items():
        for p in plans:
            flat_plans.append(
                {
                    "network": net_key,
                    "code": p["code"],
                    "name": p["name"],
                    "amount": p["amount"],
                }
            )

    wallet = Wallet.objects.filter(user=request.user).first()

    context = {
        "wallet": wallet,
        "available_networks": available_networks,
        "selected_network": selected_network,
        "plans": flat_plans,
    }
    return render(request, "transactions/buy_data.html", context)



@login_required
def pay_electricity(request):
    available_discos = DISCO_SERVICE_ID_MAP  # dict: key -> serviceID

    if request.method == "POST":
        disco = request.POST.get("disco")
        meter_number = request.POST.get("meter_number")
        meter_type = request.POST.get("meter_type")
        amount = request.POST.get("amount")
        phone = request.POST.get("phone")

        try:
            tx, vtpass_resp = purchase_electricity(
                user=request.user,
                disco=disco,
                meter_number=meter_number,
                meter_type=meter_type,
                amount=amount,
                phone=phone,
            )

        except InsufficientBalanceError:
            messages.error(request, "Insufficient wallet balance.")
            return redirect("pay_electricity")

        except MeterVerificationError as e:
            messages.error(request, f"Meter verification failed: {e}")
            return redirect("pay_electricity")

        except InvalidNetworkError as e:
            messages.error(request, str(e))
            return redirect("pay_electricity")
        
        except FraudCheckError as e:
            messages.error(request, str(e))
            return redirect("pay_electricity")

        except ValueError as e:
            messages.error(request, str(e))
            return redirect("pay_electricity")

        except Exception as e:
            messages.error(request, f"Unexpected error: {e}")
            return redirect("pay_electricity")

        status = tx.status
        vt_token = (
            vtpass_resp.get("token")
            or vtpass_resp.get("purchased_code")
            or (vtpass_resp.get("content") or {}).get("token")
            or ""
        )
        vt_token = str(vt_token or "").replace("Token :", "").strip()

        if status == "completed":
            tx.token = vt_token
            tx.save()  # Save token to the transaction

            # Send the purchase confirmation email after the transaction is completed
            send_purchase_email(request.user, tx)

            if vt_token and (meter_type or "").lower() == "prepaid":
                meter_number_from_desc = tx.description.split("-")[1] if "-" in tx.description else meter_number
                messages.success(
                    request,
                    f"Electricity purchase successful for meter {meter_number}. "
                    f"Token: {vt_token}",
                )
            else:
                messages.success(
                    request,
                    f"Electricity bill payment successful for meter {meter_number}.",
                )
            return redirect("electricity_receipt", reference=tx.reference)

        elif status == "pending":
            messages.warning(
                request,
                "Electricity payment is pending confirmation from the DISCO. "
                "You can check the status in your transaction history.",
            )
            return redirect("dashboard")

        else:
            desc = (
                vtpass_resp.get("response_description")
                or vtpass_resp.get("message")
                or "Electricity purchase failed."
            )
            messages.error(request, f"Electricity purchase failed: {desc}")
            return redirect("pay_electricity")

    # GET – show form
    wallet = Wallet.objects.filter(user=request.user).first()
    context = {
        "wallet": wallet,
        "available_discos": available_discos,
    }
    return render(request, "transactions/pay_electricity.html", context)


@login_required
def electricity_receipt(request, reference):
    try:
        tx = Transaction.objects.get(reference=reference, wallet__user=request.user)
    except Transaction.DoesNotExist:
        messages.error(request, "Receipt not found.")
        return redirect("transaction_history")

    if tx.transaction_type != "purchase":
        messages.error(request, "Invalid transaction for receipt.")
        return redirect("transaction_history")

    return render(request, "transactions/electricity_receipt.html", {"tx": tx})

@login_required
def airtime_receipt(request, reference):
    try:
        tx = Transaction.objects.get(reference=reference, wallet__user=request.user)
    except Transaction.DoesNotExist:
        messages.error(request, "Airtime receipt not found.")
        return redirect("transaction_history")

    return render(request, "transactions/airtime_receipt.html", {"tx": tx})


@login_required
def data_receipt(request, reference):
    try:
        tx = Transaction.objects.get(reference=reference, wallet__user=request.user)
    except Transaction.DoesNotExist:
        messages.error(request, "Data receipt not found.")
        return redirect("transaction_history")

    return render(request, "transactions/data_receipt.html", {"tx": tx})
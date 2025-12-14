# wallet/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
import os
import requests
import hmac
import hashlib
import json

from wallet.models import Wallet
from transactions.models import Transaction

# Paystack Configuration
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY')
MAX_FUND_LIMIT = Decimal('100000.00')  # ₦100,000 max per deposit


# ============================================
# WALLET FUNDING (Paystack Integration)
# ============================================

@login_required
def fund_wallet(request):
    """Display wallet funding page with Paystack integration."""
    if request.method == 'POST':
        return HttpResponseBadRequest('Use JavaScript to initialize payment')
    
    context = {
        'paystack_public_key': PAYSTACK_PUBLIC_KEY,
        'email': request.user.email,
    }
    return render(request, 'wallet/fund_wallet.html', context)


@login_required
def verify_payment(request, reference):
    """Verify Paystack payment and credit user wallet."""
    PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
    try:
        # Call Paystack API to verify transaction
        url = f'https://api.paystack.co/transaction/verify/{reference}'
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        print(f"🔍 Paystack Response: {data}")  # Debug
        
        # Check if verification was successful
        if data['status'] and data['data']['status'] == 'success':
            amount = Decimal(data['data']['amount']) / 100  # Convert kobo to naira
            print(f"✅ Payment verified: ₦{amount}")
            
            # Validate amount
            if amount > MAX_FUND_LIMIT:
                messages.error(request, f'Amount cannot exceed ₦{MAX_FUND_LIMIT:,}')
                return redirect('fund_wallet')
            
            with transaction.atomic():
                # Lock wallet to prevent race conditions
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                
                # Check if transaction already processed (idempotency)
                if Transaction.objects.filter(reference=reference).exists():
                    print(f"⚠️ Transaction already processed")
                    messages.info(request, 'This payment has already been processed')
                    return redirect('wallet_info')
                
                # Credit wallet
                wallet.deposit(
                    amount=amount,
                    description='Paystack Deposit',
                    reference=reference
                )
                
                print(f"✅ Wallet credited! New balance: ₦{wallet.balance}")
            
            messages.success(request, f'Successfully funded wallet with ₦{amount:,.2f}')
            return redirect('dashboard')
        
        else:
            print(f"❌ Payment verification failed: {data}")
            messages.error(request, 'Payment verification failed')
            return redirect('fund_wallet')
    
    except requests.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        messages.error(request, 'Could not verify payment. Please contact support.')
        return redirect('fund_wallet')
    
    except Wallet.DoesNotExist:
        print(f"❌ Wallet not found for user: {request.user.username}")
        messages.error(request, 'Wallet not found')
        return redirect('fund_wallet')
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error processing payment: {str(e)}')
        return redirect('fund_wallet')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhook notifications."""
    secret = PAYSTACK_SECRET_KEY.encode()
    signature = request.headers.get('x-paystack-signature')
    payload = request.body
    
    # Verify webhook signature
    computed_sig = hmac.new(secret, payload, hashlib.sha512).hexdigest()
    if signature != computed_sig:
        return HttpResponse(status=400)
    
    # Process event
    event = json.loads(payload)
    if event['event'] == 'charge.success':
        reference = event['data']['reference']
        # TODO: Process payment asynchronously with Celery/RQ for production
    
    return HttpResponse(status=200)


# ============================================
# WALLET INFO
# ============================================

@login_required
def wallet_info(request):
    """Display user's wallet balance and recent transactions."""
    wallet = Wallet.objects.get(user=request.user)
    recent_transactions = Transaction.objects.filter(
        wallet=wallet
    ).order_by('-timestamp')[:10]  # Last 10 transactions
    
    return render(request, 'wallet/wallet_info.html', {
        'wallet': wallet,
        'recent_transactions': recent_transactions
    })


# # ============================================
# # DEMO WITHDRAWAL (For Testing Only)
# # ============================================

# @login_required
# def demo_withdraw(request):
#     """Demo withdrawal for testing purposes. Remove in production."""
#     if request.method == 'POST':
#         try:
#             amount = Decimal(request.POST.get('amount', '0'))
            
#             with transaction.atomic():
#                 wallet = Wallet.objects.select_for_update().get(user=request.user)
                
#                 # Use purchase method for withdrawals
#                 wallet.purchase(
#                     amount=amount,
#                     description='Demo Withdrawal'
#                 )
            
#             messages.success(request, f'Successfully withdrawn ₦{amount:,.2f}')
#             return redirect('dashboard')
            
#         except ValueError as e:
#             messages.error(request, str(e))
#         except Exception as e:
#             messages.error(request, f'Error: {str(e)}')
    
#     return render(request, 'wallet/demo_withdraw.html')
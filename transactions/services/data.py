# transactions/services/data.py

import time
from decimal import Decimal
from typing import Tuple, Dict, Any

from django.db import transaction as db_transaction

from django.contrib.auth import get_user_model

from wallet.models import Wallet
from transactions.models import Transaction
from transactions.providers import get_vtpass_client
from transactions.services.airtime import (
    InsufficientBalanceError,
    InvalidNetworkError,
)
from transactions.services.fraud_check import run_fraud_checks, FraudCheckError


User = get_user_model()

# Map our network keys to VTPass service IDs for data
NETWORK_DATA_SERVICE_ID_MAP: Dict[str, str] = {
    "mtn": "mtn-data",
    "airtel": "airtel-data",
    "glo": "glo-data",
    "9mobile": "etisalat-data",
}

# Simple in-code plan catalog for now (you can later fetch from VTPass variations API)
DATA_PLANS: Dict[str, list[dict]] = {
    "mtn": [
        {
            "code": "mtn-10mb-100",
            "name": "MTN 100MB – 24 hrs",
            "amount": Decimal("100"),
        },
        {
            "code": "mtn-50mb-200",
            "name": "MTN 200MB – 2 days",
            "amount": Decimal("200"),
        },
        {
            "code": "mtn-100mb-1000",
            "name": "MTN 1.5GB – 30 days",
            "amount": Decimal("1000"),
        },
    ],
    "airtel": [
        {
            "code": "airt-100",
            "name": "Airtel 75MB – 1 day",
            "amount": Decimal("100"),
        },
        {
            "code": "airt-200",
            "name": "Airtel 200MB – 3 days",
            "amount": Decimal("200"),
        },
        {
            "code": "airt-500",
            "name": "Airtel 750MB – 14 days",
            "amount": Decimal("500"),
        },
    ],
    "glo": [
        {
            "code": "glo100",
            "name": "Glo 105MB – 2 days",
            "amount": Decimal("100"),
        },
        {
            "code": "glo200",
            "name": "Glo 350MB – 4 days",
            "amount": Decimal("200"),
        },
        {
            "code": "glo500",
            "name": "Glo 1.05GB – 14 days",
            "amount": Decimal("500"),
        },
    ],
    "9mobile": [
        {
            "code": "eti-100",
            "name": "9mobile 100MB – 1 day",
            "amount": Decimal("100"),
        },
        {
            "code": "eti-200",
            "name": "9mobile 650MB – 1 day",
            "amount": Decimal("200"),
        },
        {
            "code": "eti-500",
            "name": "9mobile 500MB – 30 days",
            "amount": Decimal("500"),
        },
    ],
}



def get_data_plans_for_network(network: str) -> list[dict]:
    """
    Return list of plans for a given network key: 'mtn', 'airtel', 'glo', '9mobile'.
    """
    key = (network or "").lower()
    return DATA_PLANS.get(key, [])


def resolve_data_plan(network: str, variation_code: str) -> dict:
    """
    Find a plan dict for the given network + variation_code.

    Raises ValueError if not found.
    """
    key = (network or "").lower()
    plans = DATA_PLANS.get(key, [])
    for plan in plans:
        if plan["code"] == variation_code:
            return plan
    raise ValueError("Selected data plan is not available.")


def purchase_data(
    user: User,
    network: str,
    phone: str,
    variation_code: str,
) -> Tuple[Transaction, Dict[str, Any]]:
    """
    Purchase data using VTPass.

    Flow (similar to airtime):
    - Validate network + variation_code
    - Run fraud checks (NEW)
    - Check wallet balance
    - Create pending Transaction and debit wallet (atomic)
    - Call VTPass buy_data
    - Update Transaction status based on provider response
    - Refund wallet on failure
    """

    network_key = (network or "").lower()
    if network_key not in NETWORK_DATA_SERVICE_ID_MAP:
        raise InvalidNetworkError(f"Unsupported data network: {network}")

    service_id = NETWORK_DATA_SERVICE_ID_MAP[network_key]

    # Resolve the chosen plan + amount
    plan = resolve_data_plan(network_key, variation_code)
    amount: Decimal = plan["amount"]

    # ---------- FRAUD CHECK (NEW) ----------
    run_fraud_checks(user, amount)

    # Step 1: create transaction & debit wallet under lock
    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)

        if wallet.balance < amount:
            raise InsufficientBalanceError("Insufficient balance for data purchase.")

        # Generate reference like DATA-<user_id>-<timestamp_ms>
        reference = f"DATA-{user.pk}-{int(time.time() * 1000)}"

        tx = Transaction.objects.create(
            wallet=wallet,
            transaction_type="purchase",
            amount=amount,
            description=f"Data - {plan['name']} to {phone}",
            status="pending",
            reference=reference,
        )

        # Debit wallet
        wallet.balance -= amount
        wallet.save()

    # Step 2: Call provider outside of DB lock
    client = get_vtpass_client()
    vtpass_response = client.buy_data(
        service_id=service_id,
        phone=phone,
        variation_code=variation_code,
        amount=amount,
        request_id=tx.reference,
    )

    # Step 3: Interpret provider response & update transaction + wallet under lock
    code = str(vtpass_response.get("code", "")).strip()
    content = vtpass_response.get("content") or {}
    tx_data = content.get("transactions") or {}
    vtpass_status = str(tx_data.get("status", "")).lower()

    with db_transaction.atomic():
        # Reload fresh rows and lock
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        tx = Transaction.objects.select_for_update().get(pk=tx.pk)

        # Save provider snapshots (works with the new fields we added earlier)
        tx.provider_status = vtpass_status or code or ""
        tx.provider_response = vtpass_response

        if code in ("000", "0000") and vtpass_status in ("delivered", "success"):
            # Success
            tx.status = "completed"
            tx.description = (tx.description or "") + " [Data delivered]"
            tx.save()

        elif vtpass_status in ("pending", "processing", ""):
            # Still pending – let the verification job handle it later
            tx.status = "pending"
            tx.description = (tx.description or "") + " [Awaiting data confirmation]"
            tx.save()

        else:
            # Failed or unexpected error – mark failed and refund wallet
            tx.status = "failed"
            tx.description = (tx.description or "") + " [Data failed, refunded]"
            tx.save()

            wallet.balance += tx.amount
            wallet.save()

    return tx, vtpass_response
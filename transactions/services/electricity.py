# transactions/services/electricity.py

import time
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction

from transactions.models import Transaction
from transactions.providers import get_vtpass_client
from transactions.services.airtime import (
    InsufficientBalanceError,
    InvalidNetworkError,
)
from transactions.services.fraud_check import run_fraud_checks
from wallet.models import Wallet

User = get_user_model()


class MeterVerificationError(Exception):
    """Raised when VTpass meter verification fails."""


# Map our short DISCO keys to VTpass serviceID
DISCO_SERVICE_ID_MAP: dict[str, str] = {
    "ikedc": "ikeja-electric",
    "ekedc": "eko-electric",
    "aedc": "abuja-electric",
    "bedc": "benin-electric",
    "phed": "portharcourt-electric",
    "kaedco": "kaduna-electric",
    "kedco": "kano-electric",
    "eedc": "enugu-electric",
    "aba": "aba-electric",
}


def purchase_electricity(
    user: User,
    disco: str,
    meter_number: str,
    meter_type: str,
    amount: Decimal,
    phone: str,
) -> tuple[Transaction, dict[str, Any]]:
    """
    Purchase electricity via VTpass (prepaid or postpaid).

    Flow:
    - Validate DISCO + meter_type + amount
    - Run fraud checks (NEW)
    - Verify meter with VTpass (merchant-verify)
    - Debit wallet + create pending Transaction (atomic)
    - Call VTpass pay API
    - Update Transaction status and refund on failure (atomic)
    """

    disco_key = (disco or "").lower().strip()
    if disco_key not in DISCO_SERVICE_ID_MAP:
        raise InvalidNetworkError(f"Unsupported DISCO: {disco}")

    service_id = DISCO_SERVICE_ID_MAP[disco_key]

    meter_type = (meter_type or "").lower().strip()
    if meter_type not in ("prepaid", "postpaid"):
        raise ValueError("Invalid meter type. Must be 'prepaid' or 'postpaid'.")

    try:
        amount = Decimal(amount)
    except Exception:
        raise ValueError("Invalid amount.")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    meter_number = (meter_number or "").strip()
    if not meter_number:
        raise ValueError("Meter number is required.")

    phone = (phone or "").strip()
    if not phone:
        raise ValueError("Customer phone number is required.")

    # ---------- FRAUD CHECK (NEW) ----------
    run_fraud_checks(user, amount)

    client = get_vtpass_client()

    # 1) Verify meter with VTpass
    verify_resp = client.verify_meter(
        service_id=service_id,
        meter_number=meter_number,
        meter_type=meter_type,
    )
    if str(verify_resp.get("code")) != "000":
        desc = verify_resp.get("response_description") or "Meter verification failed."
        raise MeterVerificationError(desc)

    # Optional: you can inspect verify_resp["content"] for name/address if needed

    # 2) Create transaction + debit wallet under lock
    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)

        if wallet.balance < amount:
            raise InsufficientBalanceError("Insufficient balance for electricity purchase.")

        reference = f"ELEC-{user.pk}-{int(time.time() * 1000)}"

        tx = Transaction.objects.create(
            wallet=wallet,
            transaction_type="purchase",
            amount=amount,
            description=f"Electricity VTU - {disco_key.upper()} {meter_type} meter {meter_number} via VTPass",
            status="pending",
            reference=reference,
        )

        wallet.balance -= amount
        wallet.save()

    # 3) Call VTpass pay outside DB lock
    vtpass_resp = client.pay_electricity(
        service_id=service_id,
        meter_number=meter_number,
        meter_type=meter_type,
        amount=amount,
        phone=phone,
        request_id=tx.reference,
    )

    # Extract status + token-like fields
    code = str(vtpass_resp.get("code", "")).strip()
    content = vtpass_resp.get("content") or {}
    tx_data = content.get("transactions") or {}
    vtpass_status = str(tx_data.get("status", "")).lower()

    # Electricity token (prepaid)
    token = (
        vtpass_resp.get("token") or vtpass_resp.get("purchased_code") or content.get("token") or ""
    )
    token = str(token or "").strip()

    # 4) Update transaction + wallet under lock, with refund on failure
    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        tx = Transaction.objects.select_for_update().get(pk=tx.pk)

        tx.provider_status = vtpass_status or code or ""
        tx.provider_response = vtpass_resp

        if code == "000" and vtpass_status == "delivered":
            tx.status = "completed"
            if token:
                tx.token = token
            else:
                # if error delete
                tx.description = (tx.description or "") + " [Electricity delivered]"
            tx.save()

        elif vtpass_status in ("pending", "processing", ""):
            tx.status = "pending"
            tx.description = (tx.description or "") + " [Awaiting DISCO confirmation]"
            tx.save()

        else:
            tx.status = "failed"
            tx.description = (tx.description or "") + " [Electricity failed, refunded]"
            tx.save()

            wallet.balance += tx.amount
            wallet.save()

    return tx, vtpass_resp

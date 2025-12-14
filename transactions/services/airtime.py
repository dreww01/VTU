# transactions/services/airtime.py

from decimal import Decimal
from typing import Tuple

from django.db import transaction as db_transaction
from django.utils import timezone

from wallet.models import Wallet
from transactions.models import Transaction
from transactions.providers import get_vtpass_client
from transactions.providers.exceptions import VTPassError
from transactions.services.fraud_check import run_fraud_checks, FraudCheckError


# Map UI network selection -> VTPass serviceID
NETWORK_SERVICE_ID_MAP = {
    "mtn": "mtn",
    "airtel": "airtel",
    "glo": "glo",
    "9mobile": "etisalat",  # VTPass still uses 'etisalat'
}


class InsufficientBalanceError(Exception):
    """Raised when wallet does not have enough balance."""


class InvalidNetworkError(Exception):
    """Raised when provided network is not supported."""


def _generate_request_id(user_id: int) -> str:
    """
    Generate a unique request_id for VTPass & our Transaction reference.
    Simple format: VTU-<user_id>-<timestamp>
    """
    ts = int(timezone.now().timestamp() * 1000)
    return f"VTU-{user_id}-{ts}"


def purchase_airtime(
    *,
    user,
    network: str,
    phone: str,
    amount: Decimal,
) -> Tuple[Transaction, dict]:
    """
    Core airtime purchase flow.

    - Validates network
    - Runs fraud checks (NEW)
    - Locks wallet & checks balance
    - Creates a pending Transaction
    - Debits wallet
    - Calls VTPass API
    - Updates Transaction status based on provider response
    - Refunds wallet if needed

    Returns (transaction, raw_provider_response)
    May raise InsufficientBalanceError, InvalidNetworkError, VTPassError, FraudCheckError
    """

    # Normalize network key
    network_key = network.lower().strip()
    if network_key not in NETWORK_SERVICE_ID_MAP:
        raise InvalidNetworkError(f"Unsupported network: {network}")

    service_id = NETWORK_SERVICE_ID_MAP[network_key]

    if amount <= 0:
        raise ValueError("Amount must be positive.")

    # ---------- FRAUD CHECK (NEW) ----------
    # This will raise FraudCheckError if user exceeds limits
    run_fraud_checks(user, amount)

    client = get_vtpass_client()
    request_id = _generate_request_id(user.id)

    # ---------- Step 1: create pending transaction & debit wallet ----------

    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)

        if wallet.balance < amount:
            raise InsufficientBalanceError("Insufficient wallet balance.")

        tx = Transaction.objects.create(
            wallet=wallet,
            transaction_type="purchase",   # must exist in your choices
            amount=amount,
            status="pending",              # must exist in your choices
            reference=request_id,
            description=f"Airtime VTU - {network_key.upper()} to {phone} via VTPass",
        )

        # Debit wallet immediately (we'll refund on failure)
        wallet.balance -= amount
        wallet.save()

    # ---------- Step 2: call VTPass outside the DB lock ----------

    vtpass_response = client.buy_airtime(
        service_id=service_id,
        phone=phone,
        amount=amount,
        request_id=request_id,
    )

    code = str(vtpass_response.get("code", "")).strip()
    # VTPass success is usually "000" or "0000"
    is_success = code in ("000", "0000")

    content = vtpass_response.get("content") or {}
    transactions_data = content.get("transactions") or {}
    vtpass_status = str(transactions_data.get("status", "")).lower()

    # ---------- Step 3: update Transaction & wallet based on provider result ----------

    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)
        tx = Transaction.objects.select_for_update().get(reference=request_id, wallet=wallet)

        if is_success and vtpass_status in ("delivered", "success"):
            tx.status = "completed"
            tx.description = f"Airtime SUCCESS - {network_key.upper()} to {phone}"
            tx.save()
            # Wallet already debited
        elif vtpass_status in ("pending", "processing"):
            tx.status = "pending"
            tx.description = f"Airtime PENDING - {network_key.upper()} to {phone}"
            tx.save()
        else:
            tx.status = "failed"
            tx.description = f"Airtime FAILED - {network_key.upper()} to {phone}"
            tx.save()

            # Refund wallet
            wallet.balance += amount
            wallet.save()

    return tx, vtpass_response
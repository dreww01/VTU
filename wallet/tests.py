import hashlib
import hmac
import json
import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from transactions.models import Transaction
from wallet.models import MAX_BALANCE, MAX_TRANSACTION, Wallet

User = get_user_model()
TEST_SECRET_KEY = "test_paystack_secret_key_123"


def compute_signature(payload: bytes, secret: str = TEST_SECRET_KEY) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha512).hexdigest()


class WalletModelTests(TestCase):
    """Unit tests for the Wallet model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
        )
        self.wallet = Wallet.objects.get(user=self.user)

    def test_wallet_creation_and_defaults(self):
        """Wallet should be automatically created via post_save signal with 0.00 balance."""
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertEqual(self.wallet.currency, "NGN")
        self.assertEqual(str(self.wallet), f"{self.user.username}'s Wallet - ₦0.00")

    def test_deposit_valid_amount(self):
        """Depositing a valid amount should increase balance and create completed Transaction."""
        tx = self.wallet.deposit(
            amount=Decimal("5000.00"),
            description="Test Deposit",
            reference="REF_TEST_001",
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("5000.00"))
        self.assertEqual(tx.amount, Decimal("5000.00"))
        self.assertEqual(tx.transaction_type, "funding")
        self.assertEqual(tx.reference, "REF_TEST_001")
        self.assertEqual(tx.status, "completed")
        self.assertEqual(tx.description, "Test Deposit")

    def test_deposit_invalid_amounts(self):
        """Deposit should reject non-positive amounts, invalid types, or amounts exceeding limits."""
        with self.assertRaises(ValueError):
            self.wallet.deposit(Decimal("0.00"))

        with self.assertRaises(ValueError):
            self.wallet.deposit(Decimal("-100.00"))

        with self.assertRaises(ValueError):
            self.wallet.deposit("invalid_number")

        with self.assertRaises(ValueError):
            self.wallet.deposit(MAX_TRANSACTION + Decimal("1.00"))

    def test_purchase_valid_and_insufficient_funds(self):
        """Purchase should deduct balance if funds are sufficient and reject when insufficient."""
        self.wallet.deposit(Decimal("1000.00"), reference="REF_DEP_1")
        tx = self.wallet.purchase(Decimal("400.00"), description="MTN Data")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("600.00"))
        self.assertEqual(tx.amount, Decimal("400.00"))
        self.assertEqual(tx.transaction_type, "purchase")

        with self.assertRaises(ValueError):
            self.wallet.purchase(Decimal("700.00"), description="Airtel Data")

    def test_wallet_clean_validation(self):
        """Wallet clean method should enforce balance constraints."""
        self.wallet.balance = Decimal("-10.00")
        with self.assertRaises(ValidationError):
            self.wallet.clean()

        self.wallet.balance = MAX_BALANCE + Decimal("100.00")
        with self.assertRaises(ValidationError):
            self.wallet.clean()


class PaystackWebhookTests(TestCase):
    """Tests for the Paystack charge.success webhook fulfillment endpoint."""

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse("paystack_webhook")
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="password123",
        )
        self.wallet = Wallet.objects.get(user=self.user)

    def _post_webhook(self, payload_dict, signature=None, content_type="application/json"):
        if isinstance(payload_dict, (dict, list)):
            payload_bytes = json.dumps(payload_dict).encode("utf-8")
        elif isinstance(payload_dict, (bytes, str)):
            payload_bytes = (
                payload_dict if isinstance(payload_dict, bytes) else payload_dict.encode("utf-8")
            )
        else:
            payload_bytes = b""

        extra = {}
        if signature is not None:
            extra["HTTP_X_PAYSTACK_SIGNATURE"] = signature

        return self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type=content_type,
            **extra,
        )

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_valid_charge_success_credits_wallet(self):
        """Valid charge.success webhook credits the user's wallet with the exact amount."""
        payload = {
            "event": "charge.success",
            "data": {
                "id": 123456,
                "reference": "PSK_REF_1001",
                "amount": 500000,  # 5,000.00 NGN in kobo
                "status": "success",
                "customer": {
                    "email": "customer@example.com",
                    "id": 789,
                },
            },
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(payload_bytes, TEST_SECRET_KEY)

        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(payload, signature=sig)

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("5000.00"))

        # Verify Transaction record was created
        tx = Transaction.objects.get(reference="PSK_REF_1001")
        self.assertEqual(tx.amount, Decimal("5000.00"))
        self.assertEqual(tx.transaction_type, "funding")
        self.assertEqual(tx.description, "Paystack Webhook Deposit")
        self.assertEqual(tx.status, "completed")
        self.assertEqual(tx.wallet, self.wallet)

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_case_insensitive_email_webhook_credits_wallet(self):
        """Webhook with customer email in different casing (e.g. mixed/upper case) still matches user."""
        payload = {
            "event": "charge.success",
            "data": {
                "id": 123457,
                "reference": "PSK_REF_CASE_1002",
                "amount": 300000,  # 3,000.00 NGN in kobo
                "status": "success",
                "customer": {
                    "email": "Customer@Example.Com",
                    "id": 789,
                },
            },
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(payload_bytes, TEST_SECRET_KEY)

        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(payload, signature=sig)

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("3000.00"))

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_replaying_webhook_is_idempotent(self):
        """Replaying the exact same webhook payload/reference returns HTTP 200 without double-crediting."""
        payload = {
            "event": "charge.success",
            "data": {
                "reference": "PSK_REF_REPLAY_1",
                "amount": 250000,  # 2,500.00 NGN
                "customer": {
                    "email": "customer@example.com",
                },
            },
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(payload_bytes, TEST_SECRET_KEY)

        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            # First delivery
            response1 = self._post_webhook(payload, signature=sig)
            self.assertEqual(response1.status_code, 200)
            self.wallet.refresh_from_db()
            self.assertEqual(self.wallet.balance, Decimal("2500.00"))
            self.assertEqual(Transaction.objects.filter(reference="PSK_REF_REPLAY_1").count(), 1)

            # Replay same payload
            response2 = self._post_webhook(payload, signature=sig)
            self.assertEqual(response2.status_code, 200)
            self.wallet.refresh_from_db()
            # Balance must still be 2500.00, NOT 5000.00
            self.assertEqual(self.wallet.balance, Decimal("2500.00"))
            self.assertEqual(Transaction.objects.filter(reference="PSK_REF_REPLAY_1").count(), 1)

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_missing_signature_header_returns_400(self):
        """Webhook request without x-paystack-signature header returns HTTP 400."""
        payload = {
            "event": "charge.success",
            "data": {
                "reference": "PSK_REF_NO_SIG",
                "amount": 100000,
                "customer": {"email": "customer@example.com"},
            },
        }
        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(payload, signature=None)

        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_empty_signature_header_returns_400(self):
        """Webhook request with empty signature header returns HTTP 400."""
        payload = {
            "event": "charge.success",
            "data": {
                "reference": "PSK_REF_EMPTY_SIG",
                "amount": 100000,
                "customer": {"email": "customer@example.com"},
            },
        }
        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(payload, signature="")

        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_forged_signature_returns_400(self):
        """Webhook request with forged / invalid signature returns HTTP 400."""
        payload = {
            "event": "charge.success",
            "data": {
                "reference": "PSK_REF_FORGED",
                "amount": 100000,
                "customer": {"email": "customer@example.com"},
            },
        }
        forged_sig = "a" * 128  # Invalid HMAC-SHA512 hex string

        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(payload, signature=forged_sig)

        self.assertEqual(response.status_code, 400)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_nonexistent_customer_email_returns_404(self):
        """Webhook for non-existent customer email returns HTTP 404 without crashing."""
        payload = {
            "event": "charge.success",
            "data": {
                "reference": "PSK_REF_NONEXISTENT_USER",
                "amount": 100000,
                "customer": {"email": "nonexistent@example.com"},
            },
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(payload_bytes, TEST_SECRET_KEY)

        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(payload, signature=sig)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Transaction.objects.filter(reference="PSK_REF_NONEXISTENT_USER").exists())

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_unhandled_event_type_returns_200(self):
        """Events other than charge.success (e.g. transfer.success) return 200 without crediting."""
        payload = {
            "event": "transfer.success",
            "data": {
                "reference": "PSK_REF_TRANSFER",
                "amount": 100000,
                "customer": {"email": "customer@example.com"},
            },
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(payload_bytes, TEST_SECRET_KEY)

        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(payload, signature=sig)

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_malformed_json_payload_returns_400(self):
        """Invalid JSON payload returns HTTP 400."""
        raw_payload = b"not-a-valid-json-string"
        sig = compute_signature(raw_payload, TEST_SECRET_KEY)

        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(raw_payload, signature=sig)

        self.assertEqual(response.status_code, 400)

    @override_settings(PAYSTACK_SECRET_KEY=TEST_SECRET_KEY)
    def test_incomplete_payload_missing_fields_returns_400(self):
        """Payload missing required reference or amount returns HTTP 400."""
        payload = {
            "event": "charge.success",
            "data": {
                "customer": {"email": "customer@example.com"},
                # Missing reference and amount
            },
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        sig = compute_signature(payload_bytes, TEST_SECRET_KEY)

        with patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": TEST_SECRET_KEY}):
            response = self._post_webhook(payload, signature=sig)

        self.assertEqual(response.status_code, 400)


class WalletViewsTests(TestCase):
    """Tests for fund_wallet, verify_payment, and wallet_info views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="viewuser",
            email="viewuser@example.com",
            password="password123",
        )
        self.wallet = Wallet.objects.get(user=self.user)
        self.client.login(username="viewuser", password="password123")

    def test_fund_wallet_get(self):
        """GET fund_wallet should render fund_wallet page."""
        response = self.client.get(reverse("fund_wallet"))
        self.assertEqual(response.status_code, 200)

    def test_fund_wallet_post_returns_400(self):
        """POST fund_wallet should return 400 (client-side Paystack JS required)."""
        response = self.client.post(reverse("fund_wallet"))
        self.assertEqual(response.status_code, 400)

    def test_wallet_info_view(self):
        """wallet_info should render user's wallet balance and transactions."""
        self.wallet.deposit(Decimal("1000.00"), reference="INFO_REF_1")
        response = self.client.get(reverse("wallet_info"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1,000.00")

    @patch("wallet.views.get_paystack_client")
    def test_verify_payment_success(self, mock_get_client):
        """verify_payment view verifies reference with Paystack and credits wallet."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "status": "success",
                "amount": 300000,  # 3,000 NGN in kobo
            },
        }
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        response = self.client.get(
            reverse("verify_payment", kwargs={"reference": "VERIFY_REF_1"})
        )
        self.assertEqual(response.status_code, 302)  # Redirects to dashboard
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("3000.00"))
        self.assertTrue(Transaction.objects.filter(reference="VERIFY_REF_1").exists())

    @patch("wallet.views.get_paystack_client")
    def test_verify_payment_idempotency(self, mock_get_client):
        """verify_payment redirects to wallet_info without double crediting when reference is re-verified."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "status": "success",
                "amount": 300000,
            },
        }
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        # First verification
        self.client.get(reverse("verify_payment", kwargs={"reference": "VERIFY_REF_IDEM"}))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("3000.00"))

        # Second verification of same reference
        response2 = self.client.get(
            reverse("verify_payment", kwargs={"reference": "VERIFY_REF_IDEM"})
        )
        self.assertEqual(response2.status_code, 302)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("3000.00"))
